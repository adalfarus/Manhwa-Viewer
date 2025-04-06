"""TBA"""
from PySide6.QtCore import Signal
from aplustools.web.request import UnifiedRequestHandler
from playwright.sync_api import sync_playwright, Error as PlaywrightError, Playwright, Browser
from aplustools.package.timid import TimidTimer
# from aplustools.web.utils import WebPage
from traceback import format_exc
from oaplustools.data.imagetools import OnlineImage
from urllib.parse import urljoin, urlparse
from abc import ABCMeta, abstractmethod
from bs4 import BeautifulSoup
from queue import Queue
import subprocess
import threading
import requests
import urllib3
import json
import uuid
import time
import re
import os

# import aiohttp
# import asyncio
# import aiofiles

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
    register_library_name: str = "Core Library"
    register_library_id: str = "core_lib"
    curr_uuid: str

    @classmethod
    @abstractmethod
    def save_chapter(cls, provider: "CoreProvider", chapter_number: str, chapter_title: str, chapter_img_folder: str,
                     quality_present: _ty.Literal["best_quality", "quality", "size", "smallest_size"],
                     progress_signal: Signal | None = None) -> _ty.Generator[None, None, bool]:
        ...

    @classmethod
    @abstractmethod
    def create_library(cls, library_path: str, name: str) -> None:
        ...

    @classmethod
    @abstractmethod
    def rename_library(cls, library_path: str, new_name: str) -> None:
        ...

    @classmethod
    @abstractmethod
    def get_library_name(cls, library_path: str) -> str:
        ...

    @classmethod
    @abstractmethod
    def is_compatible(cls, library_path: str) -> bool:
        ...


class CoreProvider(metaclass=ABCMeta):
    register_provider_name: str = "Core"
    register_provider_id: str = "core_prov"
    needs_library_path: bool = False  # Remove?
    register_baseclass: str = "CoreProvider"
    use_threading: bool = True
    register_saver: _ty.Type[CoreSaver] | None = None
    # You can find the button popup def in main.py under the MainWindow cls, IT IS NOT THREAD SAFE, DO NOT CALL IN CHAPTER LOADING METHODS
    button_popup: _ty.Callable[[str, str, str, _ty.Literal["Information", "Critical", "Question", "Warning", "NoIcon"], list[str], str, str | None], tuple[str | None, bool]]

    def __init__(self, title: str, chapter: int, library_path: str, logo_folder: str) -> None:
        self._title: str = title
        self._chapter: float = chapter
        self._library_path: str = library_path
        self._current_cache_folder: str | None = None
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

    def load_current_chapter(self, current_cache_folder: str, progress_signal: Signal | None = None) -> _ty.Generator[None, None, bool]:
        self._current_cache_folder = current_cache_folder
        gen = self._load_current_chapter()
        try:
            while True:
                progress = next(gen)
                if progress_signal is not None:
                    progress_signal.emit(progress)
                yield  # Return control briefly
        except StopIteration as e:
            ret_val = e.value
        finally:
            self._current_cache_folder = None
        return bool(ret_val)

    @abstractmethod
    def _load_current_chapter(self) -> _ty.Generator[int, None, bool]:
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

    @classmethod
    def cleanup(cls) -> None:
        return None

    def local_cleanup(self) -> None:
        return None


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
    register_provider_name: str = "Offline"
    register_provider_id: str = "offline_prov"
    needs_library_path: bool = True
    register_baseclass: str = "OfflineProvider"
    saver: _ty.Type[CoreSaver] | None = None

    def get_logo_path(self) -> str:
        return os.path.join(self._logo_folder, "empty.png")


