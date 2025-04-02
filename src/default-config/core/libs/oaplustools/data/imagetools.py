from typing import Type, Union, Tuple, Optional, List
from oaplustools.web.utils import get_user_agent
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, urljoin
from PIL import Image, ImageFilter
# from aiohttp import ClientSession
from requests import Session
from io import BytesIO
import functools
import mimetypes
import warnings
import requests
# import asyncio
import base64
import os
import re


class ImageManager:
    def __init__(self, base_location: Optional[str] = None, use_async: bool = False):
        self.base_location = base_location
        self.images: List[Union[OfflineImage, OnlineImage]] = []
        self.use_async = use_async

    def add_image(self, image_class: Type[Union['OfflineImage', 'OnlineImage']], *args, **kwargs) -> int:
        """
        Creates and adds an image objects.

        Parameters:
            image_class -- The image class for the object
            args -- The positional arguments for the image_class
            kwargs -- The keyword arguments for the image_class
        """

        kwargs["base_location"] = kwargs.get("base_location") or self.base_location
        if self.use_async:
            kwargs["_use_async"] = True
            # asyncio.run(self._add_image_async(image_class, *args, **kwargs))
        else:
            kwargs["_use_async"] = False
            self.images.append(image_class(*args, **kwargs))
        return len(self.images) - 1

    # async def _add_image_async(self, image_class: Type[Union['OfflineImage', 'OnlineImage']], *args, **kwargs):
    #     self.images.append(await self.create_async(image_class, *args, **kwargs))
    #
    # @staticmethod
    # async def create_async(cls, *args, **kwargs):
    #     # Asynchronously perform initialization tasks here
    #     instance = cls(*args, **kwargs)
    #     # Optionally perform more async operations on 'instance' if needed
    #     return instance

    def add_images(self, images_info: List[Tuple[Type[Union['OfflineImage', 'OnlineImage']], tuple, dict]]):
        """
        Creates and adds multiple image objects.

        Parameters:
            images_info -- First is the image class for the object, then an argument tuple and at last a keyword
            argument dictionary
        """
        if self.use_async:
            ...#asyncio.run(self._add_images_async(images_info))
        else:
            for image_class, args, kwargs in images_info:
                kwargs["base_location"] = kwargs.get("base_location") or self.base_location
                kwargs["_use_async"] = False
                self.images.append(image_class(**kwargs))

    # async def _add_images_async(self, images_info):
    #     tasks = [ImageClass(*args, **{**kwargs, "_use_async": True,
    #                                   "base_location": kwargs.get("base_location") or self.base_location})
    #              for ImageClass, args, kwargs in images_info]
    #     self.images.extend(await asyncio.gather(*tasks))

    def add_image_object(self, image_object: Union['OfflineImage', 'OnlineImage']) -> int:
        """Adds image objects."""
        self.images.append(image_object)
        return len(self.images) - 1

    def add_image_objects(self, image_objects: List[Union['OfflineImage', 'OnlineImage']]):
        """Adds image objects."""
        self.images.extend(image_objects)

    def remove_image(self, index: int):
        if self.use_async:
            ...#asyncio.run(self._remove_image(index))
        else:
            del self.images[index]

    # async def _remove_image(self, index: int):
    #     await asyncio.sleep(0)  # Yield control to the event loop
    #     del self.images[index]

    def remove_images(self, indices_list: List[int]):
        if self.use_async:
            ...#asyncio.run(self._remove_images(indices_list))
        else:
            for index in sorted(indices_list, reverse=True):
                del self.images[index]

    # async def _remove_images(self, indices_list: List[int]):
    #     tasks = [self._remove_image(index) for index in sorted(indices_list, reverse=True)]
    #     await asyncio.gather(*tasks)

    def remove_image_object(self, image_object: Union['OfflineImage', 'OnlineImage']):
        if self.use_async:
            ...#asyncio.run(self._remove_image_object(image_object))
        else:
            self.images.remove(image_object)

    # async def _remove_image_object(self, image_object: Union['OfflineImage', 'OnlineImage']):
    #     await asyncio.sleep(0)  # Yield control to the event loop
    #     self.images.remove(image_object)

    def remove_image_objects(self, image_objects: List[Union['OfflineImage', 'OnlineImage']]):
        if self.use_async:
            ...#asyncio.run(self._remove_image_objects(image_objects))
        else:
            for image_object in image_objects:
                self.images.remove(image_object)

    # async def _remove_image_objects(self, image_objects: List[Union['OfflineImage', 'OnlineImage']]):
    #     tasks = [self._remove_image_object(image_object) for image_object in image_objects]
    #     await asyncio.gather(*tasks)

    def execute_func(self, index: int, function, *args, **kwargs):
        if self.use_async:
            ...#asyncio.run(self._execute_func_async(index, function, *args, **kwargs))
        else:
            getattr(self.images[index], function)(*args, **kwargs)

    # async def _execute_func_async(self, index: int, function, *args, **kwargs):
    #     func = getattr(self.images[index], function)
    #     if asyncio.iscoroutinefunction(func):
    #         await func(*args, **kwargs)
    #     else:
    #         # Handle non-async functions, possibly with run_in_executor for CPU-bound methods
    #         loop = asyncio.get_running_loop()
    #         with ThreadPoolExecutor() as pool:
    #             await self.run_in_executor(loop, pool, func, *args, **kwargs)

    # @staticmethod
    # async def run_in_executor(loop, executor, func, *args, **kwargs):
    #     if kwargs:
    #         func = functools.partial(func, **kwargs)
    #     return await loop.run_in_executor(executor, func, *args)

    def execute_funcs(self, function_name: str, args_list: List[Tuple[int, list, dict]]):
        if self.use_async:
            ...#asyncio.run(self._execute_funcs_async(function_name, args_list))
        else:
            for index, args, kwargs in args_list:
                try:
                    getattr(self.images[index], function_name)(*args, **kwargs)
                except IndexError:
                    print(f"No image at index {index}")
                except AttributeError:
                    print(f"The function {function_name} does not exist for the image at index {index}")

    # async def _execute_funcs_async(self, function_name: str, args_list: List[Tuple[int, list, dict]]):
    #     tasks = [self._execute_func_async(index, function_name, *args, **kwargs) for index, args, kwargs in args_list]
    #     await asyncio.gather(*tasks)


