from packaging.version import Version, InvalidVersion
from typing import Tuple, Generator, Union, Literal
from collections import namedtuple
import subprocess
import threading
import requests
import socket
import sys
import os


# Often used types and classes
YieldType = Union[int, None]
ReturnType = Union[None, bool]
UpdateStatusGenerator = Generator[YieldType, None, ReturnType]
ProcessResult = namedtuple('ProcessResult', 'returncode')


class VersionNumber:
    def __init__(self, number: str):
        try:
            self.version = Version(number)
        except InvalidVersion:
            raise ValueError(f"Invalid version number: {number}")

    def __str__(self):
        return str(self.version)

    def __eq__(self, other):
        return self.compare(other, method="__eq__")

    def __ne__(self, other):
        return self.compare(other, method="__ne__")

    def __lt__(self, other):
        return self.compare(other, method="__lt__")

    def __le__(self, other):
        return self.compare(other, method="__le__")

    def __gt__(self, other):
        return self.compare(other, method="__gt__")

    def __ge__(self, other):
        return self.compare(other, method="__ge__")

    def compare(self, other, method):
        if isinstance(other, VersionNumber):
            return getattr(self.version, method)(other.version)
        if isinstance(other, str):
            try:
                other_version = Version(other)
                return getattr(self.version, method)(other_version)
            except InvalidVersion:
                raise ValueError(f"Invalid version number: {other}")
        return NotImplemented


class GithubUpdater:
    def __init__(self, author: str, repo_name: str, version: Literal["exe", "py"] = "exe"):
        self.author = author
        self.repo_name = repo_name
        self.version = version

        self.host = self.port = None

    def get_latest_release_title_version(self) -> Union[None, str]:
        try:
            response = requests.get(f"https://api.github.com/repos/{self.author}/{self.repo_name}/releases/latest")
            repo_version = ''.join([x if sum(c.isnumeric() for c in x) >= 3 else "" for x in
                                    response.json()["name"].split("v")])
            return repo_version
        except KeyError:
            print("Github repo not correctly set-up, please check the documentation and try again.")
        except Exception as e:
            print(f"Unexpected exception occurred: {e}")
        return None

    def get_latest_tag_version(self) -> Union[None, str]:
        try:
            response = requests.get(f"https://api.github.com/repos/{self.author}/{self.repo_name}/tags")
            repo_version = response.json()[0]["name"].replace("v", "")
            return repo_version
        except KeyError:
            print("Github repo not correctly set-up, please check the documentation and try again.")
        except Exception as e:
            print(f"Unexpected exception occurred: {e}")
        return None
        
    def receive_update_status(self) -> UpdateStatusGenerator:

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                bool_map = {'True': True, 'False': False}
                try:
                    while True:
                        data = s.recv(1024)
                        if data:
                            decoded_data = data.decode()
                            if "Error" in decoded_data: print(f"Error occurred: {decoded_data}")
                            elif "Connection" in decoded_data: print(decoded_data)
                            elif decoded_data in bool_map:
                                success = bool_map[decoded_data]
                            else:
                                str_progress_values = decoded_data.split("\n")
                                progress_values = [int(p) for p in str_progress_values if p]
                                for progress_value in progress_values: yield progress_value
                        else:
                            print("Connection closed by updater.")
                            return success
                except ConnectionError as e:
                    print(f"Connection Error: {e}")
        except ConnectionRefusedError:
            print("Connection Refused, maybe your updater isn't running?")
        except Exception as e:
            print(f"Unexpected exception occurred: {e}")
        return None

    def update(self, path: str, zip_path: str, repo_version: str, implementation: Literal["gui", "cmd", "none"],
               host: str = 'localhost', port: int = 5000, non_blocking: bool = False,
               wait_for_connection: bool = False) -> Union[Tuple[bool, None, int],
                                                           Tuple[bool, Exception, int],
                                                           threading.Thread]:
        if implementation not in ["gui", "cmd", "none"]:
            raise ValueError("Invalid implementation option")
        self.host = host
        self.port = port
        returns = (False, Exception(), 1)

        lib_path = os.path.dirname(os.path.abspath(__file__))
        process = ProcessResult(returncode=0)
        arg_base = []

        def subprocess_task():
            proc = subprocess.run(
                arg_base
                + [os.path.join(lib_path, f"github-updater-{implementation}.{self.version}")]
                + [str(arg) for arg in [path, zip_path, repo_version, self.author, self.repo_name, host, port,
                                        wait_for_connection]]
                , shell=True, text=True, capture_output=True
            )
            return proc

        try:
            if self.version == "py":
                arg_base = [sys.executable]
            else:  # You can remove this if you've compliled the updaters
                raise Exception("Executable Updaters have to be compiled by you now.")
            if non_blocking:
                update_thread = threading.Thread(target=subprocess_task)
                # update_thread.start()
                return update_thread
            process = subprocess_task()
            returns = (True, None, process.returncode)
        except Exception as e:
            returns = (False, e, process.returncode)
        self.host = self.port = None
        return returns


def local_test():
    try:
        from oaplustools.io.environment import Path
    
        # Initialize the updater
        updater = GithubUpdater("Adalfarus", "unicode-writer", "py")

        # Setup arguments for the update
        path, zip_path = Path("./test_data/update"), Path("./test_data/zip")
        path.mkdir(".")
        zip_path.mkdir(".")
        repo_version = "0.0.1"
    
        update_thread = updater.update(str(path), str(zip_path), repo_version, "none", "localhost", 1264, True, True)
        update_thread.start()

        # Receive the update status generator and print them
        progress_bar = 1
        print("Starting test update ...")
        for i in updater.receive_update_status():
            print(f"{i}%", end=f" PB{progress_bar}\n")
            if i == 100:
                progress_bar += 1  # Switch to second progress bar, when the downloading is finished
        update_thread.join()
    except Exception as e:
        print(f"Exception occurred {e}.")
        return False
    print("Test completed successfully.")
    return True


if __name__ == "__main__":
    local_test()
