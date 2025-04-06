"""TBA"""

# Built-in
from importlib.machinery import ModuleSpec
import importlib.util
import sqlite3
import shutil
import json
import os

# 3rd-party imports


# Standard typing imports for aps
from abc import abstractmethod, ABCMeta
import collections.abc as _a
import typing as _ty
import types as _ts


class DBManager:
    def __init__(self, path: str):
        self._path = path
        self.conn = sqlite3.connect(path)
        self.cursor = self.conn.cursor()

    def create_table(self, table_name: str, columns: list):
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
        try:
            self.cursor.execute(query)
            self.conn.commit()
        except Exception as e:
            print(f"Error creating table: {e}")

    def update_info(self, info: list, table: str, columns: list):
        if len(info) != len(columns):
            raise ValueError("Length of info must match the number of columns.")

        # Assuming first column is a unique identifier like ID
        query_check = f"SELECT COUNT(*) FROM {table} WHERE {columns[0]} = ?"
        self.cursor.execute(query_check, (info[0],))
        exists = self.cursor.fetchone()[0]

        if exists:
            placeholders = ', '.join([f"{column} = ?" for column in columns])
            query = f"UPDATE {table} SET {placeholders} WHERE {columns[0]} = ?"
            try:
                self.cursor.execute(query, (*info, info[0]))
                self.conn.commit()
            except Exception as e:
                print(f"Error updating info: {e}")
        else:
            query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' for _ in info)})"
            try:
                self.cursor.execute(query, info)
                self.conn.commit()
            except Exception as e:
                print(f"Error updating info: {e}")

    def get_info(self, table: str, columns: list) -> list:
        query = f"SELECT {', '.join(columns)} FROM {table}"
        try:
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error getting infor: {e}")
            return []

    def connect(self):
        try:
            self.conn = sqlite3.connect(self._path)
            self.cursor = self.conn.cursor()
        except Exception as e:
            print(f"Error connection to the database: {e}")

    def close(self):
        try:
            self.conn.commit()
            self.conn.close()
        except Exception as e:
            print(f"Error closing the database: {e}")


