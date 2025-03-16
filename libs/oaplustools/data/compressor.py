import lzma
import brotli
import json
import os
import zstandard as zstd
import py7zr
import io
from typing import Type, Union, Tuple


class FileContainer:
    def __init__(self, compressor: "ChunkCompressorBase", block_size: int = 1024 * 1024):  # Block size of 1 MB
        self.compressor = compressor
        self.block_size = block_size
        self.current_block = bytearray()
        self.compressed_data = bytearray()
        self.files = {}
        self.block_offsets = []

    def _compress_current_block(self):
        if self.current_block:
            compressed_block = self.compressor.compress(self.current_block)
            self.block_offsets.append({'start': len(self.compressed_data), 'length': len(compressed_block)})
            self.compressed_data.extend(compressed_block)
            self.current_block = bytearray()

    def add_file(self, filename: str, data: bytes):
        if len(self.current_block) + len(data) > self.block_size:
            self._compress_current_block()

        file_info = {
            'block_index': len(self.block_offsets),
            'start': len(self.current_block),
            'length': len(data)
        }
        self.current_block.extend(data)
        self.files[filename] = file_info

        if len(self.current_block) >= self.block_size:
            self._compress_current_block()

    def get_compressed_container(self) -> bytes:
        self._compress_current_block()  # Compress any remaining data in the current block
        index_data = json.dumps({'files': self.files, 'blocks': self.block_offsets}).encode()
        index_length = len(index_data).to_bytes(4, 'big')
        return index_length + index_data + self.compressed_data

    def extract_file(self, compressed_container: bytes, filename: str) -> bytes:
        index_length = int.from_bytes(compressed_container[:4], 'big')
        index_data = compressed_container[4:4 + index_length]
        index = json.loads(index_data)

        file_info = index['files'][filename]
        block_info = index['blocks'][file_info['block_index']]

        start_block = block_info['start']
        length_block = block_info['length']
        compressed_block = compressed_container[
                           4 + index_length + start_block:4 + index_length + start_block + length_block]

        decompressed_block = self.compressor.decompress(compressed_block)

        start_file = file_info['start']
        length_file = file_info['length']
        return decompressed_block[start_file:start_file + length_file]


class FileContainerV2:
    def __init__(self, compressor: "ChunkCompressorBase", block_size: int = 1024 * 1024):  # Block size of 1 MB
        self.compressor = compressor
        self.block_size = block_size
        self.current_block = bytearray()
        self.compressed_data = bytearray()
        self.file_info = {}  # Stores info about files by filename
        self.index_to_name = []  # Maps numeric indexes to filenames
        self.block_offsets = []

    def _compress_current_block(self):
        if self.current_block:
            compressed_block = self.compressor.compress(self.current_block)
            self.block_offsets.append({'start': len(self.compressed_data), 'length': len(compressed_block)})
            self.compressed_data.extend(compressed_block)
            self.current_block = bytearray()

    def add_file(self, filename: str, data: bytes) -> int:
        if len(self.current_block) + len(data) > self.block_size:
            self._compress_current_block()

        file_index = len(self.index_to_name)
        self.index_to_name.append(filename)
        self.file_info[filename] = {
            'index': file_index,
            'block_index': len(self.block_offsets),
            'start': len(self.current_block),
            'length': len(data)
        }
        self.current_block.extend(data)

        if len(self.current_block) >= self.block_size:
            self._compress_current_block()

        return file_index

    def get_compressed_container(self) -> bytes:
        self._compress_current_block()  # Compress any remaining data in the current block
        index_data = json.dumps({'file_info': self.file_info, 'block_offsets': self.block_offsets, 'index_to_name': self.index_to_name}).encode()
        index_length = len(index_data).to_bytes(4, 'big')
        return index_length + index_data + self.compressed_data

    def extract_file(self, compressed_container: bytes, file_identifier: Union[str, int]) -> bytes:
        index_length = int.from_bytes(compressed_container[:4], 'big')
        index_data = compressed_container[4:4 + index_length]
        index = json.loads(index_data)

        filename = file_identifier if isinstance(file_identifier, str) else index['index_to_name'][file_identifier]
        file_info = index['file_info'][filename]
        block_info = index['block_offsets'][file_info['block_index']]

        start_block = block_info['start']
        length_block = block_info['length']
        compressed_block = compressed_container[4 + index_length + start_block:4 + index_length + start_block + length_block]

        decompressed_block = self.compressor.decompress(compressed_block)

        start_file = file_info['start']
        length_file = file_info['length']
        return decompressed_block[start_file:start_file + length_file]