class LibrarySaver(CoreSaver, metaclass=ABCMeta):
    register_library_name: str = "Library Metadata"
    register_library_id: str = "library_metadata"

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
    def _ensure_valid_chapter(cls, provider: CoreProvider, chapter_number: str, chapter_title: str, chapter_img_folder: str,
                     quality_present: _ty.Literal["best_quality", "quality", "size", "smallest_size"]) -> bool:
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
                "cover_path": "./cover.png",
                "large_cover_path": "./large_cover.png"
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
    def rename_library(cls, library_path: str, new_name: str) -> None:
        if not cls._should_work(library_path):
            return

        libmeta_path = os.path.join(library_path, "libmeta.json")
        if not os.path.exists(libmeta_path):
            raise FileNotFoundError(f"libmeta.json not found in {library_path}")

        with open(libmeta_path, "r", encoding="utf-8") as f:
            libmeta = json.load(f)

        libmeta["meta"]["name"] = new_name

        with open(libmeta_path, "w", encoding="utf-8") as f:
            json.dump(libmeta, f, indent=4)

    @classmethod
    def get_library_name(cls, library_path: str) -> str:
        libmeta_path = os.path.join(library_path, "libmeta.json")
        if not os.path.exists(libmeta_path):
            raise FileNotFoundError(f"libmeta.json not found in {library_path}")

        with open(libmeta_path, "r", encoding="utf-8") as f:
            libmeta = json.load(f)

        return libmeta.get("meta", {}).get("name", "")

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
    register_provider_name: str = "Library Metadata Provider"
    register_provider_id: str = "library_metadata_provider"
    needs_library_path: bool = True
    register_baseclass: str = "LibraryProvider"
    register_saver: _ty.Type[CoreSaver] = LibrarySaver

    def __init__(self, title: str, chapter: int, library_path: str, logo_folder: str, logo: ProviderImage,
                 icon: ProviderImage | None) -> None:
        super().__init__(title, chapter, library_path, logo_folder)
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
                    results.append((self.format_title(title), data_path))
        return results

    def format_title(self, title: str) -> str:
        return ' '.join(word[0].upper() + word[1:] if word else '' for word in title.lower().split())

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
                results.append((self.format_title(title), data_path))

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
                            results.append((self.format_title(title), data_path))
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
    register_provider_name: str = "Online"
    register_provider_id: str = "online_prov"
    register_baseclass: str = "OnlineProvider"
    saver: _ty.Type[CoreSaver] | None = None

    # Shared downloader across all OnlineProvider instances
    _shared_request_pool: UnifiedRequestHandler | None = None
    _playwright: Playwright | None = None
    _downloader_lock = threading.Lock()

    def __init__(self, title: str, chapter: int, library_path: str, logo_folder: str, enable_js: bool = False) -> None:
        super().__init__(title, chapter, library_path, logo_folder)
        self._chapter_str: str = ""
        self._chap(chapter)
        self._current_url: str = ""
        self._image_queue: Queue = Queue()
        self._downloaded_images_count: int = 0
        self._total_images: int = 0
        self._download_progress_queue: Queue = Queue()
        self._process_progress_queue: Queue = Queue()

        self._js_enabled: bool
        if self._playwright is None:
            self._js_enabled = False
        else:
            self._js_enabled = enable_js

        self._browser: Browser | None = None  # Moved browser internally to avoid always having a running browser
        self.use_threading = not self._js_enabled  # Playwright can only run efficiently in the main thread I guess? And it also has crazy problems with hallucinating asyncio event loops

    def get_current_url(self) -> str:
        return self._current_url

    def increase_chapter(self, by: float) -> None:
        self._chapter += by
        self._chap(self._chapter)

    def _load_current_chapter(self) -> _ty.Generator[int, None, bool]:
        print("Updating current URL...")
        new_url: str | None = self._get_current_chapter_url()

        if new_url is not None:
            if not is_crawlable("*", new_url):
                print(f"URL {new_url} is not crawlable, returning")
                yield 0
                return False
            self._current_url = new_url
            print(f"Current URL set to: {self._current_url}")

            for progress_or_result in self._cache_current_chapter():
                # print("Handle cache result got: ", progress_or_result)
                if isinstance(progress_or_result, bool):  # Check if it's the final result
                    return progress_or_result
                yield progress_or_result  # Put the progress into the queue
            return False  # Should not happen
        print("Failed to update current URL.")
        yield 0
        return False

    @abstractmethod
    def _get_current_chapter_url(self) -> str | None:
        ...

    def _enable_js(self) -> bool:
        try:  # Try launching Playwright Chromium
            # self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
        except PlaywrightError as e:
            ...  # Hopefully the moving of playwright from main -> provider is possible, so for now I'll leave this here
            # print("Playwright browser not found. Attempting to install Chromium...")
            # try:
            #     subprocess.run(["playwright", "install", "chromium"], check=True)  # Try again after install
            #     # self._playwright = sync_playwright().start()
            #     self._browser = self._playwright.chromium.launch(headless=True)
            # except Exception as install_err:
            #     print("Failed to install Playwright browser:")
            #     print(format_exc())
            #     self._playwright = self._browser = None
            #     return False
            return False
        except Exception:
            print("Error enabling JavaScript:")
            print(format_exc())
            self._playwright = self._browser = None
            return False
        return True

    def _download_using_js(self) -> _ty.Generator[int, None, bool]:
        print("[JS MODE] Using Playwright for image downloads.")
        # Initialize browser once
        with self._downloader_lock:  # We do still need it because of the shared Playwright instance
            if self._browser is None:
                print("[JS MODE] Initializing local Playwright browser...")
                working: bool = self._enable_js()
                if not working:
                    yield 0
                    return False
        page = self._browser.new_page()
        all_image_responses: dict[str, _ty.Any] = {}  # Cache all image responses

        def _capture_all_images(response):
            if response.request.resource_type == "image":
                url = response.url.split("?")[0]
                try:
                    body = response.body()
                    all_image_responses[url] = body
                except Exception as e:
                    print(f"Failed to get image from {url}: {e}")

        page.on("response", _capture_all_images)

        page.goto(self._current_url, wait_until="networkidle")  # Visit current url
        page.evaluate("""
            () => {
                return new Promise(async resolve => {
                    const images = Array.from(document.querySelectorAll('img'));
                    const imageCount = images.length;
                    const totalScrollTime = 12 * 10; // 12 "scroll units" × 10ms base = 120ms total target time
                    const delayPerImage = Math.max(10, Math.floor(totalScrollTime / Math.max(1, imageCount)));
        
                    for (let img of images) {
                        img.scrollIntoView({ behavior: 'instant', block: 'center' });
                        await new Promise(r => setTimeout(r, delayPerImage));
                    }
                    resolve();
                });
            }
        """)  # Scroll through entire page to trigger all lazy loading using js
        page.wait_for_timeout(3000)  # To ensure enough time has passed for all images to be loaded

        soup = BeautifulSoup(page.content(), "html.parser")  # Extract the DOM to be analyzed by _be_picky
        img_tags = self._be_picky(soup)
        print(f"[JS MODE] Found {len(img_tags)} <img> tags after JS render.")
        if not img_tags:
            print("[JS MODE] No images found in _be_picky. Exiting early.")
            yield 0
            return False
        self._total_images = len(img_tags)
        self._downloaded_images_count = 0
        os.makedirs(self._current_cache_folder, exist_ok=True)

        for count, tag in enumerate(img_tags):
            src = tag.get("src")
            if not src:
                print(f"[JS MODE] Skipping img[{count}]: no src attribute.")
                continue
            url_base = src.split("?")[0]
            content = all_image_responses.get(url_base)  # Extract only the responses we want from all responses
            if content:
                filename = f"{str(count).zfill(3)}.{url_base.split('.')[-1]}"
                file_path = os.path.join(self._current_cache_folder, filename)
                with open(file_path, "wb") as f:
                    f.write(content)
                self._downloaded_images_count += 1
                progress = int((self._downloaded_images_count / self._total_images) * 100)
                yield progress
                print(f"[JS MODE] Saved image[{count}] > {filename}")
            else:
                print(f"[JS MODE] Skipped image[{count}] - No matching response for {url_base}")

        page.close()
        print(f"[JS MODE] Captured {len(all_image_responses)} image responses from network.")
        return self._downloaded_images_count > 0

    def _download_using_request(self) -> _ty.Generator[int, None, bool]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # Step 1: Fetch the page HTML
        response: requests.Response = requests.get(self._current_url, headers=headers)
        response.raise_for_status()

        # Step 2: Parse and sanitize HTML (we need to do this because of some providers with invalid html-attributes)
        content = re.sub(r'\s*src="data:[^"]+"', '', response.content.decode("UTF-8"))
        soup: BeautifulSoup = BeautifulSoup(content, 'html.parser')

        # Step 3: Let provider decide which <img> tags are relevant
        img_tags: list[dict] = self._be_picky(soup)
        self._total_images = len(img_tags)
        self._downloaded_images_count = 0

        if not img_tags:
            print("[REQ MODE] No images found after filtering.")
            yield 0
            return False

        # Step 4: Prepare image URLs and file paths
        image_urls: list[str] = []
        file_paths: list[str] = []
        os.makedirs(self._current_cache_folder, exist_ok=True)

        for i, tag in enumerate(img_tags):
            src = tag.get("src")
            if not src:
                print(f"[REQ MODE] Skipping image[{i}] — no src found.")
                continue

            full_url = urljoin(self._current_url, src)
            image_urls.append(full_url)

            ext = full_url.split(".")[-1].split("?")[0]
            filename = f"{str(i).zfill(3)}.{ext}"
            file_path = os.path.join(self._current_cache_folder, filename)
            file_paths.append(file_path)

        # Initialize pool once
        with OnlineProvider._downloader_lock:
            if OnlineProvider._shared_request_pool is None:
                print("[REQ MODE] Initializing global UnifiedRequestHandler...")
                OnlineProvider._shared_request_pool = UnifiedRequestHandler(5, 50, 5, 1.0)

        # Step 5: Download the images using your UnifiedRequestHandler
        print(f"[REQ MODE] Downloading {len(image_urls)} images...")
        handler: UnifiedRequestHandler = OnlineProvider._shared_request_pool
        result = handler.request_many(image_urls, async_mode=True).no_into().await_().no_into_results

        # Step 6: Save images to disk
        for i, (file_path, data) in enumerate(zip(file_paths, result)):
            if data:
                with open(file_path, 'wb') as f:
                    f.write(data)
                self._downloaded_images_count += 1
                progress = int((self._downloaded_images_count / self._total_images) * 100)
                yield progress
                print(f"[REQ MODE] Saved image[{i}] > {os.path.basename(file_path)}")
            else:
                print(f"[REQ MODE] Failed to download image[{i}]: {image_urls[i]}")
        return self._downloaded_images_count > 0

    @abstractmethod
    def _be_picky(self, soup: BeautifulSoup) -> list[dict]:
        ...

    def _cache_current_chapter(self) -> _ty.Generator[int | bool, None, None]:
        timer = TimidTimer()
        if not self._current_url:
            print("URL not found.")
            yield 0
            yield False
            return

        timer.start(1)
        print("Starting inline download with manual generator handling...")
        current_download_progress: int = 0
        combined_progress: int = 0
        yield 0

        try:
            # Select the correct download method
            if self._js_enabled:
                download_gen = self._download_using_js()
            else:
                download_gen = self._download_using_request()
            try:
                while True:
                    progress = next(download_gen)
                    progress_diff = progress - current_download_progress
                    current_download_progress = progress
                    combined_progress += progress_diff
                    yield combined_progress // 2
            except StopIteration as e:
                download_result = e.value
        except Exception as e:
            print(f"An error occurred: {format_exc()}")
            download_result = False
        print(f"Download complete ({timer.end()}), result: {download_result}")
        yield download_result

    @classmethod
    def cleanup(cls) -> None:
        with OnlineProvider._downloader_lock:
            if OnlineProvider._shared_request_pool is not None:
                OnlineProvider._shared_request_pool.shutdown()
                OnlineProvider._shared_request_pool = None
            # if OnlineProvider._playwright is not None:
            #     OnlineProvider._playwright.stop()
            #     OnlineProvider._playwright = None

    def local_cleanup(self) -> None:
        with self._downloader_lock:
            if self._browser is not None:
                self._browser.close()
                self._browser = None

    def __del__(self):
        self.local_cleanup()


