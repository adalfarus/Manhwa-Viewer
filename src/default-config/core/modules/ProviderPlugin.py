"""TBA"""
from aplustools.package.timid import TimidTimer
# from aplustools.web.utils import WebPage
from traceback import format_exc
from oaplustools.data.imagetools import OnlineImage
from urllib.parse import urljoin, urlparse
from abc import ABCMeta, abstractmethod
from bs4 import BeautifulSoup
from queue import Queue
import threading
import requests
import urllib3
import json
import uuid
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


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)  # Collapse multiple spaces/tabs
    text = re.sub(r'[^\w\s-]', '', text)   # Remove all non-url-safe characters except - and _
    text = text.strip()
    return "-".join(text.split())


class CoreSaver(metaclass=ABCMeta):
    curr_uuid: str

    @classmethod
    @abstractmethod
    def save_chapter(cls, provider: "CoreProvider",chapter_number: str, chapter_title: str, chapter_img_folder: str,
                     quality_present: _ty.Literal["best_quality", "quality", "size", "smallest_size"],
                     progress_queue: Queue[int] | None = None) -> bool:
        ...

    @classmethod
    @abstractmethod
    def create_library(cls, library_path: str, name: str) -> None:
        ...

    @classmethod
    @abstractmethod
    def is_compatible(cls, library_path: str) -> bool:
        ...


class CoreProvider(metaclass=ABCMeta):
    needs_library_path: bool = False
    register_baseclass: str = "CoreProvider"
    saver: _ty.Type[CoreSaver] | None = None

    def __init__(self, title: str, chapter: int, library_path: str, cache_folder: str, logo_folder: str) -> None:
        self._title: str = title
        self._chapter: float = chapter
        self._library_path: str = library_path
        self._cache_folder: str = cache_folder
        self._logo_folder: str = logo_folder
        self.clipping_space: tuple[int, int] | None = None

    def set_title(self, new_title):
        self._title = new_title

    def get_title(self):
        return self._title

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

    def set_library_path(self, new_library_path: str) -> None:
        self._library_path = new_library_path

    def get_library_path(self) -> str:
        return self._library_path

    @abstractmethod
    def get_logo_path(self) -> str:
        ...

    @abstractmethod
    def get_icon_path(self) -> str:
        ...

    def increase_chapter(self, by: float) -> None:
        self._chapter += by

    @abstractmethod
    def load_current_chapter(self, progress_queue: Queue[int] | None = None) -> bool:
        ...

    @abstractmethod
    def get_search_results(self, search_text: str | None) -> bool | list[tuple[str, str]]:
        ...

    def _download_logo_image(self, url_or_data: str, new_name: str, img_format: str, img_type: _ty.Literal["url", "base64"]):
        image: OnlineImage = OnlineImage(url_or_data)
        if img_type == "url":
            image.download_image(self._logo_folder, url_or_data, new_name, img_format)
        elif img_type == "base64":  # Moved data to the back to avoid using keyword arguments
            image.base64(self._logo_folder, new_name, img_format, url_or_data)

    def is_working(self) -> bool:
        return True

    def can_work(self) -> bool:
        return True


class ProviderImage:
    def __init__(self, name: str, img_format: str, img_type: _ty.Literal["url", "base64"], url_or_data: str) -> None:
        self._name: str = name
        self._img_format: str = img_format
        self._img_type: str = img_type
        self._url_or_data: str = url_or_data

    def get_file_name(self) -> str:
        return f"{self._name}.{self._img_format}"

    def get_path(self, from_folder: str) -> str:
        return os.path.join(from_folder, self.get_file_name())

    def save_to(self, folder_path: str) -> None:
        if self._url_or_data == "":
            return
        try:
            image: OnlineImage = OnlineImage(self._url_or_data)
            if self._img_type == "url":
                image.download_image(folder_path, self._url_or_data, self._name, self._img_format)
            elif self._img_type == "base64":  # Moved data to the back to avoid using keyword arguments
                image.base64(folder_path, self._name, self._img_format, self._url_or_data)
        except Exception as e:
            print(f"An error occurred {e}")
            return

    def save_to_empty(self, folder_path: str, discard_after: bool = False) -> None:
        if os.path.isfile(self.get_path(folder_path)):
            return
        self.save_to(folder_path)
        if discard_after:
            self.discard_data()

    def discard_data(self) -> None:
        self._url_or_data = ""


class OfflineProvider(CoreProvider, metaclass=ABCMeta):
    needs_library_path: bool = True
    register_baseclass: str = "OfflineProvider"
    saver: _ty.Type[CoreSaver] | None = None

    def get_logo_path(self) -> str:
        return os.path.join(self._logo_folder, "empty.png")


