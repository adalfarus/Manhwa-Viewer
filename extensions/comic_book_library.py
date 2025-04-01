import json
import tempfile
import uuid
from datetime import datetime

from PIL import Image

from modules.ProviderPlugin import CoreProvider, LibraryProvider, ProviderImage, CoreSaver, LibrarySaver
import typing as _ty

import zipfile
import rarfile
import py7zr
import tarfile
import os
import shutil
from xml.etree import ElementTree as ET

SUPPORTED_FORMATS = {
    "cbz": zipfile.ZipFile,
    "cb7": py7zr.SevenZipFile,
    "cbr": rarfile.RarFile,
    "cbt": tarfile.open,
    # "cba": handled separately if needed
}


def create_archive(archive_path, image_folder, format: str = "cbz"):
    format = format.lower()
    if format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format: {format}")

    if format == "cbz":
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for root, _, files in os.walk(image_folder):
                for file in sorted(files):
                    full_path = os.path.join(root, file)
                    arcname = os.path.relpath(full_path, image_folder)  # Keep folder structure
                    archive.write(full_path, arcname=arcname)

    elif format == "cb7":
        with py7zr.SevenZipFile(archive_path, 'w') as archive:
            archive.writeall(image_folder, arcname="")

    elif format == "cbt":
        with tarfile.open(archive_path, "w") as archive:
            for root, _, files in os.walk(image_folder):
                for file in sorted(files):
                    full_path = os.path.join(root, file)
                    arcname = os.path.relpath(full_path, image_folder)
                    archive.add(full_path, arcname=arcname)

    elif format == "cbr":
        raise NotImplementedError("Creating .cbr requires 'rar' binary. Use cbz/cb7 instead.")


class ComicBookSaver(LibrarySaver):
    archive_format = "cbz"

    @classmethod
    def save_chapter(cls, provider, chapter_number, chapter_title, chapter_img_folder,
                     quality_present, progress_queue=None) -> bool:
        ret_val = super()._ensure_valid_chapter(provider, chapter_number, chapter_title, chapter_img_folder, quality_present)
        if not ret_val:
            return False

        # Use same path as StdSaver would
        chapter_number_str = str(float(chapter_number))
        content_path = os.path.join(provider.get_library_path(), cls.curr_uuid)
        chapters_path = os.path.join(content_path, "chapters")
        os.makedirs(chapters_path, exist_ok=True)

        archive_path = os.path.join(chapters_path, f"{chapter_number_str}.cbz")

        # Resize + save images into temp /pages/
        with tempfile.TemporaryDirectory() as temp_dir:
            pages_path = os.path.join(temp_dir, "pages")
            os.makedirs(pages_path, exist_ok=True)

            scale_map = {
                "best_quality": 1.0,
                "quality": 0.75,
                "size": 0.5,
                "smallest_size": 0.25
            }
            scale = scale_map.get(quality_present, 1.0)

            image_files = sorted([
                f for f in os.listdir(chapter_img_folder)
                if os.path.isfile(os.path.join(chapter_img_folder, f))
            ])
            total_images = len(image_files)
            if total_images == 0:
                return False

            for idx, img_file in enumerate(image_files):
                src = os.path.join(chapter_img_folder, img_file)
                dst = os.path.join(pages_path, img_file)
                try:
                    with Image.open(src) as img:
                        if scale == 1.0:
                            img.save(dst)
                        else:
                            resized = img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.LANCZOS)
                            resized.save(dst)
                except Exception as e:
                    print(f"Error resizing {img_file}: {e}")

                if progress_queue:
                    progress_queue.put(int((idx + 1) / total_images * 90))

            # Add ComicInfo.xml with metadata
            cls._write_comicinfo_xml(
                temp_dir,
                title=provider.get_title(),
                chapter_number=chapter_number,
                chapter_title=chapter_title,
                quality=quality_present
            )

            # Create archive
            try:
                create_archive(archive_path, temp_dir, format=cls.archive_format)
            except Exception as e:
                print(f"Failed to create .cbz archive: {e}")
                return False

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
            "location": os.path.relpath(archive_path, content_path),
            "quality_present": quality_present,
            "series": provider.get_title(),
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
        if progress_queue is not None:
            progress_queue.put(100)
        return True

    @staticmethod
    def _write_comicinfo_xml(temp_dir, title, chapter_number, chapter_title, quality):
        import xml.etree.ElementTree as ET

        root = ET.Element("ComicInfo")
        ET.SubElement(root, "Series").text = title
        ET.SubElement(root, "Number").text = str(float(chapter_number))
        ET.SubElement(root, "Title").text = chapter_title
        ET.SubElement(root, "Format").text = quality
        ET.SubElement(root, "LanguageISO").text = "en"
        ET.SubElement(root, "Volume").text = "1"

        tree = ET.ElementTree(root)
        tree.write(os.path.join(temp_dir, "ComicInfo.xml"), encoding="utf-8", xml_declaration=True)