class FileContainerV3:
    def __init__(self, compressor: "ChunkCompressorBase", block_size: int = 1024 * 1024):  # Block size of 1 MB
        self.compressor = compressor
        self.block_size = block_size
        self.current_block = bytearray()
        self.compressed_data = bytearray()
        self.file_info = {}  # Stores info about files by filename
        self.index_to_name = []  # Maps numeric indexes to filenames
        self.block_offsets = []

    def _compress_current_block(self):
        if self.current_block:
            compressed_block = self.compressor.compress(self.current_block)
            self.block_offsets.append({'start': len(self.compressed_data), 'length': len(compressed_block)})
            self.compressed_data.extend(compressed_block)
            self.current_block = bytearray()

    def add_file(self, filename: str, data: bytes) -> int:
        if len(self.current_block) + len(data) > self.block_size:
            self._compress_current_block()

        file_index = len(self.index_to_name)
        self.index_to_name.append(filename)
        self.file_info[filename] = {
            'index': file_index,
            'block_index': len(self.block_offsets),
            'start': len(self.current_block),
            'length': len(data)
        }
        self.current_block.extend(data)

        if len(self.current_block) >= self.block_size:
            self._compress_current_block()

        return file_index

    def get_compressed_container(self) -> bytes:
        self._compress_current_block()  # Compress any remaining data in the current block
        index_data = json.dumps({'file_info': self.file_info, 'block_offsets': self.block_offsets, 'index_to_name': self.index_to_name}).encode()
        compressed_index_data = self.compressor.compress(index_data)
        index_length = len(compressed_index_data).to_bytes(4, 'big')
        return index_length + compressed_index_data + self.compressed_data

    def extract_file(self, compressed_container: bytes, file_identifier: Union[str, int]) -> bytes:
        compressed_index_length = int.from_bytes(compressed_container[:4], 'big')
        compressed_index_data = compressed_container[4:4 + compressed_index_length]
        index_data = self.compressor.decompress(compressed_index_data)
        index = json.loads(index_data)

        filename = file_identifier if isinstance(file_identifier, str) else index['index_to_name'][file_identifier]
        file_info = index['file_info'][filename]
        block_info = index['block_offsets'][file_info['block_index']]

        start_block = block_info['start']
        length_block = block_info['length']
        compressed_block = compressed_container[4 + compressed_index_length + start_block:4 + compressed_index_length + start_block + length_block]

        decompressed_block = self.compressor.decompress(compressed_block)

        start_file = file_info['start']
        length_file = file_info['length']
        return decompressed_block[start_file:start_file + length_file]

    def get_compressed_container_info(self, compressed_container: bytes) -> Tuple[int, dict, list]:
        """Returns a tuple(Number of Files, Index to name dictionary and an in-order name list)"""
        compressed_index_length = int.from_bytes(compressed_container[:4], 'big')
        compressed_index_data = compressed_container[4:4 + compressed_index_length]
        index_data = self.compressor.decompress(compressed_index_data)
        index = json.loads(index_data)
        return (len(index['file_info']),
                {i: name for i, name in enumerate(index['index_to_name'])}, index['index_to_name'])


class ChunkCompressorBase:
    def compress(self, data_chunk: bytes) -> bytes:
        return data_chunk

    def decompress(self, compressed_chunk: bytes) -> bytes:
        return compressed_chunk