class ResizeTypes:
    FAST = Image.Resampling.NEAREST
    BOX = Image.Resampling.BOX
    UP = Image.Resampling.BILINEAR
    DOWN = Image.Resampling.HAMMING
    GOOD_UP = Image.Resampling.BICUBIC
    HIGH_QUALITY = Image.Resampling.LANCZOS


class OfflineImage:
    def __init__(self, data: Optional[Union[str, bytes]] = None, path: Optional[str] = None, _use_async: bool = False,
                 base_location: Optional[str] = None, original_name: Optional[str] = None):
        if data is not None and path is None:
            self.data = data
        elif path is not None and data is None:
            self.get_data(path)
        else:
            raise ValueError("Please pass exactly one argument ('data' or 'path') to the init method.")
        self._use_async = _use_async
        self.base_location = base_location
        self.original_name = original_name
        
    def get_data(self, path: str):
        """
        Loads the data from path into self.data.
        """
        with open(path, 'rb') as f:
            self.data = f.read()

    def load_image_from_data(self):
        """
        Loads various data formats like base64 and bytes from self.data into a Pillow.Image object returns it.
        """
        if isinstance(self.data, str):
            # Assuming data is a base64 string
            image_data = base64.b64decode(self.data.split(',')[1])
        elif isinstance(self.data, bytes):
            image_data = self.data
        else:
            raise ValueError("Unsupported data type for self.data")

        return Image.open(BytesIO(image_data))

    def _save_image(self, source_path: str, img_data: bytes, new_name: Optional[str] = None) -> Optional[str]:
        if source_path.split(".")[-1] == 'svg':  # Optional[str] from typing import Optional
            print("SVG format is not supported.")
            return None
        with open(source_path, 'wb') as img_file:
            img_file.write(img_data)
        return self._convert_image_format(source_path, new_name) if new_name else source_path
    
    def save_image(self, img_data: bytes, original_name: str, base_location: Optional[str] = None,
                   original_format: Optional[str] = None, new_name: Optional[str] = None,
                   target_format: Optional[str] = None) -> Optional[str]:
        """
        Saves image with a new name and potentially new format.
        """
        base_location = base_location or self.base_location
        if original_format == '.svg':  # Optional[str] from typing import Optional
            print("SVG format is not supported.")
            return None
        source_path = os.path.join(base_location, f"{original_name}.{original_format}" if original_format else original_name)
        with open(source_path, 'wb') as img_file:
            img_file.write(img_data)
        return self.convert_image_format(base_location, original_name, original_format, new_name, target_format)

    @staticmethod  # Optional[str] from typing import Optional
    def _convert_image_format(source_path, new_name) -> Union[None, str]:
        if source_path.split(".")[-1] == "svg":
            print("SVG format is not supported.")
            return None
        # Create the new file path with the desired extension
        new_file_path = os.path.join(os.path.dirname(source_path), f"{new_name}")
        # Open, convert and save the image in the new format
        with Image.open(str(source_path)) as img:
            img.save(new_file_path)
        os.remove(source_path) if source_path != new_file_path else print("Skipping deleting ...")
        return new_file_path

    def convert_image_format(self, original_name: str, base_location: Optional[str] = None,
                             original_format: Optional[str] = None, new_name: Optional[str] = None,
                             target_format: Optional[str] = 'png') -> Optional[str]:
        """
        Converts image to a new format.
        """
        source_path = os.path.join(base_location, f"{original_name}"
                                                  f".{original_format}" if original_format else original_name)
        base_location = base_location or self.base_location
        if source_path.split(".")[-1] == "svg":
            print("SVG format is not supported.")
            return None
        # Extract the base file name without an extension
        base_name = os.path.splitext(os.path.basename(source_path))[0]
        # Create the new file path with the desired extension
        if new_name is None:
            new_file_path = os.path.join(os.path.dirname(source_path), f"{base_name}.{target_format}")
        else:
            new_file_path = os.path.join(os.path.dirname(source_path), f"{new_name}.{target_format}")
        # Open, convert and save the image in the new format
        with Image.open(str(source_path)) as img:
            img.save(new_file_path)
        os.remove(source_path) if source_path != new_file_path else print("Skipping deleting ...")
        return new_file_path

    def base64(self, path: str, new_name: str, img_format: str, data: Optional[str] = None) -> bool:
        internal_data = self.data if not data else data
        try:
            img_data = base64.b64decode(internal_data.split(',')[1])
            img_name = new_name + '.' + img_format
            source_path = os.path.join(path, img_name)
            if self._save_image(source_path, img_data, img_name) is None:
                return False
        except Exception as e:
            print(f"Error occurred: {e}")
            return False
        return True

    def resize_image(self, new_size: Tuple[int, int], resample=Image.Resampling.LANCZOS) -> None:
        with self.load_image_from_data() as img:
            resized_image = img.resize(new_size, resample)

            # Updating self.data with the new image data
            img_byte_arr = BytesIO()
            img_format = img.format if img.format is not None else 'PNG'
            resized_image.save(img_byte_arr, format=img_format)
            self.data = img_byte_arr.getvalue()

    def resize_image_quick(self, new_size: Tuple[int, int], resample=Image.Resampling.NEAREST) -> None:
        self.resize_image(new_size, resample)

    def rotate_image(self, degrees: float, expand=True) -> None:
        with self.load_image_from_data() as img:
            original_format = img.format
            rotated_image = img.rotate(degrees, expand=expand)

            # Updating self.data with the new image data
            img_byte_arr = BytesIO()
            rotated_image.save(img_byte_arr, format=original_format)
            self.data = img_byte_arr.getvalue()

    def crop_image(self, crop_rectangle: Tuple[int, int, int, int]) -> None:
        with self.load_image_from_data() as img:
            cropped_image = img.crop(crop_rectangle)

            # Updating self.data with the new image data
            img_byte_arr = BytesIO()
            img_format = img.format if img.format else 'PNG'
            cropped_image.save(img_byte_arr, format=img_format)
            self.data = img_byte_arr.getvalue()

    def convert_to_grayscale(self) -> None:
        with self.load_image_from_data() as img:
            grayscale_image = img.convert("L")

            # Updating self.data with the new image data
            img_byte_arr = BytesIO()
            # Use the original format or default to PNG
            img_format = img.format if img.format else 'PNG'
            grayscale_image.save(img_byte_arr, format=img_format)
            self.data = img_byte_arr.getvalue()

    def apply_filter(self, filter_type=ImageFilter.BLUR) -> None:
        with self.load_image_from_data() as img:
            filtered_image = img.filter(filter_type)

            # Updating self.data with the new image data
            img_byte_arr = BytesIO()
            img_format = img.format if img.format else 'PNG'
            filtered_image.save(img_byte_arr, format=img_format)
            self.data = img_byte_arr.getvalue()

    def save_image_to_disk(self, file_path: Optional[str] = None) -> None:
        if not isinstance(self.data, (bytes, str)):
            raise ValueError("self.data must be a byte string or a base64 string.")

        if not file_path:
            if self.base_location and self.original_name:
                file_path = os.path.join(self.base_location, self.original_name)
            else:
                raise ValueError("You can't omit file_path, if self.base_location and self.original_name aren't both set.")

        with open(file_path, "wb") as file:
            file.write(self.data if isinstance(self.data, bytes) else base64.b64decode(self.data.split(',')[1]))