class Settings:
    def __init__(self, db_path, overwrite_settings: _ty.Optional[dict] = None, export_settings_func=lambda: None) -> None:
        is_setup = os.path.isfile(db_path)
        self.db = DBManager(db_path)
        self.is_open = True
        self.default_settings = {
            "provider_id": "manhwa_clan",
            "title": "Thanks for using ManhwaViewer!",
            "chapter": "1",
            "libraries": '[]',  # json
            "current_lib_idx": "-1",
            "library_manager_id": "std_lib",
            "downscaling": "True",
            "upscaling": "False",
            "manual_content_width": "1200",
            "borderless": "True",
            "hide_titlebar": "False",
            "hover_effect_all": "True",
            "acrylic_menus": "True",
            "acrylic_background": "False",
            "hide_scrollbar": "False",
            "stay_on_top": "False",
            "geometry": "100, 100, 640, 480",
            "advanced_settings": '{"recent_titles": [], "themes": {"light": "light_light", "dark": "light_dark", "font": "Segoe UI"}, "settings_file_path": "", "settings_file_mode": "overwrite", "misc": {"auto_export": false, "quality_preset": "quality", "max_cached_chapters": -1, "use_threading_for_pipeline_if_available": true, "image_processing_pipeline": []}}',
            "chapter_rate": "1.0",
            "no_update_info": "True",
            "not_recommened_update_info": "True",
            "update_info": "True",
            "last_scroll_positions": "0, 0",
            "scrolling_sensitivity": "4.0",
            "lazy_loading": "True",
            "save_last_titles": "True",
            "show_provider_logo": "True",
            "show_tutorial": "True"
        }
        self.settings = self.default_settings.copy()
        if overwrite_settings:
            self.settings.update(overwrite_settings)
        if not is_setup:
            self.setup_database(self.settings)
        self.fetch_data()
        self.export_settings_func = export_settings_func

    def connect(self):
        self.db.connect()
        self.is_open = True
        self.fetch_data()

    def get_default_setting(self, setting: str):
        return self.default_settings.get(setting)

    def boolean(self, to_boolean: str) -> bool:
        return to_boolean.lower() == "true"

    def str_to_list(self, s: str) -> list[str]:
        return s.split(", ")

    def list_to_str(self, lst: list[str]) -> str:
        return ', '.join(lst)

    def ensure_keys(self, base: dict, modified: dict) -> dict:
        """
        Ensures all keys and nested keys in `base` exist in `modified`.
        If a key is missing in `modified`, it's added from `base`.
        """
        result = modified.copy()  # Make a shallow copy to avoid modifying the original

        for key, base_value in base.items():
            if key not in result:
                result[key] = base_value
            else:
                # If both are dicts, recurse
                if isinstance(base_value, dict) and isinstance(result[key], dict):
                    result[key] = self.ensure_keys(base_value, result[key])
        return result

    def get(self, key: str) -> _ty.Any:
        value = self.settings.get(key)
        if key in ["blacklisted_websites"]:
            return self.str_to_list(value)
        elif key in ["chapter"]:
            return int(value) if float(value).is_integer() else float(value)
        elif key in ["chapter_rate", "scrolling_sensitivity"]:
            return float(value)
        elif key in ["downscaling", "upscaling", "borderless", "hide_titlebar", "hover_effect_all",
                     "acrylic_menus", "acrylic_background", "hide_scrollbar", "stay_on_top", "no_update_info",
                     "update_info", "lazy_loading", "save_last_titles", "show_provider_logo", "show_tutorial"]:
            return self.boolean(value)
        elif key in ["manual_content_width", "current_lib_idx", "max_cached_chapters"]:
            return int(value)
        elif key in ["geometry", "last_scroll_positions"]:
            return [int(x) for x in value.split(", ")]
        elif key in ["advanced_settings", "libraries"]:
            mod_val = json.loads(value)
            if not isinstance(mod_val, dict):
                return mod_val
            return self.ensure_keys(json.loads(self.default_settings.get(key)), mod_val)
        return value

    def set(self, key: str, value: _ty.Any) -> None:
        if key in ["blacklisted_websites"]:
            value = self.list_to_str(value)
        elif key in ["chapter"]:
            value = str(int(value) if float(value).is_integer() else value)
        elif key in ["chapter_rate", "scrolling_sensitivity"]:
            value = str(float(value))
        elif key in ["downscaling", "upscaling", "borderless", "hide_titlebar", "hover_effect_all",
                     "acrylic_menus", "acrylic_background", "hide_scrollbar", "stay_on_top", "no_update_info",
                     "update_info", "lazy_loading", "save_last_titles", "show_provider_logo", "show_tutorial"]:
            value = str(value)
        elif key in ["manual_content_width", "current_lib_idx", "max_cached_chapters"]:
            value = str(int(value))
        elif key in ["geometry", "last_scroll_positions"]:
            value = ', '.join([str(x) for x in value])
        elif key in ["advanced_settings", "libraries"]:
            if isinstance(value, dict):
                base = json.loads(self.default_settings.get(key))
                value = json.dumps(self.ensure_keys(base, value))
            else:
                value = json.dumps(value)
        self.settings[key] = value
        self.update_data()
        # if self.get_advanced_settings()["misc"]["auto_export"]:
        #     self.export_settings_func()

    def get_provider_id(self):
        return self.get("provider_id")

    def set_provider_id(self, value):
        self.set("provider_id", value)

    def get_title(self):
        return self.get("title")

    def set_title(self, value):
        self.set("title", value)

    def get_chapter(self):
        return self.get("chapter")

    def set_chapter(self, value):
        self.set("chapter", value)

    def get_libraries(self):
        return self.get("libraries")

    def set_libraries(self, value):
        self.set("libraries", value)

    def get_current_lib_idx(self):
        return self.get("current_lib_idx")

    def set_current_lib_idx(self, value):
        self.set("current_lib_idx", value)

    def get_library_manager_id(self):
        return self.get("library_manager_id")

    def set_library_manager_id(self, value):
        self.set("library_manager_id", value)

    def get_downscaling(self):
        return self.get("downscaling")

    def set_downscaling(self, value):
        self.set("downscaling", value)

    def get_upscaling(self):
        return self.get("upscaling")

    def set_upscaling(self, value):
        self.set("upscaling", value)

    def get_manual_content_width(self):
        return self.get("manual_content_width")

    def set_manual_content_width(self, value):
        self.set("manual_content_width", value)

    def get_borderless(self):
        return self.get("borderless")

    def set_borderless(self, value):
        self.set("borderless", value)

    def get_hide_titlebar(self):
        return self.get("hide_titlebar")

    def set_hide_titlebar(self, value):
        self.set("hide_titlebar", value)

    def get_hover_effect_all(self):
        return self.get("hover_effect_all")

    def set_hover_effect_all(self, value):
        self.set("hover_effect_all", value)

    def get_acrylic_menus(self):
        return self.get("acrylic_menus")

    def set_acrylic_menus(self, value):
        self.set("acrylic_menus", value)

    def get_acrylic_background(self):
        return self.get("acrylic_background")

    def set_acrylic_background(self, value):
        self.set("acrylic_background", value)

    def get_hide_scrollbar(self):
        return self.get("hide_scrollbar")

    def set_hide_scrollbar(self, value):
        self.set("hide_scrollbar", value)

    def get_stay_on_top(self):
        return self.get("stay_on_top")

    def set_stay_on_top(self, value):
        self.set("stay_on_top", value)

    def get_geometry(self):
        return self.get("geometry")

    def set_geometry(self, value):
        self.set("geometry", value)

    def get_advanced_settings(self):
        return self.get("advanced_settings")

    def set_advanced_settings(self, value):
        self.set("advanced_settings", value)

    def get_chapter_rate(self):
        return self.get("chapter_rate")

    def set_chapter_rate(self, value):
        self.set("chapter_rate", value)

    def get_no_update_info(self):
        return self.get("no_update_info")

    def set_no_update_info(self, value):
        self.set("no_update_info", value)

    def get_not_recommened_update_info(self):
        return self.get("not_recommened_update_info")

    def set_not_recommened_update_info(self, value):
        self.set("not_recommened_update_info", value)

    def get_update_info(self):
        return self.get("update_info")

    def set_update_info(self, value):
        self.set("update_info", value)

    def get_last_scroll_positions(self):
        return self.get("last_scroll_positions")

    def set_last_scroll_positions(self, value):
        self.set("last_scroll_positions", value)

    def get_scrolling_sensitivity(self):
        return self.get("scrolling_sensitivity")

    def set_scrolling_sensitivity(self, value):
        self.set("scrolling_sensitivity", value)

    def get_lazy_loading(self):
        return self.get("lazy_loading")

    def set_lazy_loading(self, value):
        self.set("lazy_loading", value)

    def get_save_last_titles(self):
        return self.get("save_last_titles")

    def set_save_last_titles(self, value):
        self.set("save_last_titles", value)

    def get_show_provider_logo(self):
        return self.get("show_provider_logo")

    def set_show_provider_logo(self, value):
        self.set("show_provider_logo", value)

    def get_show_tutorial(self):
        return self.get("show_tutorial")

    def set_show_tutorial(self, value):
        self.set("show_tutorial", value)

    def setup_database(self, settings):
        # Define tables and their columns
        tables = {
            "settings": ["key TEXT", "value TEXT"]
        }
        # Code to set up the database, initialize password hashes, etc.
        for table_name, columns in tables.items():
            self.db.create_table(table_name, columns)
        for i in self.settings.items():
            self.db.update_info(i, "settings", ["key", "value"])

    def fetch_data(self):
        fetched_data = self.db.get_info("settings", ["key", "value"])
        for item in fetched_data:
            key, value = item
            self.settings[key] = value

    def update_data(self):
        for key, value in self.settings.items():
            self.db.update_info((key, value), "settings", ["key", "value"])

    def close(self):
        self.is_open = False
        self.db.close()


