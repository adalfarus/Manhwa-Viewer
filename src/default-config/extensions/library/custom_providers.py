"""TBA"""
from modules.LibraryPlugin import OnlineProvider, ManhwaLikeProvider, ProviderImage, slugify  # Remove ManhwaLike

from urllib.parse import urlencode, urlunparse, quote_plus, urljoin
from bs4 import BeautifulSoup
import requests
import json
import os
import re


class MangaDexProvider(ManhwaLikeProvider):
    register_provider_name: str = "MangaDex"
    register_provider_id: str = "manga_dex"

    def __init__(self, title: str, chapter: int, library_path: str, logo_folder: str) -> None:
        super().__init__(title=title, chapter=chapter, library_path=library_path, logo_folder=logo_folder,
                         specific_provider_website="mangadex.org", logo=ProviderImage("logo_mangadex", "png", "url", ""), icon=None)
        self.clipping_space = (0, 0, -1, -2)

    def can_work(self) -> bool:
        return False


class BatoToProvider(ManhwaLikeProvider):
    register_provider_name: str = "BatoTo"
    register_provider_id: str = "bato_to"

    def __init__(self, title: str, chapter: int, library_path: str, logo_folder: str) -> None:
        super().__init__(title=title, chapter=chapter, library_path=library_path, logo_folder=logo_folder,
                         specific_provider_website="bato.to", logo=ProviderImage("logo_bato", "png", "url", ""), icon=None)
        self.clipping_space = (0, 0, -1, -2)

    def can_work(self) -> bool:
        return False


class MagusToonProvider(ManhwaLikeProvider):
    register_provider_name: str = "MagusToon"
    register_provider_id: str = "magus_toon"

    def __init__(self, title: str, chapter: int, library_path: str, logo_folder: str) -> None:
        super().__init__(title=title, chapter=chapter, library_path=library_path, logo_folder=logo_folder,
                         specific_provider_website="magustoon.net", logo=ProviderImage("logo_magustoon", "png", "url", ""), icon=None)
        self.clipping_space = (0, 0, -1, -2)

    def can_work(self) -> bool:
        return False
