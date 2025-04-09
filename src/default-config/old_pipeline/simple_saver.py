import json
import os
import shutil
from datetime import datetime

from PIL import Image
from PySide6.QtCore import Signal

from core.modules.LibraryPlugin import CoreProvider, LibraryProvider, ProviderImage, CoreSaver, LibrarySaver
import typing as _ty


class SimpleImageSaver(LibrarySaver):
    register_library_name: str = "Simple Image Saver"
    register_library_id: str = "simple_image_saver"

    @classmethod
    def save_chapter(cls, provider: CoreProvider, chapter_number: str, chapter_title: str, chapter_img_folder: str,
                     quality_present: str,
                     progress_signal: Signal | None = None) -> _ty.Generator[None, None, bool]:
        ret_val = super()._ensure_valid_chapter(provider, chapter_number, chapter_title, chapter_img_folder, quality_present)
        if not ret_val:
            yield
            return False

        chapter_number_str = str(float(chapter_number))
        content_path = os.path.join(provider.get_library_path(), cls.curr_uuid)
        chapter_folder = os.path.join(content_path, "chapters", chapter_number_str)

        # Clean up and prepare the folder
        if os.path.exists(chapter_folder):
            shutil.rmtree(chapter_folder)
        os.makedirs(chapter_folder, exist_ok=True)

        image_files = sorted([
            os.path.join(chapter_img_folder, f)
            for f in os.listdir(chapter_img_folder)
            if os.path.isfile(os.path.join(chapter_img_folder, f))
        ])

        pages = []
        for idx, file in enumerate(image_files):
            try:
                img = Image.open(file)
                out_path = os.path.join(chapter_folder, f"{idx:03}.webp")
                img.save(out_path, "WEBP", quality=90)
                pages.append({"image": f"{idx:03}.webp", "type": "Story"})
                if progress_signal:
                    progress_signal.emit(10 + int((idx + 1) / len(image_files) * 60))
                    yield
            except Exception as e:
                print(f"Failed to save image {file}: {e}")
                yield
                return False

        # Update or create data.json
        data_path = os.path.join(content_path, "data.json")
        if os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"chapters": []}

        # Remove any old entry
        chapter_number_float = float(chapter_number)
        data["chapters"] = [ch for ch in data["chapters"] if ch.get("chapter_number") != chapter_number_float]

        chapter_entry = {
            "chapter_number": chapter_number_float,
            "title": chapter_title,
            "location": os.path.relpath(chapter_folder, content_path),
            "quality_present": quality_present,
            "volume": -1,
            "summary": "",
            "date": {
                "year": datetime.now().year,
                "month": datetime.now().month,
                "day": datetime.now().day
            },
            "tags": [],
            "pagecount": len(pages),
            "languageISO": "en",
            "blackandwhite": False,
            "pages": pages
        }

        data["chapters"].append(chapter_entry)
        data["chapters"].sort(key=lambda ch: ch["chapter_number"])

        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        if progress_signal:
            progress_signal.emit(100)
            yield
        return True


class SimpleImageLibraryProvider(LibraryProvider):
    register_provider_name = "Simple Image Library"
    register_provider_id = "simple_image_provider"
    register_saver = SimpleImageSaver  # 👈 this connects your new storage engine

    def __init__(self, title: str, chapter: int, library_path: str, logo_folder: str) -> None:
        logo = ProviderImage("logo_simple", "png", "base64", "<insert base64 string or leave empty>")
        icon = ProviderImage("icon_simple", "png", "base64", "<insert base64 string or leave empty>")
        super().__init__(title, chapter, library_path, logo_folder, logo, icon)
        self.clipping_space = None

    def _load_current_chapter(self) -> _ty.Generator[int, None, bool]:
        chapter_number_str = str(float(self._chapter))
        chapter_folder = os.path.join(self._content_path, "chapters", chapter_number_str)

        if not os.path.isdir(chapter_folder):
            print(f"Chapter folder not found: {chapter_folder}")
            yield 0
            return False

        if os.path.exists(self._current_cache_folder):
            shutil.rmtree(self._current_cache_folder)
        os.makedirs(self._current_cache_folder, exist_ok=True)

        image_files = sorted([
            f for f in os.listdir(chapter_folder)
            if f.lower().endswith(".webp") or f.lower().endswith(".png") or f.lower().endswith(".jpg")
        ])

        if not image_files:
            print(f"No images found in chapter folder: {chapter_folder}")
            yield 0
            return False

        for idx, fname in enumerate(image_files):
            src = os.path.join(chapter_folder, fname)
            dst = os.path.join(self._current_cache_folder, f"{idx:03}.webp")
            shutil.copy(src, dst)
            yield int((idx + 1) / len(image_files) * 100)

        print(f"Loaded {len(image_files)} images from {chapter_folder}")
        yield 100
        return True
