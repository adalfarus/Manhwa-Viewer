"""TBA"""
import errno
import socket

from aplustools.package.timid import TimidTimer
# from aplustools.web.utils import WebPage
from traceback import format_exc
from oaplustools.data.imagetools import OnlineImage
from urllib.parse import urljoin, urlparse
from abc import ABCMeta, abstractmethod
from bs4 import BeautifulSoup
from queue import Queue
import unicodedata
import threading
import requests
import urllib3
import time
import re
import os

import aiohttp
import asyncio
import aiofiles

import collections.abc as _a
import typing as _ty
import types as _ts

# Disable only the specific InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def is_crawlable(useragent: str, url: str) -> bool:
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
                return is_crawlable("*", url)
            return True
        else:
            # If robots.txt does not exist, assume everything is crawlable
            return True
    except Exception as e:
        print(f"An error occurred while checking the robots.txt file: {e}")
        return False  # Return False if there was an error or the robots.txt file couldn't be retrieved


class CoreProvider(metaclass=ABCMeta):
    def __init__(self, title: str, chapter: int, cache_folder: str, logo_folder: str) -> None:
        self._title: str = title
        self._chapter: float = chapter
        self._cache_folder: str = cache_folder
        self._logo_folder: str = logo_folder
        self.clipping_space: tuple[float, float] | None = None

    def set_title(self, new_title):
        self._title = new_title

    def get_title(self):
        return self._title

    def set_chapter(self, new_chapter):
        self._chapter = new_chapter

    def get_chapter(self):
        return self._chapter

    @abstractmethod
    def get_logo_path(self) -> str:
        ...

    def increase_chapter(self, by: float) -> None:
        self._chapter += by

    @abstractmethod
    def load_current_chapter(self, progress_queue: Queue[int] | None = None) -> bool:
        ...

    @abstractmethod
    def get_search_results(self, search_text: str | None) -> bool | list[tuple[str, str]]:
        ...

    def is_working(self) -> bool:
        return True

    def can_work(self) -> bool:
        return True


class OnlineProvider(CoreProvider):
    def __init__(self, title: str, chapter: int, cache_folder: str, logo_folder: str) -> None:
        super().__init__(title, chapter, cache_folder, logo_folder)
        self._chapter_str: str = ""
        self._chap(chapter)
        self._current_url: str = ""
        self._image_queue: Queue = Queue()
        self._downloaded_images_count: int = 0
        self._total_images: int = 0
        self._download_progress_queue: Queue = Queue()
        self._process_progress_queue: Queue = Queue()

    def _chap(self, chapter: float | None = None) -> None:
        chap: float = chapter or self._chapter
        self._chapter = int(chap) if float(chap).is_integer() else chap
        self._chapter_str = str(self._chapter).replace(".", "-")
        return None

    def set_chapter(self, new_chapter):
        self._chapter = new_chapter
        self._chap()

    def get_chapter(self):
        self._chap()
        return self._chapter

    def increase_chapter(self, by: float) -> None:
        self._chapter += by
        self._chap(self._chapter)

    def load_current_chapter(self, progress_queue: Queue[int] | None = None) -> bool:
        print("Updating current URL...")
        new_url: str | None = self._get_current_chapter_url()

        if new_url is not None:
            if not is_crawlable("*", new_url):
                print(f"URL {new_url} is not crawlable, returning")
                return False
            self._current_url = new_url
            print(f"Current URL set to: {self._current_url}")

            for progress_or_result in self._cache_current_chapter():
                print("Handle cache result got: ", progress_or_result)
                if isinstance(progress_or_result, bool):  # Check if it's the final result
                    return progress_or_result
                if progress_queue is not None:
                    progress_queue.put(progress_or_result)  # Put the progress into the queue
            return False  # Should not happen
        print("Failed to update current URL.")
        if progress_queue is not None:
            progress_queue.put(0)
        return False

    def _download_logo_image(self, url_or_data: str, new_name: str, img_format: str, img_type: _ty.Literal["url", "base64"]):
        image: OnlineImage = OnlineImage(url_or_data)
        if img_type == "url":
            image.download_image(self._logo_folder, url_or_data, new_name, img_format)
        elif img_type == "base64":  # Moved data to the back to avoid using keyword arguments
            image.base64(self._logo_folder, new_name, img_format, url_or_data)

    @abstractmethod
    def _get_current_chapter_url(self) -> str | None:
        ...

    async def _download_image_async(self, session: aiohttp.ClientSession, img_tag: dict, new_name: str) -> str:
        url = urljoin(self._current_url, img_tag['src'])
        async with session.get(url) as response:
            if response.status == 200:
                content = await response.read()
                file_extension: str = img_tag['src'].split(".")[-1]
                file_name: str = f"{new_name}.{file_extension}"
                file_path = os.path.join(self._cache_folder, file_name)
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(content)
                self._downloaded_images_count += 1
                progress: int = int((self._downloaded_images_count / self._total_images) * 100)
                self._download_progress_queue.put(progress)
                return file_name
        return img_tag['src'].split("/")[-1]

    async def _download_images_async(self, validated_tags: list[dict]):
        count: int = 0
        async with aiohttp.ClientSession() as session:
            tasks: list[asyncio.Task] = []
            for img_tag in validated_tags:
                new_image_name = f"{str(count).zfill(3)}"
                task = asyncio.create_task(
                    self._download_image_async(session, img_tag, new_image_name))
                tasks.append(task)
                count += 1

            results = await asyncio.gather(*tasks)
            print(f"{len(validated_tags)} images downloaded!")
            return results

    def _download_images(self) -> bool:
        try:
            response: requests.Response = requests.get(self._current_url)
            response.raise_for_status()
            soup: BeautifulSoup = BeautifulSoup(response.text, 'html.parser')
            img_tags: list[dict] = self._be_picky(soup)
            self._total_images = len(img_tags)
            self._downloaded_images_count = 0
            download_result = asyncio.run(self._download_images_async(img_tags))
            print(f"Combined async download result: {download_result}")
            return True
        except Exception as e:
            print(f"An error occurred: {format_exc()}")
            return False

    @abstractmethod
    def _be_picky(self, soup: BeautifulSoup) -> list[dict]:
        ...

    def _cache_current_chapter(self) -> _ty.Generator[int, _ty.Any, bool]:
        timer = TimidTimer()
        if not self._current_url:
            print("URL not found.")
            yield 0
            return False

        timer.start(1)
        download_result_queue: Queue = Queue()
        download_thread = threading.Thread(target=lambda q=download_result_queue: q.put(self._download_images()))
        download_thread.start()
        print(f"Download-Thread startup time: {timer.end(1)}")

        current_download_progress: int = 0
        combined_progress: int = 0
        yield 0

        while True:
            if not download_thread.is_alive() and self._download_progress_queue.empty():
                break
            if not self._download_progress_queue.empty():  # Handle download progress
                new_download_progress = self._download_progress_queue.get()
                progress_diff = new_download_progress - current_download_progress
                combined_progress += progress_diff
                current_download_progress = new_download_progress
            yield combined_progress // 2
            time.sleep(0.1)

        download_result: bool = download_result_queue.get()
        print(f"Download Result: {download_result}, ({timer.end()})")
        return download_result