class OnlineImage(OfflineImage):
    def __init__(self, current_url: Optional[str] = None, base_location: str = "../utils\\", one_time: bool = False,
                 _use_async: bool = False):
        self.current_url = current_url
        self.base_location = base_location
        self._use_async = _use_async

        if one_time and current_url:
            self.download_image()
            
    def download_logo_image(self, base_path: str, new_name: str, img_format: str) -> bool:
        if not self.current_url:
            return False

        try:
            format_match = re.match(r'^data:image/[^;]+;base64,', self.current_url)
            if format_match:
                if "image/svg+xml" in self.current_url:
                    print("SVG format is not supported.")
                    return False

                image_data = base64.b64decode(self.current_url.split(',')[1])
                file_path = os.path.join(base_path, f"{new_name}.{img_format}")
                self._save_image(file_path, image_data)
                return True
            else:
                return self.download_image(self.current_url, base_path, new_name, img_format)[0]

        except Exception as e:
            print(f"An error occurred while downloading the logo image: {e}")
            return False
            
    def download_image(self, base_path: Optional[str] = None, img_url: Optional[str] = None,
                       new_name: Optional[str] = None, img_format: Optional[str] = None
                       ) -> Union[Tuple[bool, None, None], Tuple[bool, str, str]]:
        if not img_url:
            if not self.current_url:
                print("No URL provided for image download.")
                return False, None, None
            img_url = self.current_url
        base_path = base_path or self.base_location

        try:
            response = requests.get(img_url, timeout=2.0)
            response.raise_for_status()  # Will raise an HTTPError for bad requests (4xx or 5xx)

            # Determine the file extension if not provided
            if not img_format:
                guessed_extension = mimetypes.guess_extension(response.headers.get('content-type'))
                img_format = guessed_extension.strip('.') if guessed_extension else 'jpg'

            file_name = new_name if new_name else os.path.basename(urlparse(img_url).path).split('.')[0]
            file_path = os.path.join(base_path, f"{file_name}.{img_format}")

            # Save the image data
            self._save_image(file_path, response.content)
            print(f"Downloaded image from {img_url} to {file_path}")
            super().__init__(path=file_path, base_location=self.base_location, original_name=f"{file_name}.{img_format}", _use_async=self._use_async)
            return True, file_name, file_path

        except requests.ConnectionError:
            print("Failed to connect to the server.")
        except requests.Timeout:
            print("The request timed out.")
        except requests.TooManyRedirects:
            print("Too many redirects.")
        except requests.HTTPError as e:
            print(f"HTTP error occurred: {e}")
        except KeyError:
            print("The image tag does not have a src attribute.")
        except Exception as e:
            print(f"An unexpected error occurred while downloading the image: {e}")

        return False, None, None