class BrotliChunkCompressor(ChunkCompressorBase):
    def __init__(self, quality: int = 11):  # Maximum compression quality
        self.quality = quality

    def compress(self, data_chunk: bytes) -> bytes:
        # Compress the data chunk with Brotli
        return brotli.compress(data_chunk, quality=self.quality)

    def decompress(self, compressed_chunk: bytes) -> bytes:
        # Decompress the data chunk with Brotli
        return brotli.decompress(compressed_chunk)

    @staticmethod
    def add_markers(data, start_marker, end_marker):
        # Add start and end markers to the data
        return start_marker + data + end_marker


class LZMAChunkCompressor(ChunkCompressorBase):
    def __init__(self, preset=lzma.PRESET_EXTREME):
        self.preset = preset

    def compress(self, data_chunk: bytes) -> bytes:
        # Compress the data chunk with LZMA
        return lzma.compress(data_chunk, preset=self.preset)

    def decompress(self, compressed_chunk: bytes) -> bytes:
        # Decompress the data chunk with LZMA
        return lzma.decompress(compressed_chunk)


class ZstdCompressor(ChunkCompressorBase):
    def __init__(self, level: int=3):
        self.compressor = zstd.ZstdCompressor(level=level)
        self.decompressor = zstd.ZstdDecompressor()

    def compress(self, data_chunk: bytes) -> bytes:
        return self.compressor.compress(data_chunk)

    def decompress(self, compressed_chunk: bytes) -> bytes:
        return self.decompressor.decompress(compressed_chunk)


class LZMA2Compressor(ChunkCompressorBase):
    def compress(self, data_chunk: bytes) -> bytes:
        with io.BytesIO() as buffer, py7zr.SevenZipFile(buffer, 'w', filters=[{'id': py7zr.FILTER_LZMA2}]) as archive:
            # Create a file-like object from data_chunk
            file_like_data = io.BytesIO(data_chunk)
            archive.write({"data": file_like_data})
            buffer.seek(0)  # Reset buffer position to the beginning
            return buffer.getvalue()

    def decompress(self, compressed_chunk: bytes) -> bytes:
        with io.BytesIO(compressed_chunk) as input_buffer, py7zr.SevenZipFile(input_buffer, 'r') as archive:
            output_buffer = io.BytesIO()
            archive.extractall(path=output_buffer)
            output_buffer.seek(0)  # Reset buffer position to the beginning
            return output_buffer.read()


def local_test():
    try:
        compressor = BrotliChunkCompressor()
        container = FileContainerV3(compressor, block_size=2048 * 2048)

        data = {}
        for root, dirs, files in os.walk("./test_data"):
            for file in files:
                with open(os.path.join(root, file), "rb") as f:
                    image_file_data = b''.join(f.readlines())
                    data[file] = image_file_data

        for file_name, image in data.items():
            container.add_file(file_name, image)

        # Get the compressed data
        compressed_data = container.get_compressed_container()

        print("Compression done")

        with open("./test_data/files.bin", "wb") as f:
            f.write(compressed_data)

        print("Wrote bin")

        # To extract a specific file from the compressed data
        try:
            decompressed_files = []
            for i in range(len(data)):
                decompressed_file = container.extract_file(compressed_data, i)
                decompressed_files.append(decompressed_file)
        except Exception as e:
            print("Indexing not possible, error", e, "\n")
            decompressed_files = []
            for file_name in data.keys():
                decompressed_file = container.extract_file(compressed_data, file_name)
                decompressed_files.append(decompressed_file)
        compression_ratio = len(compressed_data) / sum(len(x) for x in data.values())

        print(f"Original size: {sum(len(x) for x in data.values())} bytes")
        print(f"Compressed size: {len(compressed_data)} bytes")
        print(f"Compression ratio: {compression_ratio:.2f}")

        for i, decompressed_file in enumerate(decompressed_files):
            with open(f"./test_data/file_{i}.ext", "wb") as f:
                f.write(decompressed_file)
    except Exception as e:
        print(f"An error occurred: {e}")
        return False
    print("Test completed successfully.")
    return True


if __name__ == "__main__":
    local_test()