class LibrarySaver(CoreSaver, metaclass=ABCMeta):
    @classmethod
    def _should_work(cls, library_path: str) -> bool:
        if not os.path.exists(library_path) or not os.path.isdir(library_path):
            return False
        return True

    @classmethod
    def _find_content_folder(cls, content_name: str, library_path: str) -> str:
        # Find the content folder by title
        if not cls._should_work(library_path):
            return ""
        for content_id in os.listdir(library_path):
            folder = os.path.join(library_path, content_id)
            data_path = os.path.join(folder, "data.json")
            if not os.path.exists(data_path):
                continue
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data["metadata"].get("title", "").lower() == content_name.lower():
                    return content_id
            except Exception:
                continue
        return ""

    @classmethod
    def save_chapter(cls, provider: CoreProvider, chapter_number: str, chapter_title: str, chapter_img_folder: str,
                     quality_present: _ty.Literal["best_quality", "quality", "size", "smallest_size"],
                     progress_queue: Queue[int] | None = None) -> bool:
        if not cls._should_work(provider.get_library_path()):
            return False
        cid = cls._find_content_folder(provider.get_title(), provider.get_library_path())
        if cid != "":
            cls.curr_uuid = cid
            return True
        content_id = str(uuid.uuid4())
        content_path = os.path.join(provider.get_library_path(), content_id)
        os.makedirs(content_path, exist_ok=True)

        data = {
            "metadata": {
                "title": provider.get_title(),
                "description": "",
                "uuid": content_id,
                "tags": [],
                "logo_img": "",
                "img": ""
            },
            "chapters": []
        }

        with open(os.path.join(content_path, "data.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        # Reset search cache
        cls._reset_search_meta(provider.get_library_path())
        cls._update_lib_meta(
            provider.get_library_path(),
            provider.get_title(),
            content_id,
            cls.__name__
        )
        cls.curr_uuid = content_id
        return True

    @classmethod
    def create_library(cls, library_path: str, name: str) -> None:
        if not cls._should_work(library_path):
            return
        os.makedirs(library_path, exist_ok=True)

        # Create libmeta.json
        libmeta_path = os.path.join(library_path, "libmeta.json")
        if not os.path.exists(libmeta_path):
            libmeta = {
                "meta": {
                    "name": name,
                    "library_manager": cls.__name__
                },
                "content": {}
            }
            with open(libmeta_path, "w", encoding="utf-8") as f:
                json.dump(libmeta, f, indent=4)

        # Create empty searchmeta.json
        searchmeta_path = os.path.join(library_path, "searchmeta.json")
        if not os.path.exists(searchmeta_path):
            with open(searchmeta_path, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=4)

    @classmethod
    def is_compatible(cls, library_path: str) -> bool:
        libmeta_path = os.path.join(library_path, "libmeta.json")
        if not os.path.exists(libmeta_path):
            return True
        try:
            with open(libmeta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            return meta.get("meta", {}).get("library_manager") == cls.__name__
        except Exception:
            return False

    @classmethod
    def _reset_search_meta(cls, library_path: str) -> None:
        with open(os.path.join(library_path, "searchmeta.json"), "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)

    @classmethod
    def _update_lib_meta(cls, library_path: str, title: str, uuid_str: str, manager_name: str) -> None:
        libmeta_path = os.path.join(library_path, "libmeta.json")

        if os.path.exists(libmeta_path):
            try:
                with open(libmeta_path, "r", encoding="utf-8") as f:
                    libmeta = json.load(f)
            except Exception:
                libmeta = {}
        else:
            libmeta = {}

        # Set meta block
        libmeta.setdefault("meta", {})
        libmeta["meta"]["name"] = os.path.basename(library_path)
        libmeta["meta"]["library_manager"] = manager_name

        # Set content block
        libmeta.setdefault("content", {})
        libmeta["content"][uuid_str] = title

        with open(libmeta_path, "w", encoding="utf-8") as f:
            json.dump(libmeta, f, indent=4)


class LibraryProvider(CoreProvider, metaclass=ABCMeta):
    needs_library_path: bool = True
    register_baseclass: str = "LibraryProvider"
    saver: _ty.Type[CoreSaver] = LibrarySaver

    def __init__(self, title: str, chapter: int, library_path: str, cache_folder: str, logo_folder: str,
                 logo: ProviderImage, icon: ProviderImage | None) -> None:
        super().__init__(title, chapter, library_path, cache_folder, logo_folder)
        self._logo: ProviderImage = logo
        self._logo.save_to_empty(self._logo_folder, discard_after=True)  # Not like we'll need it
        self._icon: ProviderImage | None = icon
        if self._icon is not None:
            self._icon.save_to_empty(self._logo_folder, discard_after=True)  # Not like we'll need it
        self._search_meta_path: str = os.path.join(self._library_path, "searchmeta.json")
        self._lib_meta_path = os.path.join(self._library_path, "libmeta.json")
        self._content_path = self._find_content_folder()

    def set_library_path(self, new_library_path: str) -> None:
        super().set_library_path(new_library_path)
        self._content_path = self._find_content_folder()

    def _find_content_folder(self) -> str:
        # Find the content folder by title
        if not os.path.exists(self._library_path) or not os.path.isdir(self._library_path):
            return ""
        for content_id in os.listdir(self._library_path):
            folder = os.path.join(self._library_path, content_id)
            data_path = os.path.join(folder, "data.json")
            if not os.path.exists(data_path):
                continue
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data["metadata"].get("title", "").lower() == self._title.lower():
                    return folder
            except Exception:
                continue
        return ""

    def get_logo_path(self) -> str:
        return self._logo.get_path(self._logo_folder)

    def get_icon_path(self) -> str:
        if self._icon is None:
            return ""
        return self._icon.get_path(self._logo_folder)

    def _resolve_titles_from_ids(self, ids: list[str]) -> list[tuple[str, str]]:
        results = []
        for content_id in ids:
            data_path = os.path.join(self._library_path, content_id, "data.json")
            if os.path.exists(data_path):
                with open(data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    title = data["metadata"].get("title", content_id)
                    results.append((title, data_path))
        return results

    def get_search_results(self, search_text: str | None) -> bool | list[tuple[str, str]]:
        if search_text is None:
            return True

        search_key = search_text.lower()
        meta = self._load_search_meta()
        if search_key in meta:
            result_ids = meta[search_key]
            return self._resolve_titles_from_ids(result_ids)

        matched_ids = []
        results = []

        # Prefer searching libmeta.json if available
        libmeta = self._load_lib_meta()
        content_map = libmeta.get("content", {}) if libmeta else {}

        for content_id, title in content_map.items():
            if search_key in title.lower():
                matched_ids.append(content_id)
                data_path = os.path.join(self._library_path, content_id, "data.json")
                results.append((title, data_path))

        # Fallback to full scan if libmeta doesn't help
        if not matched_ids:
            for content_id in os.listdir(self._library_path):
                path = os.path.join(self._library_path, content_id)
                if not os.path.isdir(path):
                    continue
                data_path = os.path.join(self._library_path, content_id, "data.json")
                if not os.path.exists(data_path):
                    continue
                try:
                    with open(data_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        title = data["metadata"].get("title", content_id)
                        if search_key in title.lower():  # Match against title
                            matched_ids.append(content_id)
                            results.append((title, data_path))
                except Exception:
                    continue

        meta[search_key] = matched_ids
        with open(self._search_meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=4)
        return results

    def _load_search_meta(self) -> dict:
        if not os.path.exists(self._search_meta_path):
            return {}
        try:
            with open(self._search_meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _load_lib_meta(self) -> dict:
        if not os.path.exists(self._lib_meta_path):
            return {}
        try:
            with open(self._lib_meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}


class OnlineProvider(CoreProvider, metaclass=ABCMeta):
    register_baseclass: str = "OnlineProvider"
    saver: _ty.Type[CoreSaver] | None = None

    def __init__(self, title: str, chapter: int, library_path: str, cache_folder: str, logo_folder: str) -> None:
        super().__init__(title, chapter, library_path, cache_folder, logo_folder)
        self._chapter_str: str = ""
        self._chap(chapter)
        self._current_url: str = ""
        self._image_queue: Queue = Queue()
        self._downloaded_images_count: int = 0
        self._total_images: int = 0
        self._download_progress_queue: Queue = Queue()
        self._process_progress_queue: Queue = Queue()

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
            return self._downloaded_images_count > 0
        except Exception as e:
            print(f"An error occurred: {format_exc()}")
            return False

    @abstractmethod
    def _be_picky(self, soup: BeautifulSoup) -> list[dict]:
        ...

    def _cache_current_chapter(self) -> _ty.Generator[int | bool, _ty.Any, None]:
        timer = TimidTimer()
        if not self._current_url:
            print("URL not found.")
            yield 0
            yield False

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
        yield download_result


class ManhwaLikeProvider(OnlineProvider, metaclass=ABCMeta):
    register_baseclass: str = "ManhwaLikeProvider"
    saver: _ty.Type[CoreSaver] | None = None

    def __init__(self, title: str, chapter: int, library_path: str, cache_folder: str, logo_folder: str,
                 specific_provider_website: str, logo: ProviderImage, icon: ProviderImage | None) -> None:
        super().__init__(title, chapter, library_path, cache_folder, logo_folder)
        self._specific_provider_website: str = specific_provider_website
        self._logo: ProviderImage = logo
        self._logo.save_to_empty(self._logo_folder, discard_after=True)  # Not like we'll need it
        self._icon: ProviderImage | None = icon
        if self._icon is not None:
            self._icon.save_to_empty(self._logo_folder, discard_after=True)  # Not like we'll need it

    def get_logo_path(self) -> str:
        return self._logo.get_path(self._logo_folder)

    def get_icon_path(self) -> str:
        if self._icon is None:
            return ""
        return self._icon.get_path(self._logo_folder)

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
        if not response_data.get("success", True):
            url = f"https://{self._specific_provider_website}/manga/{slugify(self._title)}/" + f"chapter-{self._chapter_str}/"
        else:
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