def extract_archive(archive_path, extract_to):
    ext = archive_path.lower().split(".")[-1]
    if ext == "cbz":
        with zipfile.ZipFile(archive_path, 'r') as archive:
            archive.extractall(extract_to)
    elif ext == "cb7":
        with py7zr.SevenZipFile(archive_path, 'r') as archive:
            archive.extractall(path=extract_to)
    elif ext == "cbr":
        with rarfile.RarFile(archive_path, 'r') as archive:
            archive.extractall(path=extract_to)
    elif ext == "cbt":
        with tarfile.open(archive_path, 'r') as archive:
            archive.extractall(path=extract_to)
    else:
        raise ValueError(f"Unsupported format: {ext}")


class ComicBookLibraryProvider(LibraryProvider):
    saver = ComicBookSaver

    def __init__(self, title: str, chapter: int, library_path: str, logo_folder: str) -> None:
        logo = ProviderImage("logo_comicbooklibrary", "png", "base64", "data:image/png;base64,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")
        super().__init__(title, chapter, library_path, logo_folder, logo, None)
        self.clipping_space = (0, 0, -1, -2)

    def _load_current_chapter(self, progress_queue=None) -> bool:
        chapter_number_str = str(float(self._chapter))
        chapter_archive = os.path.join(self._content_path, "chapters", f"{chapter_number_str}.cbz")

        if not os.path.isfile(chapter_archive):
            print(f"[CBZ] Chapter archive not found: {chapter_archive}")
            return False

        # Extract archive into temp dir
        with tempfile.TemporaryDirectory() as temp_extract_folder:
            try:
                extract_archive(chapter_archive, temp_extract_folder)
            except Exception as e:
                print(f"[CBZ] Failed to extract {chapter_archive}: {e}")
                return False

            pages_folder = os.path.join(temp_extract_folder, "pages")
            if not os.path.isdir(pages_folder):
                print(f"[CBZ] No 'pages/' directory found in archive.")
                return False

            image_files = sorted([
                os.path.join(pages_folder, f)
                for f in os.listdir(pages_folder)
                if os.path.isfile(os.path.join(pages_folder, f)) and f.lower()
            ])

            if not image_files:
                print(f"[CBZ] No images found in {chapter_archive}")
                return False

            # Prepare cache folder
            if os.path.exists(self._current_cache_folder):
                shutil.rmtree(self._current_cache_folder)
            os.makedirs(self._current_cache_folder, exist_ok=True)

            total = len(image_files)

            for idx, src in enumerate(image_files, start=1):
                dst = os.path.join(self._current_cache_folder, os.path.basename(src))
                try:
                    shutil.copy2(src, dst)
                except Exception as e:
                    print(f"Failed to copy {src} → {dst}: {e}")
                    continue

                if progress_queue:
                    progress = int((idx / total) * 100)
                    progress_queue.put(progress)

        print(f"[CBZ] Loaded chapter {self._chapter} from archive with {total} images.")
        return True
