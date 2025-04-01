import json
import os
import shutil
from datetime import datetime

from PIL import Image
from PySide6.QtCore import Signal

from modules.ProviderPlugin import CoreProvider, LibraryProvider, ProviderImage, CoreSaver, LibrarySaver
import typing as _ty


class WebPSaver(LibrarySaver):
    @classmethod
    def save_chapter(cls, provider: CoreProvider, chapter_number: str, chapter_title: str, chapter_img_folder: str,
                     quality_present: _ty.Literal["best_quality", "quality", "size", "smallest_size"],
                     progress_signal: Signal | None = None) -> _ty.Generator[None, None, bool]:
        ret_val = super()._ensure_valid_chapter(provider, chapter_number, chapter_title, chapter_img_folder, quality_present)
        if not ret_val:
            yield
            return False
        chapter_number_str = str(float(chapter_number))
        content_path: str = os.path.join(provider.get_library_path(), cls.curr_uuid)
        chapter_folder = os.path.join(content_path, "chapters", chapter_number_str)

        # Delete old chapter folder if it exists
        if os.path.exists(chapter_folder):
            shutil.rmtree(chapter_folder)

        os.makedirs(chapter_folder, exist_ok=True)

        # webp_quality_map = {
        #     "best_quality": 95,  # Nearly lossless
        #     "quality": 85,  # Great visual quality
        #     "size": 70,  # Noticeable compression, still decent
        #     "smallest_size": 50  # Aggressive compression
        # }
        webp_quality_map = {
            "best_quality": 50,  # Nearly lossless
            "quality": 30,  # Great visual quality
            "size": 10,  # Noticeable compression, still decent
            "smallest_size": 0  # Aggressive compression
        }
        quality = webp_quality_map.get(quality_present, 85)

        image_files = [
            f for f in os.listdir(chapter_img_folder)
            if os.path.isfile(os.path.join(chapter_img_folder, f))
        ]
        total_images = len(image_files)
        if total_images == 0:
            yield
            return False

        for index, img_file in enumerate(image_files):
            src = os.path.join(chapter_img_folder, img_file)
            dst = os.path.join(chapter_folder, os.path.splitext(img_file)[0] + ".webp")

            try:
                with Image.open(src) as img:
                    if img.mode in ("P", "RGBA"):
                        img = img.convert("RGB")
                    img.save(dst, format="WEBP", quality=quality)
            except Exception as e:
                print(f"Failed to process image {img_file}: {e}")

            # Report image progress (0–90%)
            if progress_signal is not None:
                percent = int((index + 1) / total_images * 90)
                progress_signal.emit(percent)
                yield  # Yield control

        # Update data.json
        data_path = os.path.join(content_path, "data.json")
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Missing data.json at {data_path}")

        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Remove any existing entry for the same chapter number
        chapter_number_float = float(chapter_number)
        data["chapters"] = [
            ch for ch in data["chapters"]
            if ch.get("chapter_number") != chapter_number_float
        ]

        pages = []
        for idx in range(total_images):
            page_type = "Story"  # "FrontCover" if idx == 0 else
            pages.append({"image": idx, "type": page_type})

        # Add new entry
        chapter_entry = {
            "chapter_number": chapter_number_float,
            "title": chapter_title,
            "location": os.path.relpath(chapter_folder, content_path),
            "quality_present": quality_present,
            # "series": provider.get_title(),
            "volume": -1,
            "summary": "",
            "date": {
                "year": datetime.now().year,
                "month": datetime.now().month,
                "day": datetime.now().day
            },
            "publisher": "",
            "genre": "",
            "tags": [],
            "pagecount": total_images,
            "languageISO": "en",
            "blackandwhite": False,
            "manga": False,
            "characters": [],
            "web": provider.get_current_url() if hasattr(provider, "get_current_url") else "",
            "teams": [],
            "locations": [],
            "storyarc": "",
            "seriesgroup": "",
            "agerating": "All Ages",
            "communityrating": 0.0,
            "maincharacterorteam": "",
            "pages": pages
        }

        data["chapters"].append(chapter_entry)
        data["chapters"].sort(key=lambda ch: ch["chapter_number"])

        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        if progress_signal is not None:
            progress_signal.emit(100)
            yield  # Yield control
        return True


class WebPLibraryProvider(LibraryProvider):
    saver: _ty.Type[CoreSaver] | None = WebPSaver

    def __init__(self, title: str, chapter: int, library_path: str, logo_folder: str) -> None:
        logo = ProviderImage("logo_webplibrary", "png", "base64", "data:image/png;base64,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")
        icon = ProviderImage("icon_webplibrary", "png", "base64", "data:image/png;base64,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")
        super().__init__(title, chapter, library_path, logo_folder, logo, icon)
        # self.clipping_space = (0, 0, -1, -2)

    def _load_current_chapter(self) -> _ty.Generator[int, None, bool]:
        chapter_number_str = str(float(self._chapter))
        chapter_folder = os.path.join(self._content_path, "chapters", chapter_number_str)

        if not os.path.isdir(chapter_folder):
            print(f"Chapter folder not found: {chapter_folder}")
            yield 0
            return False

        image_files = sorted([
            os.path.join(chapter_folder, img)
            for img in os.listdir(chapter_folder)
            if os.path.isfile(os.path.join(chapter_folder, img))
        ])

        if not image_files:
            print(f"No images found in chapter {chapter_number_str}")
            yield 0
            return False

        # Clear the cache folder
        if os.path.exists(self._current_cache_folder):
            shutil.rmtree(self._current_cache_folder)
        os.makedirs(self._current_cache_folder, exist_ok=True)

        total = len(image_files)

        # Copy images one-by-one and update progress (0-100)
        for idx, src in enumerate(image_files, start=1):
            dst = os.path.join(self._current_cache_folder, os.path.basename(src))
            try:
                shutil.copy2(src, dst)
            except Exception as e:
                print(f"Failed to copy {src} → {dst}: {e}")
                continue

            progress = int((idx / total) * 100)
            yield progress

        print(f"Loaded chapter {self._chapter} with {total} images.")
        return True