class ManhwaLikeProvider(OnlineProvider):
    def __init__(self, title: str, chapter: int, cache_folder: str, logo_folder: str, specific_provider_website: str,
                 logo_name: str, logo_url_or_data: str, logo_img_format: str, logo_img_type: _ty.Literal["url", "base64"]) -> None:
        super().__init__(title, chapter, cache_folder, logo_folder)
        self._specific_provider_website: str = specific_provider_website
        self._logo_path: str = os.path.join(logo_folder, f"{logo_name}.{logo_img_format}")
        print(self._logo_path, f"Is file: {os.path.isfile(self._logo_path)}")
        if os.path.isfile(self._logo_path):
            return
        try:
            # Using base64 is better as it won't matter if the url is ever changed, otherwise pass the url and
            # img_type="url"
            self._download_logo_image(logo_url_or_data, logo_name, img_format=logo_img_format, img_type=logo_img_type)
        except Exception as e:
            print(f"An error occurred {e}")
            return

    def get_logo_path(self) -> str:
        return self._logo_path

    def _search_post(self, search_text: str) -> dict | None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': f'https://{self._specific_provider_website}',
            'Referer': f'https://{self._specific_provider_website}',
        }

        # Define the URL for the request
        url = f'https://{self._specific_provider_website}/wp-admin/admin-ajax.php'

        # Define the data for the first POST request
        data = {
            'action': 'wp-manga-search-manga',
            'title': search_text
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

    def _search_web(self, search_text: str) -> dict:
        base_url = self._specific_provider_website
        search_url = f"https://{base_url}?s={search_text}&post_type=wp-manga"

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

    def _search(self, search_text: str) -> dict | None:
        text = search_text

        search_results = self._search_web(text)
        if not search_results["data"]:
            return self._search_post(text)
        return search_results

    def _get_current_chapter_url(self) -> str | None:
        response_data = self._search(self._title)
        if response_data is None:
            return None
        url = response_data["data"][0]["url"] + f"chapter-{self._chapter_str}/"
        if url:
            print("Found URL:" + url)  # Concatenate (add-->+) string, to avoid breaking timestamps
            return url
        return None

    def get_search_results(self, search_text: str | None) -> bool | list[tuple[str, str]]:
        if search_text is None:
            return True
        response_data = self._search(search_text)
        if response_data is None:
            return []
        titles = [data.get("title") for data in response_data["data"]]
        # urls = [self._get_url(data["url"] + f"chapter-{self.chapter_str}/",
        #                       f'chapter {self.chapter} {self.title.title()}') for data in response_data["data"]]
        return [(title, "data\\reload_icon.png") for title in titles]

    def _be_picky(self, soup: BeautifulSoup) -> list[dict]:
        # Find the div with class 'reading-content'
        reading_content_div = soup.find('div', class_='reading-content')

        if not reading_content_div:
            return []

        # Extract all image elements within the div
        images = reading_content_div.find_all('img')

        # Define a regex pattern to filter out base64 images (data:...)
        valid_images = []
        for img in images:
            src = img.get('src', '')
            if src and not re.match(r'^data:.*', src):  # Ensures src is not base64
                valid_images.append(img)

        return valid_images

    def is_working(self) -> bool:
        try:
            response = requests.get(f"https://{self._specific_provider_website}", timeout=0.1)
            response.raise_for_status()
            return True
        except requests.ReadTimeout:
            return True  # If it times out due to read timeout, it means the website is still up
        except requests.ConnectTimeout:
            return False  # Website was not able to be reached at all
        except requests.ConnectionError as e:
            if "[WinError 10013]" in repr(e):
                print(f"Blocked by firewall or permissions (WinError 10013) for {self._specific_provider_website}")
                return False
            print("Is working check failed: ", format_exc())
            return False  # Catch-all for any other connection error
        except requests.RequestException:
            print("Is working check failed: ", format_exc())
            return False  # Other errors mean it's likely down
