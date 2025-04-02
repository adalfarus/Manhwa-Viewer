import json
import os
import platform
import shutil
import tempfile
from datetime import datetime

from PIL import Image
from PySide6.QtCore import Signal

from core.modules.ProviderPlugin import CoreProvider, LibraryProvider, ProviderImage, CoreSaver, LibrarySaver
import typing as _ty

import ffmpeg


def encode_chapter(images: list[str], output_path: str, fps: int = 30, crf: int = 0,
                   preset: _ty.Literal["veryslow", "slow", "medium", "fast", "veryfast"] = "veryslow",
                   tune: _ty.Literal["film", "psnr", "animation", "grain", "tune"] = "grain",
                   progress_signal=None):
    """
    Encode a chapter using a list of images, each displayed for exactly 1 frame.

    :param images: List of image paths to encode into a video.
    :param output_path: Path for the output MKV file.
    :param fps: Frames per second (default: 30). Higher FPS reduces time per image.
    :param crf: Constant Rate Factor (default: 0). Lower is higher quality, range is 0–51.
    :param preset: Encoding speed preset. Slower presets provide better compression (default: "veryslow").
                   Options: "veryslow", "slow", "medium", "fast", "veryfast".
    :param tune: Encoder tuning for content type (default: "grain").
                 Options: "film", "psnr", "animation", "grain", "tune".
    """
    # Create a temporary directory in the system temp folder
    temp_dir = tempfile.mkdtemp()

    try:
        # Copy the images to the temporary directory and rename them in a sequential order
        for i, image_path in enumerate(images):
            new_image_name = f'image_{i + 1:03d}.png'
            new_image_path = os.path.join(temp_dir, new_image_name)
            shutil.copy(image_path, new_image_path)

            if progress_signal:
                percent = 20 + int((i + 1) / len(images) * 20)
                progress_signal.emit(percent)
                yield  # Yield control

        # Create the ffmpeg input pattern based on the copied images
        input_pattern = os.path.join(temp_dir, 'image_%03d.png')

        # Encode the images into a video
        (
            ffmpeg
            .input(input_pattern, framerate=fps)
            # Scale the images to ensure width and height are divisible by 2
            .filter('scale', 'trunc(iw/2)*2', 'trunc(ih/2)*2')
            .filter('format', 'yuv420p')  # Set the pixel format to yuv420p to avoid deprecated format
            .output(output_path, vcodec='libx265', r=fps, pix_fmt='yuv420p', crf=crf, preset=preset, tune=tune)
            .overwrite_output()
            .run()
        )
        if progress_signal:
            progress_signal.emit(90)
            yield  # Yield control
        print(f"Encoded chapter to {output_path}")
    except ffmpeg.Error as e:
        print(f"An error occurred while encoding the chapter: {e.stderr.decode()}")
    finally:
        # Clean up temporary directory and files after encoding is complete
        shutil.rmtree(temp_dir)
        print(f"Temporary files deleted from {temp_dir}")