class ManhwaLikeProvider(OnlineProvider, metaclass=ABCMeta):
    register_baseclass: str = "ManhwaLikeProvider"
    saver: _ty.Type[CoreSaver] | None = None

    def __init__(self, title: str, chapter: int, library_path: str, logo_folder: str, specific_provider_website: str,
                 logo: ProviderImage, icon: ProviderImage | None, enable_js: bool = False) -> None:
        super().__init__(title, chapter, library_path, logo_folder, enable_js=enable_js)
        self._specific_provider_website: str = specific_provider_website
        self._logo: ProviderImage = logo
        self._logo.save_to_empty(self._logo_folder, discard_after=True)  # Not like we'll need it
        self._icon: ProviderImage | None = icon
        if self._icon is not None:
            self._icon.save_to_empty(self._logo_folder, discard_after=True)  # Not like we'll need it

    @property
    def register_provider_name(self) -> str:
        return self.__class__.__name__.removesuffix("Provider")  # Default impl
    @property
    def register_provider_id(self) -> str: # Default impl
        parts = re.findall(r'[A-Z]+(?=[A-Z][a-z]|[0-9]|$)|[A-Z]?[a-z0-9]+', self.register_provider_name)
        return '_'.join(parts)

    def get_logo_path(self) -> str:
        return self._logo.get_path(self._logo_folder)

    def get_icon_path(self) -> str:
        if self._icon is None:
            return ""
        return self._icon.get_path(self._logo_folder)

    def _search_post_js(self, search_text: str) -> dict | None:
        print("[JS MODE] Performing JS-based POST search.")
        with self._downloader_lock:
            if self._browser is None:
                print("[JS MODE] Initializing local Playwright browser...")
                working: bool = self._enable_js()
                if not working:
                    return None

        page = self._browser.new_page()
        url = f"https://{self._specific_provider_website}/wp-admin/admin-ajax.php"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': f'https://{self._specific_provider_website}',
            'Referer': f'https://{self._specific_provider_website}',
        }

        post_data = f'action=wp-manga-search-manga&title={search_text}'

        response = page.request.post(url, headers=headers, data=post_data)

        if response.status == 200:
            try:
                return response.json()
            except Exception as e:
                print(f"[JS MODE] Failed to parse JSON response: {e}")
        else:
            print(f"[JS MODE] Error: POST returned {response.status}")
        return None

    def _search_web_js(self, search_text: str) -> dict:
        print("[JS MODE] Performing JS-based web search.")
        with self._downloader_lock:
            if self._browser is None:
                print("[JS MODE] Initializing local Playwright browser...")
                working: bool = self._enable_js()
                if not working:
                    return {"success": False, "data": [""]}

        page = self._browser.new_page()
        search_url = f"https://{self._specific_provider_website}?s={search_text}&post_type=wp-manga"

        try:
            page.goto(search_url, wait_until="networkidle")
            page.wait_for_timeout(3000)
            html = page.content()
        except Exception as e:
            print(f"[JS MODE] Failed to load page: {e}")
            return {"success": False, "data": [""]}
        finally:
            page.close()

        soup = BeautifulSoup(html, 'html.parser')
        c_tabs_item_divs = soup.find_all('div', class_='c-tabs-item')

        titles_urls = []
        for div in c_tabs_item_divs:
            for row_c_tabs in div.find_all('div', class_='row c-tabs-item__content'):
                a_tag = row_c_tabs.find('a')
                if a_tag and 'href' in a_tag.attrs and 'title' in a_tag.attrs:
                    titles_urls.append({"title": a_tag['title'], "url": a_tag['href']})

        return {"data": titles_urls}

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
        search_url = f"https://{base_url}/?s={search_text}&post_type=wp-manga"

        try:
            response = requests.get(search_url)
            response.raise_for_status()
        except requests.RequestException:
            return {"success": False, "data": [""]}

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

        if self._js_enabled:
            search_results = self._search_web_js(text)
            if not search_results["data"]:
                return self._search_post_js(text)
            return search_results
        else:
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
            url = response_data["data"][0]["url"].removesuffix("/") + f"/chapter-{self._chapter_str}/"
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
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
            response = requests.get(f"https://{self._specific_provider_website}", timeout=0.1, headers=headers)
            response.raise_for_status()
            return True
        except requests.ReadTimeout:
            return True  # If it times out due to read timeout, it means the website is still up
        except requests.ConnectTimeout:
            return False  # Website was not able to be reached at all
        except requests.ConnectionError as e:
            if "[WinError 10013]" in repr(e):
                print(f"{{IS WORKING}} Blocked by firewall or permissions (WinError 10013) for {self._specific_provider_website}")
                return False
            elif "Max retries exceeded" in repr(e):
                print(f"{self._specific_provider_website} seems to be offline, max retries exceeded")
                return False
            print(f"{{IS WORKING}} Check failed: ", format_exc())
            return False  # Catch-all for any other connection error
        except requests.HTTPError as e:
            print(f"{{IS WORKING}} Faulty response from provider {self._specific_provider_website}, {e}")
            return False
        except requests.RequestException:
            print(f"{{IS WORKING}} Check failed: ", format_exc())
            return False  # Other errors mean it's likely down