class AutoProviderManager:
    def __init__(self, path: str, absolute_base: _ty.Type) -> None:
        self.path: str = path
        self.absolute_base: _ty.Type = absolute_base
        self.providers: list[_ty.Type] = []

    def _load_providers(self) -> None:
        for file in os.listdir(self.path):
            if file.endswith('.py') or file.endswith('.pyd') and file != '__init__.py':
                module_name: str = file.split(".")[0]
                module_path: str = os.path.join(self.path, file)
                spec: ModuleSpec | None = importlib.util.spec_from_file_location(module_name, module_path)
                if spec is None:
                    continue
                module: _ts.ModuleType = importlib.util.module_from_spec(spec)
                if spec.loader is None:
                    continue
                spec.loader.exec_module(module)
                for attribute_name in dir(module):
                    attribute = getattr(module, attribute_name)
                    if not hasattr(attribute, "register_baseclass"):
                        continue
                    if isinstance(attribute, type) and issubclass(attribute, self.absolute_base) and attribute.register_baseclass != attribute_name:
                        self.providers.append(attribute)

    def get_providers(self) -> list[_ty.Type]:
        self.providers.clear()
        self._load_providers()
        return self.providers


class CacheManager:
    def __init__(self, base_cache_folder: str) -> None:
        self.base_cache_folder = base_cache_folder
        os.makedirs(self.base_cache_folder, exist_ok=True)

    def get_cache_folder(self, chapter: float) -> str:
        folder: str = os.path.join(self.base_cache_folder, str(float(chapter)))
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        return folder

    def is_cache_loaded(self, folder: str) -> bool:
        return os.path.isdir(folder) and len(os.listdir(folder)) > 0

    def clear_cache(self, folder: str) -> None:
        self._clear_folder(folder)

    def clear_all_caches(self) -> None:
        for folder in os.listdir(self.base_cache_folder):
            path = os.path.join(self.base_cache_folder, folder)
            self._clear_folder(path)

    def get_cached_chapters(self) -> list[float]:
        chapters = []
        for folder in os.listdir(self.base_cache_folder):
            try:
                chapters.append(float(folder))
            except ValueError:
                continue  # Ignore non-chapter folders
        return sorted(chapters)

    def ensure_less_than(self, n: int, current: int) -> None:
        if n == -1:
            return

        chapters = self.get_cached_chapters()
        if len(chapters) <= n:
            return

        # Sort chapters by distance from current
        chapters.sort(key=lambda x: abs(x - current), reverse=True)

        # Chapters to remove
        excess = chapters[n:]

        for chapter in excess:
            folder = os.path.join(self.base_cache_folder, str(float(chapter)))
            self._clear_folder(folder)

    def _clear_folder(self, folder: str):
        if os.path.exists(folder):
            shutil.rmtree(folder)
