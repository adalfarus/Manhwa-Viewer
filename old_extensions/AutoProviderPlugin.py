from oaplustools.data.imagetools import OnlineImage, OfflineImage
from concurrent.futures import ThreadPoolExecutor, as_completed
from oaplustools.web.search import Search
from urllib.parse import urljoin, urlparse
from typing import Optional, Union, List
from requests.sessions import Session
from abc import ABC, abstractmethod
from multiprocessing import Pool
from bs4 import BeautifulSoup
from queue import Queue
from PIL import Image
import unicodedata
import threading
import requests
import urllib3
import time
import re
import os

from aplustools.package.timid import TimidTimer

import aiohttp
import asyncio
import aiofiles

convert_image_format = OnlineImage.convert_image_format

# Disable only the specific InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class AutoProviderPlugin(ABC):
    def __init__(self, title: str, chapter: int, chapter_rate: float, data_folder: str, cache_folder: str,
                 provider: str, specific_provider_website: str, logo_path: str, num_workers: int = 10):
        self.title = title
        self.url_title = self.urlify(title)
        self.chapter = None
        self.chapter_str = None
        self.chap(chapter)
        self.chapter_rate = chapter_rate
        self.data_folder = data_folder
        self.cache_folder = cache_folder
        self.provider_type = provider
        self.specific_provider_website = specific_provider_website
        self.logo_path = logo_path
        self.blacklisted_websites = [
            "247manga.com",
            "ww6.mangakakalot.tv",
            "jimanga.com",
            "mangapure.net",
            "mangareader.mobi",
            "onepiece.fandom.com"
        ]
        self.current_url = None
        self.image_queue = Queue()
        self.total_images = 0
        self.download_progress_queue = Queue()
        self.process_progress_queue = Queue()
        self.session = Session()  # Create a session for connection pooling
        self.clipping_space = None
        self.num_workers = num_workers

    @staticmethod
    def urlify(to_url: str):
        url = unicodedata.normalize('NFKD', to_url)
        url = url.encode('ascii', 'ignore').decode('ascii')
        url = re.sub(r"[^a-zA-Z0-9\s_-]", "", url)  # title = re.sub(r"[^a-zA-Z0-9_-]", "", title)
        return url.strip()

    def get_logo_path(self):
        return self.logo_path

    def set_title(self, new_title):
        self.title = new_title
        self.url_title = self.urlify(new_title)

    def get_title(self):
        return self.title

    def set_chapter(self, new_chapter):
        self.chapter = new_chapter
        self.chap()

    def get_chapter(self):
        self.chap()
        return self.chapter

    def set_chapter_rate(self, new_chapter_rate):
        self.chapter_rate = new_chapter_rate

    def get_chapter_rate(self):
        return self.chapter_rate

    def set_provider_type(self, new_provider):
        self.provider_type = new_provider

    def get_provider_type(self):
        return self.provider_type

    def set_current_url(self, new_current_url):
        self.current_url = new_current_url

    def get_current_url(self):
        return self.current_url

    def set_blacklisted_websites(self, new_blacklisted_websites):
        self.blacklisted_websites = new_blacklisted_websites

    def get_blacklisted_websites(self):
        return self.blacklisted_websites

    def chap(self, chapter=None):
        if chapter is not None:
            self.chapter = int(chapter) if float(chapter).is_integer() else chapter
            self.chapter_str = str(self.chapter).replace(".", "-")
        else:
            self.chapter = int(self.chapter) if float(self.chapter).is_integer() else self.chapter
            self.chapter_str = str(self.chapter).replace(".", "-")

    def next_chapter(self, progress_queue=None):
        self.chapter += self.chapter_rate
        self.chap()
        if self.update_current_url():
            return self._handle_cache_result(self.cache_current_chapter(), progress_queue)
        else:
            if progress_queue:
                progress_queue.put(0)
            return False

    def previous_chapter(self, progress_queue=None):
        self.chapter -= self.chapter_rate
        self.chap()
        if self.update_current_url():
            return self._handle_cache_result(self.cache_current_chapter(), progress_queue)
        else:
            if progress_queue:
                progress_queue.put(0)
            return False

    def reload_chapter(self, progress_queue=None):
        self.chap()
        if self.update_current_url():
            return self._handle_cache_result(self.cache_current_chapter(), progress_queue)
        else:
            if progress_queue:
                progress_queue.put(0)
            return False

    def _handle_cache_result(self, cache_gen, progress_queue):
        final_result = None
        for progress_or_result in cache_gen:
            # print("Handle cache result got: ", progress_or_result) # Debug
            if isinstance(progress_or_result, bool):  # Check if it's the final result
                final_result = progress_or_result
            else:
                if progress_queue:
                    progress_queue.put(progress_or_result)  # Put the progress into the queue
                else:
                    continue  # If no progress_queue is provided, just continue to the next iteration
        print("Handle cache result done, returning now ...")
        return final_result

    def _download_logo_image(self, url_or_data: str, new_name: str, img_format: str, img_type: Optional[str] = None):
        image = OnlineImage(url_or_data)
        if img_type.lower() == "url":
            image.download_image(self.data_folder, url_or_data, new_name, img_format)
        elif img_type.lower() == "base64":  # Moved data to the back to avoid using keyword arguments
            image.base64(self.data_folder, new_name, img_format, url_or_data)

    def redo_prep(self):
        self._empty_cache()
        image = Image.open(f"{self.data_folder}/empty.png")
        image.save(f"{self.cache_folder}/empty.png")

    def update_current_url(self):
        print("Updating current URL...")
        self.current_url = self._get_current_chapter_url()
        if self.current_url:
            print(f"Current URL set to: {self.current_url}")
            return True
        else:
            print("Failed to update current URL.")
            return False

    def _get_current_chapter_url(self):
        provider_function = {
            "google": self._google_provider,
            "duckduckgo": self._duckduckgo_provider,
            "bing": self._bing_provider,
            "indirect": self._indirect_provider,
            "direct": self._direct_provider
        }.get(self.provider_type.lower())

        if provider_function:
            return provider_function()
        else:
            print(f"Provider {self.provider_type} not supported.")
            return None

    @classmethod
    def check_url(cls, useragent: str, url: str, urlTitle: str, inTitle: Optional[Union[str, List[str]]] = None,
                  blacklisted_websites: Optional[list] = None) -> Optional[str]:
        if inTitle is not None and not isinstance(inTitle, list): inTitle = [inTitle]
        if inTitle is None or all([str(x).lower() in urlTitle.lower() for x in inTitle]):
            # Checking if the URL is accessible or leads to a 404 error
            try:
                response = requests.head(url, allow_redirects=True)  # Using HEAD request to get the headers
                if response.status_code == 404:
                    print(f"The URL {url} leads to a 404 error, checking next result...")
                    return None
            except requests.RequestException as e:
                print(f"Error accessing URL {url}: {e}, checking next result...")
                return None
            if cls.is_crawlable(useragent, url):
                if blacklisted_websites is None or not url.split("/")[2] in blacklisted_websites:
                    return url
                else:
                    print("Blacklisted URL:", url)
            else:
                print(f"The URL {url} cannot be crawled, checking next result...")
        return None

    @classmethod
    def is_crawlable(cls, useragent: str, url: str) -> bool:
        """
        Check if the URL can be crawled by checking the robots.txt file of the website.
        """
        try:
            domain = urlparse(url).netloc
            robots_txt_url = urljoin(f'https://{domain}', '/robots.txt')

            # Retrieve the robots.txt content
            response = requests.get(robots_txt_url)

            # If robots.txt exists, parse it
            if response.status_code == 200:
                lines = response.text.split('\n')
                user_agent_section = False
                for line in lines:
                    if line.lower().startswith('user-agent'):
                        if user_agent_section:
                            break
                        user_agent_section = any(ua.strip() == useragent.lower() for ua in line.split(':')[1:])
                    elif user_agent_section and line.lower().startswith('disallow'):
                        disallowed_path = line.split(':')[1].strip()
                        if disallowed_path == '/' or url.startswith(disallowed_path) and disallowed_path != "":
                            return False
                if not user_agent_section and useragent != "*":
                    return cls.is_crawlable("*", url)
                return True
            else:
                # If robots.txt does not exist, assume everything is crawlable
                return True
        except Exception as e:
            print(f"An error occurred while checking the robots.txt file: {e}")
            return False  # Return False if there was an error or the robots.txt file couldn't be retrieved

    def _get_url(self, url, title):
        return self.check_url("*", url, title, [self.title, str(self.chapter)])

    def _google_provider(self):
        queries = [
            f'manga "{self.title}" "chapter {self.chapter}" site:{self.specific_provider_website} -tapas',
            f'manga "{self.title}" chapter {self.chapter} site:{self.specific_provider_website} -tapas',
            f'manga {self.title} chapter {self.chapter} site:{self.specific_provider_website} -tapas',
            f'manga {self.title} site:{self.specific_provider_website}',
            f'manga site:{self.specific_provider_website}'
        ]
        search = Search()
        return search.google_provider(queries)

    def _duckduckgo_provider(self):
        queries = [
            f'manga "{self.title}" "chapter {self.chapter}" site:{self.specific_provider_website} -tapas',
            f'manga "{self.title}" chapter {self.chapter} site:{self.specific_provider_website} -tapas',
            f'manga {self.title} chapter {self.chapter} site:{self.specific_provider_website} -tapas',
            f'manga {self.title} site:{self.specific_provider_website}',
            f'manga site:{self.specific_provider_website}'
        ]
        search = Search()
        return search.duckduckgo_provider(queries)

    def _bing_provider(self):
        queries = [
            f'manga "{self.title}" "chapter {self.chapter}" site:{self.specific_provider_website} -tapas',
            f'manga "{self.title}" chapter {self.chapter} site:{self.specific_provider_website} -tapas',
            f'manga {self.title} chapter {self.chapter} site:{self.specific_provider_website} -tapas',
            f'manga {self.title} site:{self.specific_provider_website}',
            f'manga site:{self.specific_provider_website}'
        ]
        search = Search()
        return search.bing_provider(queries)

    @abstractmethod
    def _indirect_provider(self):  # Can't be generalized, you need to overwrite this
        return None

    @abstractmethod
    def _direct_provider(self):  # Can't be generalized, you need to overwrite this
        return None

    def get_search_results(self, text):  # Can't be generalized, you need to overwrite this
        return False  # Could also return None, but stick to bool for this method

    def _empty_cache(self):
        files = os.listdir(self.cache_folder)
        for f in files:
            os.remove(f"{self.cache_folder}/{f}")

    async def _download_image_async(self, session, img_tag, new_name):
        timer = TimidTimer()
        url = urljoin(self.current_url, img_tag['src'])
        async with session.get(url) as response:
            if response.status == 200:
                content = await response.read()
                file_extension = img_tag['src'].split(".")[-1]
                file_name = f"{new_name}.{file_extension}"
                file_path = os.path.join(self.cache_folder, file_name)
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(content)
                print(timer.end(), "IMGTI")
                self.downloaded_images_count += 1
                progress = int((self.downloaded_images_count / self.total_images) * 100)
                self.download_progress_queue.put(progress)
                return file_name
        return img_tag['src'].split("/")[-1]

    async def download_images_async(self, validated_tags):
        total_images = len(validated_tags)
        count = 0
        async with aiohttp.ClientSession() as session:
            tasks = []
            for img_tag in validated_tags:
                new_image_name = f"{str(count).zfill(3)}"
                task = asyncio.create_task(
                    self._download_image_async(session, img_tag, new_image_name))
                tasks.append(task)
                count += 1

            results = await asyncio.gather(*tasks)
            print(f"{len(validated_tags)} images downloaded!")
            return results

    def download_images(self):
        try:
            response = requests.get(self.current_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            img_tags = soup.find_all('img')

            validated_tags = [img_tag for img_tag in img_tags if self.validate_image(img_tag['src'].split("/")[-1])[-1]]

            self.total_images = len(validated_tags)

            self.downloaded_images_count = 0
            download_result = asyncio.run(self.download_images_async(validated_tags))

            return True

        except Exception as e:
            print(f"An error occurred: {e}")
            return False

    def validate_image(self, image):
        timer = TimidTimer()
        file_name, file_extension, *_ = image.rsplit(".", maxsplit=1) + ["", ""]
        new_name = file_name.zfill(3)
        if file_name.isdigit():
            print(timer.end(), "VALT")
            return file_name, file_extension, new_name, True
        print(timer.end(), "VALF")
        return file_name, file_extension, new_name, False

    def cache_current_chapter(self):
        timer = TimidTimer()
        if not self.current_url:
            print("URL nor found.")
            yield 0
            return False
        self._empty_cache()

        timer2 = TimidTimer()
        download_result_queue = Queue()
        download_thread = threading.Thread(target=lambda q=download_result_queue: q.put(self.download_images()))
        download_thread.start()
        print(timer2.end(), "STRTUP")

        current_download_progress = 0
        combined_progress = 0

        yield 0

        while True:
            if not download_thread.is_alive() and self.download_progress_queue.empty():
                break

            # Handle download progress
            if not self.download_progress_queue.empty():
                new_download_progress = self.download_progress_queue.get()
                progress_diff = new_download_progress - current_download_progress
                combined_progress += progress_diff
                current_download_progress = new_download_progress

            yield combined_progress // 2
            time.sleep(0.1)

        download_result = download_result_queue.get()
        print("DOWNLOAD RESULT", download_result)

        print("Cache current chapter done, returning now")
        print("Download Thread alive: " + str(download_thread.is_alive()))
        print(timer.end(), "FULL")
        return download_result


class AutoProviderBaseLike(AutoProviderPlugin):
    def __init__(self, title, chapter, chapter_rate, data_folder, cache_folder, provider, specific_provider_website,
                 logo_path, logo_url_or_data, logo_img_format, logo_img_type, num_workers: int = 10):
        super().__init__(title=title, chapter=chapter, chapter_rate=chapter_rate, data_folder=data_folder,
                         cache_folder=cache_folder, provider=provider,
                         specific_provider_website=specific_provider_website, logo_path=logo_path, num_workers=num_workers)
        if not os.path.isfile(os.path.join(data_folder, logo_path.split("/")[-1])):
            try:
                # Using base64 is better as it won't matter if the url is ever changed, otherwise pass the url and
                # img_type="url"
                self._download_logo_image(logo_url_or_data, logo_path.split("/")[-1].split(".")[0],
                                          img_format=logo_img_format, img_type=logo_img_type)
            except Exception as e:
                print(f"An error occurred {e}")
                return

    def _search_post(self, text):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': f'https://{self.specific_provider_website}',
            'Referer': f'https://{self.specific_provider_website}',
        }

        # Define the URL for the request
        url = f'https://{self.specific_provider_website}/wp-admin/admin-ajax.php'

        # Define the data for the first POST request
        data = {
            'action': 'wp-manga-search-manga',
            'title': text
        }

        # Send the first POST request
        response = requests.post(url, headers=headers, data=data)

        # Check for a successful response (HTTP status code 200)
        if response.status_code == 200:
            # Parse the JSON response
            response_data = response.json()
            return response_data
        else:
            print(f'Error: {response.status_code}')
        return None

    def _search_web(self, text):
        base_url = self.specific_provider_website
        search_url = f"https://{base_url}?s={text}&post_type=wp-manga"

        response = requests.get(search_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        c_tabs_item_divs = soup.find_all('div', class_='c-tabs-item')  # There is only ever one of these

        # Dictionary to hold titles and urls
        titles_urls = []

        # Iterate through each div to extract titles and urls
        for div in c_tabs_item_divs:
            for row_c_tabs in div.find_all('div', class_='row c-tabs-item__content'):
                a_tag = row_c_tabs.find('a')
                if a_tag and 'href' in a_tag.attrs and 'title' in a_tag.attrs:
                    titles_urls.append({"title": a_tag['title'], "url": a_tag['href']})

        return {"data": titles_urls}

    def _search(self, text: Optional[str] = None):
        text = text or self.title

        search_results = self._search_web(text)
        if not search_results["data"]:
            search_results = self._search_post(text)
        return search_results

    def _direct_provider(self):
        response_data = self._search()
        url = self._get_url(response_data["data"][0]["url"] + f"chapter-{self.chapter_str}/",
                            f'chapter {self.chapter} {self.title.title()}')
        if url:
            print("Found URL:" + url)  # Concatenate (add-->+) string, to avoid breaking timestamps
            return url
        return None

    def _indirect_provider(self):
        url = self._get_url(
            f'https://{self.specific_provider_website}/manga/{"-".join(self.url_title.lower().split())}/chapter-'
            f'{self.chapter_str}/', f'chapter{self.chapter} {self.title.title()}')
        if url:
            print("Found URL:" + url)  # Concatenate (add-->+) string, to avoid breaking timestamps
            return url
        return None

    def get_search_results(self, text):
        if text is None:
            return True
        response_data = self._search(text)
        titles = [data.get("title") for data in response_data["data"]]
        # urls = [self._get_url(data["url"] + f"chapter-{self.chapter_str}/",
        #                       f'chapter {self.chapter} {self.title.title()}') for data in response_data["data"]]
        return ([title, "data\\reload_icon.png"] for title in titles)  # list(zip(titles, url_results))


class AutoProviderBaseLike2(AutoProviderBaseLike):
    def __init__(self, title, chapter, chapter_rate, data_folder, cache_folder, provider, specific_provider_website,
                 logo_path, logo_url_or_data, logo_img_format, logo_img_type, num_workers: int = 10):
        super().__init__(title=title, chapter=chapter, chapter_rate=chapter_rate, data_folder=data_folder,
                         cache_folder=cache_folder, provider=provider,
                         specific_provider_website=specific_provider_website, logo_path=logo_path, num_workers=num_workers)
        if not os.path.isfile(os.path.join(data_folder, logo_path.split("/")[-1])):
            try:
                # Using base64 is better as it won't matter if the url is ever changed, otherwise pass the url and
                # img_type="url"
                self._download_logo_image(logo_url_or_data, logo_path.split("/")[-1].split(".")[0],
                                          img_format=logo_img_format, img_type=logo_img_type)
            except Exception as e:
                print(f"An error occurred {e}")
                return

    def _search(self, text: Optional[str] = None):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': f'https://{self.specific_provider_website}',
            'Referer': f'https://{self.specific_provider_website}',
        }

        # Define the URL for the request
        url = f'https://{self.specific_provider_website}/wp-admin/admin-ajax.php'

        # Define the data for the first POST request
        data = {
            'action': 'wp-manga-search-manga',
            'title': text or self.title
        }

        # Send the first POST request
        response = requests.post(url, headers=headers, data=data)

        # Check for a successful response (HTTP status code 200)
        if response.status_code == 200:
            # Parse the JSON response
            response_data = response.json()
            return response_data
        else:
            print(f'Error: {response.status_code}')
        return None

    def _direct_provider(self):
        response_data = self._search()
        url = self._get_url(response_data["data"][0]["url"] + f"chapter-{self.chapter_str}/",
                            f'chapter {self.chapter} {self.title.title()}')
        if url:
            print("Found URL:" + url)  # Concatenate (add-->+) string, to avoid breaking timestamps
            return url
        return None

    def _indirect_provider(self):
        url = self._get_url(
            f'https://{self.specific_provider_website}/manga/{"-".join(self.url_title.lower().split())}/chapter-'
            f'{self.chapter_str}/', f'chapter{self.chapter} {self.title.title()}')
        if url:
            print("Found URL:" + url)  # Concatenate (add-->+) string, to avoid breaking timestamps
            return url
        return None

    def get_search_results(self, text):
        if text is None:
            return True
        response_data = self._search(text)
        titles = [data.get("title") for data in response_data["data"]]
        # urls = [self._get_url(data["url"] + f"chapter-{self.chapter_str}/",
        #                       f'chapter {self.chapter} {self.title.title()}') for data in response_data["data"]]
        return ([title, "data\\reload_icon.png"] for title in titles)  # list(zip(titles, url_results))