class SVGCompatibleImage(OfflineImage):
    def __init__(self, file_path_or_url, resolution: Optional[int] = None,
                 output_size: Optional[Tuple[int, int]] = None, magick_path: Optional[str] = None,
                 _use_async: bool = False, base_location: Optional[str] = None, keep_online_svg: bool = False):
        if magick_path:
            os.environ['MAGICK_HOME'] = magick_path
        self.base_location = base_location
        self.resolution = resolution  # Resolution in DPI (dots per inch)
        self.output_size = output_size  # Output size as (width, height)
        file_path, online_svg = self.handle_path_or_url(file_path_or_url)
        # self.image = self.load_image(file_path)
        self.data = self.load_data(file_path)
        if not keep_online_svg and online_svg:
            os.remove(file_path)
        super().__init__(self.data, _use_async=_use_async, base_location=base_location,
                         original_name='.'.join(os.path.basename(file_path).rsplit(".")[:-1])+".png")

    def handle_path_or_url(self, file_path_or_url):
        if self.is_url(file_path_or_url):
            # It's a URL, download the file
            return self.download_image(file_path_or_url), True
        else:
            # It's a local file path
            return file_path_or_url, False

    @staticmethod
    def is_url(string):
        try:
            result = urlparse(string)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    def load_data(self, file_path):
        if file_path.lower().endswith('.svg'):
            return self._convert_svg_to_raster(file_path, True)
        else:
            return super().get_data(file_path)

    def load_image(self, file_path):
        if file_path.lower().endswith('.svg'):
            return self._convert_svg_to_raster(file_path)
        else:
            return Image.open(file_path)

    def _convert_svg_to_raster(self, svg_file, return_as_bytes=False):
        from wand.image import Image as WandImage

        with WandImage(filename=svg_file, format='png') as img:
            if self.resolution:
                img.density = self.resolution
            if self.output_size:
                img.resize(*self.output_size)
            png_blob = img.make_blob()
        if return_as_bytes:
            return png_blob
        return Image.open(BytesIO(png_blob))
        # img = Image.open(BytesIO(png_blob))
        # if return_as_bytes:
        #     with BytesIO() as output:
        #         img.save(output, format='PNG')
        #         return output.getvalue()
        # else:
        #     return img

    def download_image(self, url):
        try:
            user_agent = get_user_agent()
            headers = {"User-Agent": user_agent}
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            file_name = os.path.basename(urlparse(url).path)
            file_path = os.path.join(self.base_location, file_name)
            with open(file_path, 'wb') as file:
                file.write(response.content)
            print(f"Downloaded image from {url} to {file_path}")
            return file_path
        except Exception as e:
            print(f"An error occurred while downloading the image: {e}")
            return None


