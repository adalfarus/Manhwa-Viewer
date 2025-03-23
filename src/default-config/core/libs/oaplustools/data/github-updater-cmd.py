from oaplustools.io.environment import get_temp
from oaplustools.data import updaters
from typing import List
import sys
import os


def main(path, repo_version, author, repo_name, host, port):
    # Initialize the updater
    updater = updaters.GithubUpdater(author, repo_name, "py")
    tmpdir = os.path.join(get_temp(), f"update_{repo_name}")

    os.makedirs(path, exist_ok=True)
    os.makedirs(tmpdir, exist_ok=True)

    # Setup update thread for the update
    update_thread = updater.update(path, tmpdir, repo_version, "none", host, port, True, True)
    update_thread.start()

    # Receive the update status generator and print them
    progress_bar = 1
    print("Starting update ...")
    for i in updater.receive_update_status():
        print(f"{i}%", end=f" PB{progress_bar}\n")
        if i == 100:
            progress_bar += 1  # Switch to second progress bar, when the downloading is finished
    update_thread.join()


try:
    in_array: List[any] = sys.argv[1:8]  # Exclude script path and bool flags
    if len(in_array) - 1 < 4:  # If enough arguments were passed
        print("Not enough arguments provided. Please input them manually.")
        in_array[0] = str(input("Path: "))  # path e.g. ./save
        in_array[2] = str(input("Repo_version: "))  # Repo Version e.g. 1.0.0
        in_array[3] = str(input("Author: "))  # Author of repo
        in_array[4] = str(input("Repo_name: "))  # Repo name
        in_array[5] = str(input("Host: "))  # Server host
        in_array[6] = int(input("Port: "))  # Server port
    else:
        if len(in_array) - 1 < 5:
            in_array.append('localhost')
            in_array.append(5000)
        elif len(in_array) - 1 < 6:
            in_array.append(5000)
        else:
            in_array[6] = int(in_array[6])
    in_array.pop(1)
    main(*in_array)
except Exception as e:
    print(f"Error: {e}")
else:
    print("Update done!")
