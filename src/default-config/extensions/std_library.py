import json
import os
import shutil
from datetime import datetime

from PIL import Image
from PySide6.QtCore import Signal

from core.modules.LibraryPlugin import CoreProvider, LibraryProvider, ProviderImage, CoreSaver, LibrarySaver
import typing as _ty


class StdSaver(LibrarySaver):
    register_library_name: str = "Std"
    register_library_id: str = "std_lib"

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

        # Determine resize scale
        scale_map = {
            "best_quality": 1.0,
            "quality": 0.75,
            "size": 0.5,
            "smallest_size": 0.25
        }
        scale = scale_map.get(quality_present, 1.0)

        image_files = [
            f for f in os.listdir(chapter_img_folder)
            if os.path.isfile(os.path.join(chapter_img_folder, f))
        ]
        total_images = len(image_files)
        if total_images == 0:
            yield
            return False

        # Copy + resize images into the chapter folder
        for index, img_file in enumerate(image_files):
            src = os.path.join(chapter_img_folder, img_file)
            dst = os.path.join(chapter_folder, img_file)

            try:
                with Image.open(src) as img:
                    if scale == 1.0:
                        img.save(dst)
                    else:
                        new_size = (int(img.width * scale), int(img.height * scale))
                        resized = img.resize(new_size, Image.Resampling.LANCZOS)
                        resized.save(dst)
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


class StdLibraryProvider(LibraryProvider):
    register_provider_name: str = "Std Lib"
    register_provider_id: str = "std_lib"
    register_saver: _ty.Type[CoreSaver] | None = StdSaver

    def __init__(self, title: str, chapter: int, library_path: str, logo_folder: str) -> None:
        logo = ProviderImage("logo_stdlibrary", "png", "base64", "data:image/png;base64,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")
        super().__init__(title, chapter, library_path, logo_folder, logo, None)
        self.clipping_space = (0, 0, -1, -2)

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
