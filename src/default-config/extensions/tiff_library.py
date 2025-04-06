import json
import os
import shutil
from datetime import datetime

from PIL import Image
from PySide6.QtCore import Signal

from core.modules.LibraryPlugin import CoreProvider, LibraryProvider, ProviderImage, CoreSaver, LibrarySaver
import typing as _ty


class TiffSaver(LibrarySaver):
    register_library_name: str = "Lossless Tiff"
    register_library_id: str = "lossless_tiff_lib"

    @classmethod
    def save_chapter(cls, provider: CoreProvider, chapter_number: str, chapter_title: str, chapter_img_folder: str,
                     quality_present: _ty.Literal["best_quality", "quality", "size", "smallest_size"],
                     progress_signal: Signal | None = None) -> _ty.Generator[None, None, bool]:
        ret_val = super()._ensure_valid_chapter(provider, chapter_number, chapter_title, chapter_img_folder, quality_present)
        if not ret_val:
            yield
            return False

        chapter_number_str = str(float(chapter_number))
        content_path = os.path.join(provider.get_library_path(), cls.curr_uuid)
        chapters_path = os.path.join(content_path, "chapters")
        os.makedirs(chapters_path, exist_ok=True)

        tiff_path = os.path.join(chapters_path, f"{chapter_number_str}.tiff")

        # Remove old .tiff if it exists
        if os.path.exists(tiff_path):
            os.remove(tiff_path)

        compression_map = {
            "best_quality": "none",          # uncompressed
            "quality": "tiff_lzw",           # lossless but smaller
            "size": "tiff_deflate",          # balanced
            "smallest_size": "jpeg",         # lossy, small
        }
        compression = compression_map.get(quality_present, "tiff_deflate")

        image_files = sorted([
            f for f in os.listdir(chapter_img_folder)
            if os.path.isfile(os.path.join(chapter_img_folder, f))
        ])
        total_images = len(image_files)
        if total_images == 0:
            yield
            return False

        frames = []
        for idx, img_file in enumerate(image_files):
            src = os.path.join(chapter_img_folder, img_file)
            try:
                with Image.open(src) as img:
                    img = img.convert("RGB")
                    frames.append(img.copy())
            except Exception as e:
                print(f"[TIFF] Failed to process image {img_file}: {e}")
                continue

            if progress_signal:
                progress_signal.emit(int((idx + 1) / total_images * 90))
                yield  # Yield control

        if not frames:
            print("[TIFF] No images processed successfully for .tiff.")
            yield
            return False

        try:
            save_kwargs = {
                "save_all": True,
                "append_images": frames[1:],
                "compression": compression
            }
            if compression == "jpeg":
                save_kwargs["quality"] = 80

            frames[0].save(tiff_path, **save_kwargs)
        except Exception as e:
            print(f"[TIFF] Failed to save TIFF: {e}")
            yield
            return False

        # Update data.json
        data_path = os.path.join(content_path, "data.json")
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Missing data.json at {data_path}")

        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        chapter_number_float = float(chapter_number)
        data["chapters"] = [
            ch for ch in data["chapters"]
            if ch.get("chapter_number") != chapter_number_float
        ]

        pages = []
        for idx in range(total_images):
            page_type = "Story"  # "FrontCover" if idx == 0 else
            pages.append({"image": idx, "type": page_type})

        chapter_entry = {
            "chapter_number": chapter_number_float,
            "title": chapter_title,
            "location": os.path.relpath(tiff_path, content_path),
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

        if progress_signal:
            progress_signal.emit(100)
            yield  # Yield control

        return True


class TiffLibraryProvider(LibraryProvider):
    register_provider_name: str = "Lossless Tiff Lib"
    register_provider_id: str = "lossless_tiff_lib"
    register_saver: _ty.Type[CoreSaver] | None = TiffSaver

    def __init__(self, title: str, chapter: int, library_path: str, logo_folder: str) -> None:
        logo = ProviderImage("logo_tifflibrary", "png", "base64", "data:image/png;base64,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")
        icon = None  # ProviderImage("icon_tifflibrary", "png", "base64", "data:image/png;base64,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")
        super().__init__(title, chapter, library_path, logo_folder, logo, icon)
        self.clipping_space = (0, 0, -1, -2)

    def _load_current_chapter(self) -> _ty.Generator[int, None, bool]:
        chapter_number_str = str(float(self._chapter))
        tiff_path = os.path.join(self._content_path, "chapters", f"{chapter_number_str}.tiff")

        if not os.path.isfile(tiff_path):
            print(f"[TIFF] Chapter TIFF not found at: {tiff_path}")
            yield 0
            return False

        # Clear and prepare cache
        if os.path.exists(self._current_cache_folder):
            shutil.rmtree(self._current_cache_folder)
        os.makedirs(self._current_cache_folder, exist_ok=True)

        try:
            with Image.open(tiff_path) as img:
                total = getattr(img, "n_frames", 1)

                for i in range(total):
                    img.seek(i)
                    page = img.convert("RGB")
                    output_path = os.path.join(self._current_cache_folder, f"{i+1:03}.jpg")
                    page.save(output_path, format="JPEG")

                    progress = int(((i + 1) / total) * 100)
                    yield progress

        except Exception as e:
            print(f"[TIFF] Failed to read or extract TIFF: {e}")
            return False

        print(f"[TIFF] Loaded chapter {self._chapter} with {total} pages from TIFF.")
        return True
