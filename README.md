# ManhwaViewer (NMV)

If you want to use ManhwaViewer (NMV), just download the latest release [here](https://github.com/adalfarus/Manhwa-Viewer-1.6/releases/latest).

### Version showcases:

#### MV1.6.2 vs MV1.5
<p float="center">
  <img src="/repo_images/repo_image_1.png" width="41%" />
  <img src="/repo_images/repo_image_4.png" width="48%" />
</p>

#### NMV1.6.5 & NMV166 Borderless vs MV1.6.4.1 (Both windows are the same size)
<p float="center">
    <img src="/repo_images/repo_image_8.png" width="100%" />
</p>

#### NMV1.6.5 & NMV166 Acrylic Menu Showcase (left) and NMV166 new themes showcase (right)
<p float="center">
    <img src="/repo_images/repo_image_9.png" width="49%" />
    <img src="/repo_images/repo_image_10.png" width="49%" />
</p>

(Everything below this point is accurate for NMV 1.6.5 & NMV 166)

## For Users

### MV, NMV and ADMV:

- **MV** (ManhwaViewer) -> The original Versions from v1.0 to v1.6.4.1, including the content system rewrite in v1.5
- **NMV** (NewManhwaViewer) -> Quick rewrite that doesn't impact user experience while making ManhwaViewer compatible with new internal systems and removes many bugs. This will include all versions up to 1.7.0/170 .
- **SMV** (SuperManhwaViewer) -> Thorough rewrite that uses key insights from other projects. This will include all versions up to 2.0.0/200 .
- **ADMV** (ActDirectManhwaViewer) \[**PLANNED**\] -> A modern version using ActDirect, that uses best practices, is really compatible, efficient and configurable and makes important changes for further apps. This version will be released as ADMV 2.0.0/200

### New Versioning:

Traditionally ManhwaViewers releases used a v[Major].[Minor].[Patch] versioning scheme, it will continue to do so, but more compacted.
For example "v1.6.5" can be reduced to "v165" without losing any information. The meaning of the numbers will not change.

### Basics:

- **Search Bar**: At the top, which can be lowered. It will be grayed out if the current "Provider" does not support search.
- **Side Menu**: Contains all important features. It's less frequently used if you don't change stories often.
- **Optimal Settings**:
  - Chapter rate set to 0.5 (set to 1.0 if you don't want extra chapters without a story).
  - Provider type: Choose between indirect and direct. Direct is generally better or necessary.
  - Scale buttons and default width setting should be self-explanatory.
  - Window modification options: Borderless, Hide Scrollbar, Stay On Top, ...
  - Change your current provider using the "Provider" dropdown menu in the side menu. Included providers are AsuraToon, CoffeManga, HariManga, MangaQueen (can be slow), ManhwaClan, ... . Additional providers can be added through modding.

To read, type relevant keywords into the search bar and double-click the desired result. Restart the program if the chapter and title don't update automatically. Manual entry of the title in the side menu is possible but can cause errors.

The program takes 1-2 seconds to load initially. Images are loaded while scrolling through a chapter, avoiding additional loading times.

# Modding Guide for ManhwaViewer

## Introduction
To mod ManhwaViewer, you need a basic understanding of Python, as the program is written in this language. The windows 7 version runs on [CPython 3.10 by NulAsh](https://github.com/NulAsh/cpython/releases/tag/v3.10.1win7-1) with [PySide2](https://pypi.org/project/PySide2/) and the windows 10-11 version runs on Python 3.12 with [PySide6](https://pypi.org/project/PySide6/). All standard libraries are included.

## Getting Started
1. **Accessing the App Folder**:
   - Right-click on the ManhwaViewer shortcut or search result.
   - Select "Open File Location".
   - Navigate to the `_internal` directory and then open the `extensions` folder.
   - Here, you can either create a new file or modify an existing one.
   - For detailed information, explore the `_interal/modules/AutoProviderPlugin.py` file.

2. **Working with Packages**:
   - Packages can be added to the `_interal/libs` folder, this location is the first python will check so you can overwrite packages.
   - All standard libs have been included as a [pyinstaller option](https://stackoverflow.com/questions/62602954/force-pyinstaller-to-include-all-built-in-modules).
   - Two key steps:
     - Add `from modules.AutoProviderPlugin import AutoProviderPlugin, AutoProviderBaseLike` at the beginning of your code.
     - Your extensions must be a subclass of either `AutoProviderPlugin` or `AutoProviderBaseLike`.

## Creating Extensions
1. **Using `AutoProviderPlugin` and `AutoProviderBaseLike` Classes**:
   - `AutoProviderPlugin` is the base class for all extensions.
   - `AutoProviderBaseLike` inherits from `AutoProviderPlugin` and is tailored for websites that use the same website-base as the ManhwaClan website.

2. **Implementing a Simple Base-like Extension**:
   - Subclass `AutoProviderBaseLike`.
   - Your `__init__` method should accept the parameters (`title`, `chapter`, `chapter_rate`, `data_folder`, `cache_folder`, `provider` and `num_workers`).
   - Pass these parameters along with the website you've chosen as **specific_provider_website** (only the core url, so from `https://www.manhwaclan.com/manga` -> `manhwaclan.com`).
   - Restart the app to see your provider and test it out. Check the logs at **./_internal/data/logs.txt** for errors even if everything seems to work fine.

3. **Creating Custom Site Extensions (Advanced)**:
   - Subclass `AutoProviderPlugin`.
   - Follow similar steps as Base-like extensions, but include additional error handling for e.g. logo downloads as any uncaught exception will crash the program.

## Important Methods and Variables
- Internal Variables: 
  - `title` -- The current Manhwa Title
  - `url_title` -- The current Manhwa Title, made url safe
  - `chapter` -- The current chapter, integer if it's whole and float if it's decimal.
  - `chapter_str` -- A string of the current chapter
  - `chapter_rate` -- Float
  - `data_folder` & `chache_folder` -- Not really used for modding
  - `provider` -- The current provider as a string, can either be "indirect" or "direct"
  - `specific_provider_website` -- Whatever you passed to the parents init call
  - `blacklisted_websites` -- Was used for search engine provider
  - `current_url` -- Holds the current chapter url
  - `clipping_space` -- Tells the program which piece of the logo image can be used as an icon (by default it is height x height)

### Key Methods Overview
Understanding these methods is crucial for successful modding. They play a vital role in how the application processes images and retrieves chapter URLs.

#### 1. `validate_image`
- **Purpose**: Determines which downloaded images qualify as "Chapter Images".
- **Input**: Receives a string representing an image file (e.g., `"image003.png"`).
- **Output**:
  - Returns `file_name` (original name), `file_extension` (original extension), `new_name` (simplified name for internal use), and a boolean flag indicating the validity of the image.

#### 2. `_indirect_provider`
- **Purpose**: Finds the URL for the currently selected chapter based on the current chapter and title. It's an estimation method.
- **Output**: Returns the chapter URL as a string.
- **Behavior**: Utilizes class attributes for its operation.

#### 3. `_direct_provider`
- **Purpose**: Similar to `_indirect_provider`, but designed to actively search for the chapter URL.
- **Output**: Returns the chapter URL as a string.
- **Behavior**: Leverages class attributes and a search mechanism.

#### 4. `get_search_results`
- **Purpose**: Provides search results, primarily used by the search feature of the application.
- **Input**: Takes in a search query as text.
- **Output**: Returns a list in the format `[title, empty_string]`. Should return `False` if the method is not implemented.

### Implementation Recommendations
- Implement a general `_search` method to streamline support for both `get_search_results` and `_direct_provider`.
- Avoid altering other methods to prevent application crashes.
- Custom helper methods can be created, but refrain from using specific reserved method names (listed below).

## Guidelines and Libraries
- Avoid modifying certain methods to prevent crashes.
- Helper methods can be implemented, but avoid any already used names (`__init__`, `urlify`, `get_logo_path`, `set_title`, `get_title`, `set_chapter`, `get_chapter`, `set_chapter_rate`, `get_chapter_rate`, `set_provider`, `get_provider`, `set_current_url`, `get_current_url`, `set_blacklisted_websites`, `get_blacklisted_websites`, `chap`, `next_chapter`, `previous_chapter`, `reload_chapter`, `_handle_cache_result`, `_download_logo_image`, `redo_prep`, `update_current_url`, `_get_current_chapter_url`, `check_url`, `is_crawlable`, `_get_url`, `_google_provider`, `_duckduckgo_provider`, `_bing_provider`, `_indirect_provider`, `_direct_provider`, `get_search_results`, `_empty_cache`, `_download_image_async`, `download_images_async`, `download_images`, `validate_image`, `cache_current_chapter`).
- Included non-standard libraries:
  - `aplustools==1.4.8.4`
  - `beautifulsoup4==4.12.2`
  - `Pillow==10.3.0`
  - `PySide6==6.6.0`
  - `Requests==2.31.0`
  - `urllib3==2.1.0`
  - `packaging==24.0`
  - `stdlib-list==0.10.0`
  - `aiohttp==3.9.5`
  - `aiofiles==23.2.1`

To compatabilty: 
- Windows Vista and lower are untested
- Windows 10-1703 has a different dark mode reg key (you need to set the environment variable to change themes).
- All other Windows versions should work without problems.
- Linux and Mac would need more modification but are also okay, just that I wouldn't be able to easily test them.

## For Programmers

### Bugs
#### The title doesn't update internally and you need to restart the program.
##### Affected versions: 1.6.2 & 1.6.3
##### Fix:
- ~~Open the file {install_location}/_internal/modules/AutoProviderPlugin.py~~
- ~~Go to `line 68` or to the function `set_title`~~
- ~~Add the line **self.url_title = self.urlify(new_title)**~~
- The Classes dir was included with the executable, so it can't be fixed in compiled programs.

#### The task window keeps popping up if the task failed and you close it before reaching 10%.
##### Affected versions: 1.6.2 & 1.6.3
##### Fix (1.6.3):
- ~~Open the file {install_location}/_internal/modules/Classes.py~~
- ~~Go to to the function `updateProgress`~~
- ~~Change the line **while self.current_value == 0 and self.value() < 10:** to **if self.current_value == 0 and self.value() < 10:**~~
- The Classes dir was included with the executable, so it can't be fixed in compiled programs.

### Linux Support (Ubuntu 22.04 LTS ONLY) -- There is a know incompatibility with Wayland & Arch

#### Please note that this was tested only on a fresh install with all default packages installed. Your path to success may vary.

1. **Download the Source Files:**
   - Use git or the GitHub website to download the source files. Unpack them if necessary.

2. **Install Python and Virtual Environment:**
   - Install pip for Python:
     ```bash
     sudo apt-get -y install python3-pip
     ```
   - Install `venv` for Python:
     ```bash
     sudo apt-get install python3.10-venv
     ```
   - Create a virtual environment:
     ```bash
     python3.10 -m venv ./.env
     ```
   - Activate the virtual environment:
     ```bash
     source ./.env/bin/activate
     ```

3. **Install Project Requirements:**
   - Install the required Python packages:
     ```bash
     pip3 install -r requirements.txt
     ```

4. **Install `cpulimit` (Recommended):**
   - To prevent a stray bug from freezing your PC, install `cpulimit`:
     ```bash
     sudo apt-get install cpulimit
     ```

5. **Install Qt Dependency:**
   - To run Qt on Ubuntu 22.04 LTS, install the necessary package:
     ```bash
     sudo apt-get install libxcb-cursor0
     ```

6. **Run the Application:**
   - Use `cpulimit` to run the application with a CPU limit:
     ```bash
     cpulimit -l 50 -- python3.10 nmv.py
     ```
   - Alternatively, run the application without `cpulimit`:
     ```bash
     python3.10 nmv.py
     ```

7. **Update Configuration:**
   - Change `os.environ['LOCALAPPDATA']` to `./data` (or any other folder you want the program data to sit in) in the `config.py` file and the startup section of the program.
   - Copy the directory `./default-config/modules` into `./`.
   - (For older distributions, rename moduless -> modules, move all important folders into _internal, and avoid any os.path.abspath usage in the base paths)

8. **Note on Missing Files:**
   - Depending on how you solved step 7, you will encounter an error about a missing file. The new version of `aplustools` should help detect other systems and handle these issues more easily. You can fix this by making the folder variables using os.path.abspath as we now don't have an absolute path anymore. The lower window corners are never rounded, which seems to be the system default so nothing I can do about that.  You can also disable the default os theme check in timer_tick as it won't be able to detect anything and just throw some error (they won't crash the program, but rather clutter the log file).

By following these steps, you should be able to run the application on Ubuntu 22.04 LTS.