class DeepCSaver(LibrarySaver):
    register_library_name: str = "DeepC (FFx265)"
    register_library_id: str = "deep_c_lib"
    old_quality_settings = {
        "best_quality":    {"fps": 1,   "crf": 18, "preset": "veryslow", "tune": "film"},
        "quality":         {"fps": 30,  "crf": 23, "preset": "slow",     "tune": "psnr"},
        "size":            {"fps": 60,  "crf": 28, "preset": "medium",   "tune": "animation"},
        "smallest_size":   {"fps": 120, "crf": 35, "preset": "fast",     "tune": "grain"},
    }
    quality_settings = {
        "best_quality": {"fps": 1, "crf": 16, "preset": "veryslow", "tune": "psnr"},
        "quality": {"fps": 30, "crf": 23, "preset": "slow", "tune": "psnr"},
        "size": {"fps": 60, "crf": 28, "preset": "veryslow", "tune": "psnr"},
        "smallest_size": {"fps": 120, "crf": 35, "preset": "veryslow", "tune": "psnr"},
    }

    old_if = """        if len(sizes) > 1:
            # Combine vertically
            max_width = max(w for w, h in sizes)
            total_height = sum(img.height for img in images)
            combined = Image.new("RGB", (max_width, total_height))
            y_offset = 0
            for img in images:
                if img.width != max_width:
                    img = img.crop((0, 0, max_width, img.height))  # Crop excess width
                combined.paste(img, (0, y_offset))
                y_offset += img.height

            # Ideal portrait aspect ratio
            target_ratio = 9 / 16
            best_chunk_height = None
            smallest_diff = float("inf")

            for n_slices in range(1, total_height + 1):
                if total_height % n_slices != 0:
                    continue  # Only allow clean splits
                chunk_height = total_height // n_slices
                aspect = max_width / chunk_height
                diff = abs(aspect - target_ratio)
                if diff < smallest_diff:
                    smallest_diff = diff
                    best_chunk_height = chunk_height
                if diff < 0.01:
                    break  # Close enough

            num_chunks = total_height // best_chunk_height
            resized_paths = []
            for i in range(num_chunks):
                top = i * best_chunk_height
                bottom = top + best_chunk_height
                box = (0, top, max_width, bottom)
                out_path = os.path.join(chapter_folder, f"{i:03}.png")
                combined.crop(box).save(out_path)
                resized_paths.append(out_path)"""

    @classmethod
    def save_chapter(cls, provider: CoreProvider, chapter_number: str, chapter_title: str, chapter_img_folder: str,
                     quality_present: _ty.Literal["best_quality", "quality", "size", "smallest_size"],
                     progress_signal: Signal | None = None) -> _ty.Generator[None, None, bool]:
        ret_val = super()._ensure_valid_chapter(provider, chapter_number, chapter_title, chapter_img_folder, quality_present)
        if not ret_val:
            yield
            return False
        if shutil.which("ffmpeg") is None:
            system = platform.system()
            install_help = "-> Unknown operating system"
            if system == "Windows":
                install_help = "-> Download from https://ffmpeg.org/download.html and add it to PATH."
            elif system == "Darwin":
                install_help = "-> Try: brew install ffmpeg"
            elif system == "Linux":
                install_help = "-> Try: sudo apt install ffmpeg or sudo dnf install ffmpeg"
            message = ("FFmpeg is not installed or not found in your system's PATH.",
                       "DeepCLibrary requires FFmpeg to function correctly.",
                       "Please install it and ensure it's accessible via the command line.",
                       "",
                       "How to install ffmpeg:",
                       install_help)
            for part in message:
                print(part)
            yield
            return False
        chapter_number_str = str(float(chapter_number))
        content_path: str = os.path.join(provider.get_library_path(), cls.curr_uuid)
        chapter_folder = os.path.join(content_path, "chapters", chapter_number_str)
        output_file = os.path.join(content_path, "chapters", f"{chapter_number_str}.mkv")

        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Cleanup if folder already exists
        if os.path.exists(chapter_folder):
            shutil.rmtree(chapter_folder)
        os.makedirs(chapter_folder, exist_ok=True)

        # Load and normalize image sizes
        image_files = sorted([
            os.path.join(chapter_img_folder, f)
            for f in os.listdir(chapter_img_folder)
            if os.path.isfile(os.path.join(chapter_img_folder, f))
        ])

        images = []
        sizes = set()
        for idx, file in enumerate(image_files):
            try:
                img = Image.open(file)
                images.append(img)
                sizes.add(img.size)
            except Exception as e:
                print(f"Failed to load image {file}: {e}")

            if progress_signal:
                percent = 10 + int((idx + 1) / len(image_files) * 5)
                progress_signal.emit(percent)
                yield  # Yield control

        if not images:
            yield
            return False  # Nothing to save

        # Determine common size (crop to smallest WxH)
        if len(sizes) > 1:
            # Combine vertically
            max_width = max(w for w, h in sizes)
            total_height = sum(img.height for img in images)
            combined = Image.new("RGB", (max_width, total_height))
            y_offset = 0
            for img in images:
                # Align width by padding (optional) or cropping (safe)
                if img.width != max_width:
                    aspect_ratio = img.height / img.width
                    new_height = int(max_width * aspect_ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                combined.paste(img, (0, y_offset))
                y_offset += img.height

            # Ideal 9:16 aspect ratio
            target_ratio = 9 / 16
            best_height = total_height
            best_chunk_height = None
            for n in range(1, len(images) + 20):
                chunk_height = total_height // n
                if chunk_height == 0:
                    break
                if abs((max_width / chunk_height) - target_ratio) < 0.2:  # Acceptable deviation
                    best_chunk_height = chunk_height
                    break
            if best_chunk_height is None:
                best_chunk_height = total_height // len(images)

            num_chunks = total_height // best_chunk_height
            resized_paths = []
            for i in range(num_chunks):
                top = i * best_chunk_height
                bottom = top + best_chunk_height
                box = (0, top, max_width, bottom)
                out_path = os.path.join(chapter_folder, f"{i:03}.png")
                combined.crop(box).save(out_path)
                resized_paths.append(out_path)

                if progress_signal:
                    progress = 15 + int((i + 1) / num_chunks * 5)
                    progress_signal.emit(progress)
                    yield  # Yield control
        else:
            resized_paths = []
            for idx, img in enumerate(images):
                out_path = os.path.join(chapter_folder, f"{idx:03}.png")
                img.save(out_path)
                resized_paths.append(out_path)
                if progress_signal:
                    progress = 15 + int((idx + 1) / len(images) * 5)
                    progress_signal.emit(progress)
                    yield  # Yield control

        # Encode chapter video
        settings = cls.quality_settings[quality_present]
        for _ in encode_chapter(resized_paths, output_file, **settings, progress_signal=progress_signal):
            yield  # Yield control from encode chapter

        # Cleanup original images
        shutil.rmtree(chapter_folder)

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
        total_images = len(resized_paths)
        for idx in range(total_images):
            page_type = "Story"  # "FrontCover" if idx == 0 else
            pages.append({"image": idx, "type": page_type})

        chapter_entry = {
            "chapter_number": chapter_number_float,
            "title": chapter_title,
            "location": os.path.relpath(output_file, content_path),
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


def extract_chapter_images(chapter_file: str, output_dir: str, fps: int) -> None:
    """
    Extracts frames from a chapter MKV file and saves them as images.

    :param chapter_file: Path to the MKV chapter file (e.g., 'chapter_1.mkv').
    :param output_dir: Directory where the extracted images will be saved (default: 'test_images').
    :param fps: The frame rate at which to extract images (default: 1 frame per second).
    """
    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Define the output image format (e.g., test_images/frame001.jpg)
    output_pattern = os.path.join(output_dir, 'frame_%03d.png')

    try:
        # Extract frames from the video file
        (
            ffmpeg
            .input(chapter_file, r=fps)  # Input video with the specified frame rate (fps)
            .output(output_pattern, start_number=0)  # Correct output format with sequence
            .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
        )
        print(f"Images extracted from {chapter_file} to {output_dir}")
    except ffmpeg.Error as e:
        print(f"An error occurred while extracting images: {e.stderr.decode()}")


class DeepCLibraryProvider(LibraryProvider):
    register_provider_name: str = "DeepC Lib (FFmpeg)"
    register_provider_id: str = "deep_c_lib"
    saver = DeepCSaver

    def __init__(self, title: str, chapter: int, library_path: str, logo_folder: str) -> None:
        logo = ProviderImage("logo_deepclibrary", "png", "base64", "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAZAAAADICAYAAADGFbfiAAABg2lDQ1BJQ0MgcHJvZmlsZQAAKJF9kT1Iw0AcxV9TpSIVh3aw4pChOtlFRRxLFYtgobQVWnUwufQLmjQkKS6OgmvBwY/FqoOLs64OroIg+AHiLjgpukiJ/0sKLWI8OO7Hu3uPu3eA0Kox1eyLA6pmGZlkQswXVsXAK/yIIIQAIhIz9VR2MQfP8XUPH1/vYjzL+9yfY0gpmgzwicRxphsW8Qbx7Kalc94nDrOKpBCfE08adEHiR67LLr9xLjss8MywkcvME4eJxXIPyz3MKoZKPEMcVVSN8oW8ywrnLc5qrcE69+QvDBa1lSzXaY4hiSWkkIYIGQ1UUYOFGK0aKSYytJ/w8I86/jS5ZHJVwcixgDpUSI4f/A9+d2uWpqfcpGAC6H+x7Y9xILALtJu2/X1s2+0TwP8MXGldf70FzH2S3uxq0SNgeBu4uO5q8h5wuQOMPOmSITmSn6ZQKgHvZ/RNBSB0Cwyuub119nH6AOSoq+Ub4OAQmChT9rrHuwd6e/v3TKe/H4Xecq7MoAFZAAAABmJLR0QAAAAAAAD5Q7t/AAAACXBIWXMAAC4jAAAuIwF4pT92AAAAB3RJTUUH6QMZEwgL1kXMhgAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAAzhSURBVHja7d19kFV1Hcfxz+/uLuvlQQHB4J6FyBhIwURtNB11RgMVuIdFrbXRyVKZxsSHScc/arQwp/5CLUXLFGusJqUag7OLD2iN+Sw+0CiOBSLIngskCQqyLnDPrz+WUFj24e7uPY/v14x/yN695/f97vmdz/nde+65EgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJBlhhYAyLzCskaZ3EzJzpQ0vp/PtkZWj8qaB7Wp+CoBEiXHWyjphnh30bwl2d+pvW2R3m/ayWwEYn9cuUnSLZJyIW3xBZXL87R57lsECAHSk50yukit7nJmKhATDc23yNofxWAkj8pvc6WmMgFCgPRklYa3naLVTbuZwUAECt6bMpoSw5Gtk1+cKBmb1Nbm2Luqbpq259vleDs0aukw2gGEdvL5pBzPxjQ8JOloOc2BHO82AgQ9Gar63Edq8NbRCqCKxjwyQY5nJX0tISO+Xo63hwBBz6y+IMezKniX0QxggDV416mm9t0EjrxWjmd10it1BAh6ZvSAHK9EI4AB4iz7i6x+nugaNm9K1HulBEi0xnYstS2fxwH6Fx4/lcwF6ajFS8zVWQRILHaY5oAQAfpoXMuZkvlhiirKqeD9ngBBhSECoGJB8HTqajK6RFOWDCJAUMnStZUmABXNmQ2prW17/h0CBBVNBxW8ubQB6IWGJXn1/75Vsa6QAEGlS9dHaALQCza/Pv0h6S0iQFDpsvxWmgD06Kj0h6TmEyCo1E20AOj2zPw6mkCAoMtVSMskmgB0eWa+MDO1FrzTCZCk8F1zwH/W3hXNQIKH+GMAXaoNeXtrJE2X1RCZuiNl7bzQtmzshfwRkqo051pJ1+67OVuYTqD5wKH8vVYK8XvbjLlWrcXPnkjukrRY0uJ9nxqv8om4mc4KJA0rEwDRG/dxuHfZPTA8Djq269IQRjCVAEkDo7+Guj2nZRpNBw4S2BmxGYvNrc7yn4IAqWjHVchXfgRFmg50cjotIECSp+S+F+7ZDRMFOMQrAUfRBAIEPf91uJQX6HxiNZomxANXYcV7oowJbVsFb5SMPVtWX5LMZOU0WdJIWQ2VNFTSIBl9LKud6rgE5j1JayS7Rsqtkr/rH1JTObG9znr9vTFlySBty18iozMkfVXSaEkjJe2QzDbJrpb0mkyuRa2zX6riSIZycCBA0LN8lQ6Wc2U0X9L0g18bkNkfXocKtMMlHb7v/yZ1/L7peLCTl+R9+kiZPykXLNTGOStjGBbJrn8gLylvDw7X1sYd3fTqahndLqlO2/Vpfw50hGSPkDRB0mzZ4GY5+3uxS8Z8X63FXzOdCRAkleP9TNIPQtqakWyTAtO0/0DS+Vp66o+D+tw76nRPqQU5OSe9Jun4AdjCYFl7rxzvXkntsqaoUvFJJiQBgrgbufxw5cvrJY2IfCzW3inHu1PSOg1vO0arm3ZTfyyM1sTl9Vo7q12S1OA9LqtzqhVXMnZFR6iaq+QXf8kkTTbeRE/vimOr8uUPY3HwPNDR2p5vr/oXAWW9/kq0lf+tccu/KMezVQyPgxP1Hjme1biWrzBZCRDERYP3/9uuHBnzkY6X41k1ePOoPwZjCcprI9lyEKxUwXuTiUuAIPpVx4uy+kWixmx1nxzveerPMKMpHaFvuV0QAYKIwqMk6ZSEjv5UOc3vUn/W9+HmgIlMgCD88HhD0thkF2EnyPH+Sf2Z35ctE5oAQVgKzZcrxnfrrNCX1eBdTP2ZD5E/M7EJEITB2MWpqsfqD9SfeRfSAgIE1T9TeyOldT1P/VlfWXuPMcEJEFTX1JTWdSr1Z31lrXOZ3gQIqqWh+f50r66ab6Z+gABBNVh7RcoL/An1Z1zBc5noBAgA9OXoxBeqESAYcA3eJSFu7WEpN1ljxg5Szp4sq/C+A7rgjaL+yN0mq89reFu9pNMkvR3eIkzjmezxxt14E8l849BfWDHAdrcN0/tNOyVJviRppaSpGtd8rgJb/atkjC1K+i31R8R3P721SEmS9IKkY1RYOkMm90QIIxjGXGcFggE/M7Mh3DHV3LH/4HmwjcXHJX1S/TrNDOqPzGld/qTUuEJSOxMRBEgy5au+Bb94fQ8vL9xY/WN4l7cnyXr9Yaw+Xugh3W5lGoIAQd/U1DwawlbGUH9sV8EvMwnAeyDom092btGgqi8EBlN/TBmzg0kgyZ+9Sl19UzwrEAAACBAAAAECACBAAAAECACAAAEAgAABABAgAAACBABAgAAACBAAAAgQAAABAgAgQAAABAgAgAABAIAAAQAQIAAAAgQAQIAAAAgQAAAIEAAAAQIAiLNaWoBDcjxL/QBYgQAACBAAAAECACBAAAAECAAABAgAoFq4jBcA+sppmSYFr1d9O75rWIEAAFKDAAEAECAAAAIEAECAAAAIEAAACBAAQH/wORAcWkyvO6d+gBUIAIAAAQBkES9hoW9GLxmqQfkdVd7KBvnuBOoHWIEAAAgQAAABAgAAAQIAIEAAAAQIAIAAAQCAAAEAECAAAAIEAECAAAAIEAAACBAAAAECACBA0FmZFgAgQNAX22kBAAIEfbGOFgAgQFA5o5dpAgACJA0K3vxQtxeYJ2g60Mk2WkCAJHFFsCjU7ZVeaY5tL+ryh2V6X8h6/dHaQgsIkGRxvIXhb3RBEN+GBJOzfaaZ9fpNQ4Qbj897g9aeSICgew3e45JuCHmrO6MNzJZp3R8/cteEMDk3U39sfTu6g7aWh7q9gnd11/uBvT/Lh8Za0uHgsFiSlx0yTrY8XbncfFl7rGwkk2ReNz9bLaMpVT7Dfk7SkG4ecFH1T2/MWuqPbMX9oHz30m4eUYxu8be3RTW14b2cbHSXHO8ayVwps+tF1dbVa2/t12V1X0gjiO3nwViBdDo45XdJwb9kzN2y9tjIxlFyH+5mh34shBEMluO91vmfF+TkeO3hTFzTTP2R+ZYK3o8jrb8rm89fH8FWJ0n2b7L5XdpTuy3E8JCMPFYgqGSHeaaHn98hG8pLaifI8Wxkfdj4ygrqj3Q/XCDHW8CEjFjZ3M4KBL3X6p7Zw8/9bDSii4sIsl4/JKO7M1PrpuIzBAh6OTHMH3v5yB0p78R/qT/zk+Hjbk6irs5IEzbGeXAESOxWH8WLe/U4G8xMdR9sMIP6s8629vCAD1Lfgt1tx8Z5eARInLTVHNHrx5Yan0t1L0qNr1N/5nV/ue7wtrHpXoCZt/R+0844D5EAic3OkpupD2Z9VNkJmmlM54mnvkn9kO8+1e3PVzftlvRsautvLU6J+xAJkFiEh76r1tmVX5paKi5T1B84HHhBt5cwUz8ODJkzUlnX3j2fS8IwCZDo06OoVve+fkygYek6ILxaR/2Q7JW9fmi+Jl33JbPBidpywX8IEPSQHXVHyi+29Pt5ausKqZk4fbl0Nev1p3JlMefeXj927ax21R82PCWvRkxK0vtfBEgkBwqtlu8atZ43MFeRbDhvk3LmuET3JGdP7vPEyXr9aZMLnIp/Z92MD2XaBif6qOAPrVOruyZRfyr21rB3k/J4ldypA/68G4tvqm5oPpE9qds7QhvnrKR+yOpybWws9el3W5va5LtGSbvdu9ED8t2cdNbexGU9e2xYO4mdJd81Ks2t3geD1p/1yb4J9FRCuvKifNdo/fnbqR+SvVQl9zf9fhrfHSMbnJ6AgrfIf7VGre4ViT2sxX6EHd/DcUNC+7tGQW6GNs3eEPqWRy0dpvrcBkkjYtiXD2U1USV3K/X3aU6EcX+usqSa0DpSW1fQhvM2DfjzFpZdJWPidtuT7dKeifIvSPzdBliBDHwmr5AJjpfvGvnupEjCQ5K2Nu6Q746U1ZAeb84Ynqdl2gbLd4dXNTyov/98t1ZG14VwCvuAfNdUJTwkqTTnHvmukQmOV+QvbZkVGt5WL98dkYbwYAVSud3q+Ja4bZLeldVLytmX1TpsRSJev2xoOU5BeZGMOTPErTbL6kaV3Lepf8DmRPVXIB0vBXYY13yuArtUUv0AbuFX8t3vRbIfjG0+SSa4PaT9YJWUu0z+7FWpPF1mxZBhTsskmeAKWZ0jaVo/ny2Qtc8ql1uuwC6O/Rl2kusPO0AOPPgeoxp7lawul1TJVU9WRvcoZ27We8V4fVXv+OYRKgffkcx0SWdL6uvnSqykx2TNgyoVH8rE6y0cRYGkBX+EAQJ8Bu+BAAAIEAAAAQIAIEAAAAQIAAAECACAAAEAECAAAAIEAECAAABAgAAACBAAAAECACBAAAAECAAABAgAgAABABAgAAACBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQY/8DGjb7aTJgTO0AAAAASUVORK5CYII=")
        icon = ProviderImage("icon_deepclibrary", "png", "base64", "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIIAAACCCAYAAACKAxD9AAAAwHpUWHRSYXcgcHJvZmlsZSB0eXBlIGV4aWYAAHjabVBBEsMgCLzzij5BARWfYxo70x/0+UUhmdh0Z1xxN1kR6J/3Cx4DGBk4Fck156DgyhWbFhIMbXIMPHlC0L246nAaqBLpTv5D9u8PPZ4BtjWt0jXo6ca2GpU9X36C/GIaHY1696DqQYRmRA9o9qyQq5TrE7YeVogtGMSytn07F53envQeQuwUKSgTZWuAxkpATQtS1gOaPBSeCnqYDuTfnA7AF+9rWRd4UI59AAABhGlDQ1BJQ0MgcHJvZmlsZQAAeJx9kT1Iw0AYht+mSqVUHNpBxSFDdbKLijiWKhbBQmkrtOpgcukfNGlIUlwcBdeCgz+LVQcXZ10dXAVB8AfEXXBSdJESv0sKLWI8uLuH97735e47QGjVmGr2xQFVs4xMMiHmC6ti4BV+jCBMa1Bipp7KLubgOb7u4eP7XYxnedf9OQaVoskAn0gcZ7phEW8Qz25aOud94girSArxOfGkQRckfuS67PIb57LDAs+MGLnMPHGEWCz3sNzDrGKoxDPEUUXVKF/Iu6xw3uKs1hqsc0/+wlBRW8lyneYYklhCCmmIkNFAFTVYiNGukWIiQ+cJD/+o40+TSyZXFYwcC6hDheT4wf/gd2/N0vSUmxRKAP0vtv0xDgR2gXbTtr+Pbbt9AvifgSut66+3gLlP0ptdLXoEDG0DF9ddTd4DLneA4SddMiRH8tMUSiXg/Yy+qQCEb4Hgmtu3zjlOH4Ac9Wr5Bjg4BCbKlL3u8e6B3r79W9Pp3w9Wj3Kbl/XgcgAADXZpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+Cjx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IlhNUCBDb3JlIDQuNC4wLUV4aXYyIj4KIDxyZGY6UkRGIHhtbG5zOnJkZj0iaHR0cDovL3d3dy53My5vcmcvMTk5OS8wMi8yMi1yZGYtc3ludGF4LW5zIyI+CiAgPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIKICAgIHhtbG5zOnhtcE1NPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvbW0vIgogICAgeG1sbnM6c3RFdnQ9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZUV2ZW50IyIKICAgIHhtbG5zOmRjPSJodHRwOi8vcHVybC5vcmcvZGMvZWxlbWVudHMvMS4xLyIKICAgIHhtbG5zOkdJTVA9Imh0dHA6Ly93d3cuZ2ltcC5vcmcveG1wLyIKICAgIHhtbG5zOnRpZmY9Imh0dHA6Ly9ucy5hZG9iZS5jb20vdGlmZi8xLjAvIgogICAgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIgogICB4bXBNTTpEb2N1bWVudElEPSJnaW1wOmRvY2lkOmdpbXA6OGVkNWJhNWQtYzg3NS00YjExLTg5MjAtYzZjN2ExODBmMzI5IgogICB4bXBNTTpJbnN0YW5jZUlEPSJ4bXAuaWlkOjdmMTQ1M2IxLTdhYjItNGM4YS1hNDMyLWQxZTJjYzdlZTM0MSIKICAgeG1wTU06T3JpZ2luYWxEb2N1bWVudElEPSJ4bXAuZGlkOmQ5NDIxODkwLTQ4ZDQtNDdiYi1iMTUwLWYxNjg1ZjA2YzBkNiIKICAgZGM6Rm9ybWF0PSJpbWFnZS9wbmciCiAgIEdJTVA6QVBJPSIyLjAiCiAgIEdJTVA6UGxhdGZvcm09IldpbmRvd3MiCiAgIEdJTVA6VGltZVN0YW1wPSIxNzQyOTI5NDYyMjM2MTI0IgogICBHSU1QOlZlcnNpb249IjIuMTAuMzYiCiAgIHRpZmY6T3JpZW50YXRpb249IjEiCiAgIHhtcDpDcmVhdG9yVG9vbD0iR0lNUCAyLjEwIgogICB4bXA6TWV0YWRhdGFEYXRlPSIyMDI1OjAzOjI1VDIwOjA0OjIyKzAxOjAwIgogICB4bXA6TW9kaWZ5RGF0ZT0iMjAyNTowMzoyNVQyMDowNDoyMiswMTowMCI+CiAgIDx4bXBNTTpIaXN0b3J5PgogICAgPHJkZjpTZXE+CiAgICAgPHJkZjpsaQogICAgICBzdEV2dDphY3Rpb249InNhdmVkIgogICAgICBzdEV2dDpjaGFuZ2VkPSIvIgogICAgICBzdEV2dDppbnN0YW5jZUlEPSJ4bXAuaWlkOjRlYTZhYmFiLTAxYjQtNDg1MC1iMjE4LTRmOTg0YmM4MzAzYyIKICAgICAgc3RFdnQ6c29mdHdhcmVBZ2VudD0iR2ltcCAyLjEwIChXaW5kb3dzKSIKICAgICAgc3RFdnQ6d2hlbj0iMjAyNS0wMy0yNVQyMDowNDoyMiIvPgogICAgPC9yZGY6U2VxPgogICA8L3htcE1NOkhpc3Rvcnk+CiAgPC9yZGY6RGVzY3JpcHRpb24+CiA8L3JkZjpSREY+CjwveDp4bXBtZXRhPgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgCjw/eHBhY2tldCBlbmQ9InciPz4Bd6qdAAAABmJLR0QAAAAAAAD5Q7t/AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH6QMZEwQWGfbvUwAADPtJREFUeNrtXUuPnFcRPafHjp0QhRBsENMrSPgVEAm2gTHkscgmEhtACASRIiTEymsWeSxYAAskggIEyZFmAlsLJX+BZSKkyCOiSTCRELHHmT4s7q1bde/32SSoTXo8dRR7xjPd3+Peepw6VV8HSCQSiUQikUgkEolEIpFIJBKJRCKRSCQSiUQikUgkEolEIpFIJBKJOVy+fPlUrkIikUgkEoljhYsXv3I2VyGRSCQSiUQikUgkEolEIpFIJBKJRCKRSCQSiUQikUgkEolEIvHfwLUfcPmKoC2oHp4EIJV/k35CHQLX34Te/TFzGyqWl0SdgigQBESUlVsB+9/k8TKE7UsCTgMEpPozltuhyhkFghJkhiEBR/+A3v7WyTOK8y8Id30BlHw7qLpG9XsBBIszXX3pSbz/uz8ci4ggnQKotvFu2Sz/TSJEuXEcCfj7hRNjDNzeleqa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")
        super().__init__(title, chapter, library_path, logo_folder, logo, icon)
        self.clipping_space = None

    def _load_current_chapter(self, progress_queue=None) -> bool:
        if shutil.which("ffmpeg") is None:
            system = platform.system()
            install_help = "-> Unknown operating system"
            if system == "Windows":
                install_help = "-> Download from https://ffmpeg.org/download.html and add it to PATH."
            elif system == "Darwin":
                install_help = "-> Try: brew install ffmpeg"
            elif system == "Linux":
                install_help = "-> Try: sudo apt install ffmpeg or sudo dnf install ffmpeg"
            message = ("FFmpeg is not installed or not found in your system's PATH.",
                       "DeepCLibrary requires FFmpeg to function correctly.",
                       "Please install it and ensure it's accessible via the command line.",
                       "",
                       "How to install ffmpeg:",
                       install_help)
            for part in message:
                print(part)
            return False
        chapter_number_str = str(float(self._chapter))  # Match saved mkv filename
        data_path = os.path.join(self._content_path, "data.json")

        if not os.path.isfile(data_path):
            print("Missing data.json")
            return False

        try:
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Failed to read data.json: {e}")
            return False

        # Locate chapter entry
        chapter_data = next(
            (ch for ch in data.get("chapters", []) if str(float(ch["chapter_number"])) == chapter_number_str),
            None
        )
        if not chapter_data:
            print(f"Chapter {chapter_number_str} not found in data.json")
            return False

        video_path = os.path.join(self._content_path, chapter_data["location"])
        if not os.path.isfile(video_path):
            print(f"Chapter video not found: {video_path}")
            return False

        # Determine FPS from quality
        preset_fps = {
            "best_quality": 1,
            "quality": 30,
            "size": 60,
            "smallest_size": 120
        }
        quality = chapter_data.get("quality_present", "quality")
        fps = preset_fps.get(quality, 30)

        # Clear cache folder
        if os.path.exists(self._current_cache_folder):
            shutil.rmtree(self._current_cache_folder)
        os.makedirs(self._current_cache_folder, exist_ok=True)

        # Extract frames into cache
        try:
            extract_chapter_images(video_path, output_dir=self._current_cache_folder, fps=fps)
        except Exception as e:
            print(f"Failed to extract chapter images: {e}")
            return False

        # Count how many images were extracted
        image_files = sorted([
            f for f in os.listdir(self._current_cache_folder)
            if os.path.isfile(os.path.join(self._current_cache_folder, f))
        ])
        if not image_files:
            return False

        total = len(image_files)
        for idx in range(total):
            if progress_queue:
                progress_queue.put(int((idx + 1) / total * 100))

        print(f"Loaded and extracted {total} images for chapter {chapter_number_str}")
        return True
