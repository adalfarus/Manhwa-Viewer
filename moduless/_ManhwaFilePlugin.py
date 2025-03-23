import json
import base64
from io import BytesIO
from PIL import Image
from aplustools.utils.imagetools import OfflineImage
import requests
import urllib3
import os
from urllib.parse import urlencode, urlunparse, quote_plus
from urllib.request import urlopen, Request
from urllib.parse import urljoin, urlparse
from aplustools.web import webtools as wt

# Disable only the specific InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ManhwaFilePlugin:
    def __init__(self, chapter, file_path, data_folder, cache_folder):
        self.title = "" # Get title from the file
        self.chapter = chapter
        self.chapters = None
        self.file_path = file_path
        self.data_folder = data_folder
        self.cache_folder = cache_folder
        self.current_chapter_data = None  # This will hold the current chapter data after reading
        self.read_mwa_file_data()

    def set_title(self, new_title):
        self.title = new_title
        
    def get_title(self):
        return self.title

    def set_chapter(self, new_chapter):
        self.chapter = new_chapter
        
    def get_chapter(self):
        return self.chapter
        
    def set_file_path(self, new_file_path):
        self.file_path = new_file_path
        
    def get_file_path(self):
        return self.file_path
        
    def redo_prep(self):
        self._empty_cache()
        image = Image.open(f"{self.data_folder}empty.png")
        image.save(f"{self.cache_folder}empty.png")
        
    def _get_url(self, url, title):
        return wt.check_url(url, title, [self.title, str(self.chapter)])
        
    def _is_crawlable(self, url):
        return wt.is_crawlable(url)
            
    def _convert_image_format(self, source_path, new_name=None, target_format='png'):
        image = OfflineImage(path=source_path)
        if new_name is not None:
            print(source_path, new_name + "." + target_format)
            image._convert_image_format(source_path, new_name + "." + target_format)
        else:
            print(source_path, source_path.split(".")[-2] + "." + target_format)
            image._convert_image_format(source_path, source_path.split(".")[-2] + "." + target_format)

    def _empty_cache(self):
        files = os.listdir(self.cache_folder)
        for f in files:
            os.remove(f"{self.cache_folder}{f}")

    def _make_cache_readable(self):
        # List all files in the directory
        files = os.listdir(self.cache_folder)
        # Filter out files that are not numerical
        numerical_files = [f for f in files if f.split('.')[0].isdigit()]
        # Sort files numerically
        numerical_files.sort(key=lambda x: int(x.split('.')[0]))
        for i, file in enumerate(numerical_files):
            # Define file name
            file_name = file.split(".")[0]
            # Generate a new file name with three digits
            new_name = str(i+1).zfill(3)
            # Convert the file to png and rename it to new_name var
            self._convert_image_format(os.path.join(self.cache_folder, file), new_name=new_name, target_format='png')
            print(f'Renamed {file} to {new_name}')

    def read_mwa_file_data(self):
        with open(self.file_path, 'r') as file:
            data = json.load(file)
            self.title = data['metadata']['title']
            self.chapters = [i['chapterNumber'] for i in data['chapters']]

    def read_mwa_file_chapter(self):
        with open(self.file_path, 'r') as file:
            data = json.load(file)
            self.title = data['metadata']['title']
            self.chapters = [i['chapterNumber'] for i in data['chapters']]
            for chapter in data['chapters']:
                if chapter['chapterNumber'] == self.chapter:
                    self.current_chapter_data = chapter
                    return chapter
            print("Chapter not found")
            raise Exception("Chapter not found")#return None

    def cache_current_chapter(self):
        if not self.current_chapter_data:
            print("Chapter data not found.")
            return False

        self._empty_cache()

        for i, page in enumerate(self.current_chapter_data['pages']):
            if page['type'] == 'base64':
                image_data = base64.b64decode(page['data'])
            elif page['type'] == 'url':
                response = requests.get(page['data'])
                image_data = response.content
            else:
                print(f"Unknown type: {page['type']}")
                continue

            image = OfflineImage()
            image.save_image(self.cache_folder, image_data, str(i), target_format='png')

        self._make_cache_readable()
        return True

    def nearest_number(self, numbers, target, direction=None):
        if direction == "positive":
            candidates = [num for num in numbers if num > target]
        elif direction == "negative":
            candidates = [num for num in numbers if num < target]
        else:
            candidates = numbers

        if not candidates:  # If the list is empty after filtering
            return target

        return min(candidates, key=lambda num: abs(num - target))

    def next_chapter(self):
        self.chapter = self.nearest_number(self.chapters, self.chapter, "positive")
        try: self.read_mwa_file_chapter()
        except: return False
        return self.cache_current_chapter()

    def previous_chapter(self):
        self.chapter = self.nearest_number(self.chapters, self.chapter, "negative")
        try: self.read_mwa_file_chapter()
        except: return False
        return self.cache_current_chapter()

    def reload_chapter(self):
        self.chapter = min(self.chapters, key=lambda num: abs(num - self.chapter))
        try: self.read_mwa_file_chapter()
        except: return False
        return self.cache_current_chapter()
        