class AutoProviderBaseLike3(AutoProviderBaseLike):
    def _search(self, text: Optional[str] = None):
        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'DNT': '1',
            'Host': 'manganato.com',
            'Origin': f'https://{self.specific_provider_website}',
            'Referer': f'https://{self.specific_provider_website}',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-GPC': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
            'X-KL-Ajax-Request': 'Ajax_Request',
            'X-Requested-With': 'XMLHttpRequest'
        }

        # Define the URL for the request
        url = f'https://{self.specific_provider_website}/getstorysearchjson'

        # Define the data for the first POST request
        data = {
            "searchword": text or self.title
        }

        # Send the first POST request
        response = requests.post(url, headers=headers, data=data)

        # Check for a successful response (HTTP status code 200)
        if response.status_code == 200:
            # Parse the JSON response
            response_data = response.json()
            return response_data
        else:
            print(f'Error: {response.status_code}')
        return None

    def _direct_provider(self):
        response_data = self._search()
        if response_data and "data" in response_data and len(response_data["data"]) > 0:
            first_result_url = response_data["data"][0].get("url_story", "") + f"chapter-{self.chapter_str}/"
            url = self._get_url(first_result_url, f'chapter {self.chapter} {self.title.title()}')
            if url:
                print(f"Found URL: {url}")  # Using f-string for better readability
                return url
        return None

    def _indirect_provider(self):
        return None

    def get_search_results(self, text):
        if text is None:
            return True
        response_data = self._search(text)
        if response_data and "data" in response_data:
            titles = [data.get("name") for data in response_data["data"]]
            # Assuming you want to return a generator of tuples (title, image path)
            return ((title, "") for title in titles)
        return iter([])  # Return an empty iterator if no data
