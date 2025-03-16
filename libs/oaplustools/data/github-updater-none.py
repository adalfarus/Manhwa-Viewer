import requests
import zipfile
import sys
import os
import socket
import traceback


def get_release_asset_download_url(owner, repo, tag, asset_name):
    try:
        releases_url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
        response = requests.get(releases_url)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch release asset download URL: {e}")

    for asset in data.get('assets', []):
        if asset['name'] == asset_name:
            return asset['browser_download_url']

    raise Exception(f"Asset with name '{asset_name}' not found.")


def download_file(url, zip_path, version, callback):
    file_path = os.path.join(zip_path, f"win-{version}.zip")
    if os.path.exists(file_path): 
        yield 100
        callback(file_path)
        print(f"File {file_path} already exists. Skipping download.")
        return
    try:
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
    except requests.RequestException as e:
        raise Exception(f"Failed to download file: {e}")

    with open(file_path, 'wb') as fd:
        for data in response.iter_content(chunk_size=4096):
            fd.write(data)
            progress = int(100 * fd.tell() / total_size)
            yield progress
    
    callback(file_path)


def main(path, zip_path, repo_version, author, repo_name, connection):
    try:
        def handle_file_path(file_path):
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                total_files = len(zip_ref.namelist())
                extracted_files = 0
                for file in zip_ref.namelist():
                    extracted_files += 1
                    zip_ref.extract(file, path)
                    progress = int(100 * extracted_files / total_files)
                    connection.sendall(str(f"{progress}\n").encode())
            connection.sendall(str(True).encode())
            
        url = get_release_asset_download_url(author, repo_name, f"v{repo_version}", f"win-{repo_version}.zip")
        file_gen = download_file(url, zip_path, repo_version, handle_file_path)
        for progress in file_gen:
            connection.sendall(str(f"{progress}\n").encode())

    except Exception as err:
        print(f"Error in main: {err}")
        print(traceback.format_exc().encode())
        connection.sendall((f"Error in main: {err}\n" + traceback.format_exc()).encode())
        connection.sendall(str(False).encode())


class MockConnection:
    @staticmethod
    def sendall(message):
        print(message.decode(), end="")


if __name__ == "__main__":
    try:
        sys.argv = sys.argv[1:]  # ['./', './update', './', '0.0.1', 'Adalfarus', 'unicode-writer']
        if len(sys.argv)-1 < 4:
            print("Not enough arguments provided.")
            sys.exit()

        def boolean(to_bool: any):
            return to_bool.lower() == "true"

        in_array = sys.argv
        safe_array = ['localhost', 5000, False]
        type_array = [str, int, boolean]

        # Start from index 5
        start_index = 5

        # Check and fill up the 'in_array' from 'start_index' using 'safe'
        for i in range(start_index, len(safe_array) + start_index):
            if i >= len(in_array):
                in_array.append(safe_array[i - start_index])
            else:
                in_array[i] = type_array[i - start_index](in_array[i])

        host, port, wait_for_connection = in_array[5:]
        conn = MockConnection()

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            s.listen(1)
            print('Updater started. Waiting for the main application to connect...')

            if wait_for_connection:
                conn, addr = s.accept()
                with conn:
                    print('Connection established.')
                    conn.sendall('Connection established.'.encode())
                    try:
                        main(*in_array[:5], conn)
                    except Exception as e:
                        print(f"Error: {e}")
                        conn.sendall(f"Error: {e}".encode())
            else:
                # Just start the updater without a connection, so no status updates
                print("Updater not waiting for connection. Proceeding with alternative tasks or shutdown.")
                main(*in_array[:5], conn)
    except Exception as e:
        print(f"Global Error: {e}")
        conn.sendall(f"Global Error: {e}".encode())
        