class SVGImage:
    pass


def local_test():
    try:
        # Setup
        folder_path = "./test_data/images"
        os.makedirs(folder_path, exist_ok=True)
        test_url = "https://huggingface.co/p1atdev/MangaLineExtraction-hf/resolve/main/images/sample.jpg"
        base64_image_str = ("data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBwgHBgkIBwgKCgkLDRYPDQ"
                            "wMDRsUFRAWIB0iIiAdHx8kKDQsJCYxJx8fLT0tMTU3Ojo6Iys/RD84QzQ5OjcBCgoKDQwNGg8PGjclHyU"
                            "3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3N//AABEIAHkAwgMB"
                            "IgACEQEDEQH/xAAcAAABBQEBAQAAAAAAAAAAAAACAAEDBAYFBwj/xABEEAABAwMCAwMGCQkJAQAAAAABA"
                            "AIDBAUREiEGMUETUXEVIjJSYZEUM0KBgpOhsdEHI1NUYmODksEWNENEc5SiwuEX/8QAFwEBAQEBAAAAAA"
                            "AAAAAAAAAAAAECA//EAB0RAQADAQEBAAMAAAAAAAAAAAABAhETEiExUXH/2gAMAwEAAhEDEQA/APRwAjA"
                            "ThoRgLrrjgdKINRhEAmmADEQYjCcKaYEMRgJwnRSCdMnUCSwkllA+E6bKWoIHTpkigSR5JspE7IoXDIQg"
                            "I0yIYoCiKEoGOOqF2EiUJKoWySHKSAQjChDktagsIgVWEiIPQWcp8qFrkQcglyllR6ktSCTKfKj1JakBk"
                            "qN0uE+UD25QCZ0wqFC+N2dkzI3ZVF+KTIyj1BV2jASJOUFgpKFrj1RakB5TIcpi5ARQFIuQkoGJQlJzkD"
                            "nICyko9RSQB0QOymyUwOSiCblSsygapQEC1FOHoT4ISCoqYPT6wq2D3omgjmUE+tPrUWcJa2jmQPE4QS6"
                            "k+pRB7TyIOO4pakEuUtQCi1ISSTzVRYyllV8kJB5CCxlPlQByIFBLlNlBlNqQGShJQkpiUDlAUiUJKBJJ"
                            "kyoiGUQCETR+sETZI/WCho2owVGJI/WCMOZ3qGnJSySm1N70tQQ2CKrurKdtSKc1EYnPKPUNXfyRVk7YK"
                            "aaZz2sDGOdrecBuBzJXgVbfTPXGYscKlkgdJJnm4dAOjeWyNVjXvj6una8sfURhw5t1DIXnvEN1rJKxzq"
                            "jMI1HsI3AZDenT7155PfriZ3EVj9DjvG8At92ENdc/hlJTskmjLqdznBrdXXuLj7BsOSmtxR3X8X11vrW"
                            "tbcHFmodo0NDwB1+dajhXjWa43umooqySqEz8GJ9NpIHV2rbGBv8AYvOrRRRVzHSP7GNodp1PPnOPXC2N"
                            "mpaOw6bnDpNU0EREO3BI7vDKEvXww4zuuXVXyjgeWsJlcOek4A+dYtt0q3wvmq6mSSV431O2HsA5KiarS"
                            "0vJzpBJ35qsY1N246obW0fCXRsc70Yxlzz8wWEu/wCVS7VExbbGRUsQ5FzA559+wWU7V00skrnZmlcS+R"
                            "wyT/4inp46iJzHACdo1Nc35QT+G1icbzgz8o1zrbpTW6407ar4Q8MbJC0Ne095HIjqeS9WDl81cJXnyBf"
                            "6S4uZqZE4tkA56XAh2PmK+jYJmSxtkjeHMcA5rgdiDyK1H2C+QsFJBrTawmSx6gaYoO0CEvTJPUJCVGXI"
                            "S9CXhMPUD1J1D2iSYeoYgXKQf4jvej8qSDlKfeso3iigI3s858JFI3im3dbRUD6anaq8bNS26yfpDnxUr"
                            "bvJ1kKyjeJ6Fw2s9WR7HqQcRUWMmyVuO/JU61ONms8qyhue0TC8S+uVkW8V2pxwLfUn2CQFSM4qtbDk22"
                            "qH0k61ONmkuNfNV22rhZN2bnxOAeemy8gkJmL5d8udsT3Bb9vFdmedDqOpbr2yXDG6xT4+ypmsJBcwnfO"
                            "x84/gszeJ/DrSk1j65b3DWO5RTuDp8gdOSOb0lAXfnAT3I0lpal8OzHED2ErrU93lc1rHyEhnIErhaSOh"
                            "RMfp33B6pqNVFe3Pj8526I3bzT53RZaOUgkA536KUTO701VyOoYwFpGWkbYRMnBlbpyNsFVX08npwtc+M"
                            "925HsKNgdGxzpRpONh/Uqx8c7V1RHQ9cBew8H3upj4WtzZMktjLQT1aHED7MLyOlhFTUhhdoYTlz8Z0t6"
                            "nC9NhvvC8FNFBFNViOJoY0CLoEreK/kvSbR8ac3+THco3cQS9FnHcQcOdJq0fwkIv3DhP95rPqlrrVz42"
                            "aUX+Ugnu9ib+0MuN1m/L3Dg51VYP4SRvnDjhgVNXy/QlOsLxlohxC8pjxA9Zvyzw4P81V/UH8EPlvhv8A"
                            "W6r6g/gr1qnGzR/2heks55Z4c/Xqr/bn8Ek61ONm2lFthOmV8Id6o3PuG6ZnYuGKahlkHrOj7Nv/ACx9y"
                            "vwwwwj81FHGO5jQFLtnOyxjo5rqOql9FtNTDvDO1d9uB96lda2SsDamaSZvqk6Gn5m4yr45Ig3vTBSbb4"
                            "Ym6YIo4+4Ma0KT4FGQMsacDqFZfJFG0l72gDnkrP1/EsfaGC2RPq6jOPMHmjxKhETLpTwUcEbpJY4msaM"
                            "lxaBheecTMst6D57W2eOdh0uljjBjd83U+C1jbNPXt7e/TmoIGWUw2iafaOq5s8Qa/HZxlg5NAwAktQ83"
                            "qbFMJMQzdr7DEWfeqtTZK6Fmp8Od9OzgvRo6CIyF3ZtBPMkqV9ut4ID2En9lxWGvjzWnt0+NMlJLqH7RG"
                            "3grtot1WythMbW69Q0GVuW59y2M1NTa2mNr9ttxnIUkVukErZGs0lvouSVTHhi81hD65lqkJbzfCPwWa4"
                            "m4Kbba6OOCsjiim3jMxJaD3F3MeJC20j6qVuRUO2AGNlyrlQVNY1zKlrp4yOrtx4JGQz9YmXhu9UB1MfR"
                            "vB2zHWR/9iFUq7fXEZnPmj5OppAP0ditZS0LKeodS3EOaT8TKDsfFWKq2SU+GjXy5txg/YtaqjwLwtc5b"
                            "jT10bo44YzlznkO1N6t08zkbL1dtpoydqaMeDV5xYQ+mu0TiHaS7zvBenRPZI3LWn3rUMWmdRG3RtHmMZ"
                            "9NvNRupYmfGUQcOpj0n8CrulvqH3ogQOiuM65bm2kuEcggY8/IlGg+44QT2G1VDfztFA8H92F054op2Fk"
                            "0bJGEYLXtBBXPFogiOaR89Mf3UpA/l5JkGy5NRwRw/NzpNH+m9zfuK5VR+Tq2OdmGqqY/2cg/0WpkjukX"
                            "xVRDO0fJlZg+8KEXOph2rbfJz9OHzh+KnmF9T+2V/+dUX6/P/AChJazy3Rd8n1ZSU8wvqf2s6x0UL6h7T"
                            "6OyKWeOMZJC4ly4gipwWtILjyCqOo64vbuGgD2lUK/ieGmYWg65ejWrP9rX3N5DcxRn3rsW3h+CHDnjU/"
                            "vKjXxSjhud+kzUyOhp/UaefitPbLbBb4gynjDT1djcqWGDsx5gACtMyAqkyGo2gPfhZKoc90h0jqtdKfM"
                            "IKzVRRyGUlveqimYZsA5wEGJg7fdo7guj8HdpwSm0aBjGVMNVo4yemfapxHIRsdksuGwGynieSRkJi6ri"
                            "CbOybROXY1HC6o3HJV5WYOQpi+lCstYrYCyXn0PcqVLVSUThRVvnNHxcjhz9i65e8dVSuFMKyEgjzlJg1"
                            "ZghjkIka1uR1AWjoXYj06lhrZVyUM3YTk6c7ErW0krXtDmvByrCTDrFxTZVdrzhEJO9aZSkoS7CDWhLlA"
                            "Tn7KNzkxchL1Q2G+q33J0Oop0GBkrK2vfhmpreSvW+yZIfLlzjzJStfILRQeiFG0dLSshGA1XACEzeak6"
                            "JiDjeVOHKsxSjkiHkOQqT2jKtu5Kq7mgiLVBJHurRUT1RW7JSxRIgpo0QQaQFDKwlWuiiciqmg9UTYkZR"
                            "MUWHNuVsbNHqaMOVK110lFN2E/IciVo3fFlZW7/HjxUVsYKpkrAWkIid1xLT8W1dlq0wmDtkxKDokUDOK"
                            "AuTlAUUWpJAkg//Z")

        # Test downloading an online image
        online_image = OnlineImage(current_url=test_url, base_location=folder_path, one_time=True)
        download_result = online_image.download_image(folder_path, online_image.current_url, "downloaded_image", "jpg")
        if not download_result[0]:
            raise Exception("Failed to download image.")
        else:
            online_image.convert_to_grayscale()
            online_image.save_image_to_disk(os.path.join(folder_path, "image.png"))

        # Test loading and saving a base64 image with OfflineImage
        offline_image = OfflineImage(data=base64_image_str, base_location=folder_path)
        save_result = offline_image.base64(folder_path, "base64_image", "png")
        if not save_result:
            raise Exception("Failed to save base64 image.")

        # Test image transformations
        offline_image.resize_image((100, 100))
        offline_image.rotate_image(45)
        offline_image.convert_to_grayscale()
        offline_image.apply_filter(ImageFilter.BLUR)
        offline_image.save_image_to_disk(os.path.join(folder_path, "transformed_image.png"))

        # Example svg image usage
        image_processor = SVGCompatibleImage("https://upload.wikimedia.org/wikipedia/commons/b/b0/NewTux.svg", 300,
                                             (667, 800), magick_path=r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI",
                                             base_location='./')
        image_processor.save_image_to_disk()

    except Exception as e:
        print(f"Exception occurred: {e}")
        return False
    print("All tests completed successfully.")
    return True


if __name__ == "__main__":
    local_test()
