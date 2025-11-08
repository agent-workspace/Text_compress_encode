"""
TextCompressor Archiver - Multi-file archive operations.

Handles creation and extraction of ._t_ archive files with shared dictionary.
"""

import struct
import os
from pathlib import Path
from typing import List, Dict, Tuple
from compressor import tokenize, build_frequency_dict, calculate_position_bytes, get_struct_format


def create_archive(files: List[Path], output: Path) -> Dict[str, any]:
    """
    Create a ._t_ archive from multiple text files with a shared dictionary.

    Archive format:
    [header_byte: chr(N)]
    [shared_dictionary: token + chr(0) + token + chr(0) + ... + chr(1)]
    [file_entry_1]
    [file_entry_2]
    ...

    Each file entry:
    [filename_length: 2 bytes]
    [filename: UTF-8 bytes]
    [chr(2): separator]
    [token_count: 4 bytes]
    [encoded_data: N bytes per token]

    Args:
        files: List of Path objects for input files
        output: Path object for output archive

    Returns:
        Dictionary with statistics (original_size, compressed_size, ratio, file_count)
    """
    if not files:
        raise ValueError("No files provided for archiving")

    # Read all files and collect all tokens
    all_tokens = []
    file_contents = []

    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
                tokens = tokenize(text)
                file_contents.append({
                    'name': file_path.name,
                    'text': text,
                    'tokens': tokens
                })
                all_tokens.extend(tokens)
        except Exception as e:
            raise ValueError(f"Error reading {file_path}: {e}")

    # Build shared dictionary from all tokens
    dictionary = build_frequency_dict(all_tokens)
    position_bytes = calculate_position_bytes(len(dictionary))
    token_to_position = {token: i for i, token in enumerate(dictionary)}

    # Start building archive
    result = bytearray()

    # Add header byte
    result.append(position_bytes)

    # Add shared dictionary
    for token in dictionary:
        result.extend(token.encode('utf-8'))
        result.append(0)
    result.append(1)

    # Add file entries
    struct_format = get_struct_format(position_bytes)

    for file_data in file_contents:
        # Filename length (2 bytes)
        filename_bytes = file_data['name'].encode('utf-8')
        result.extend(struct.pack('<H', len(filename_bytes)))

        # Filename
        result.extend(filename_bytes)

        # Separator
        result.append(2)

        # Token count (4 bytes)
        token_count = len(file_data['tokens'])
        result.extend(struct.pack('<I', token_count))

        # Encoded tokens
        for token in file_data['tokens']:
            position = token_to_position.get(token, 0)
            if position_bytes == 3:
                packed = struct.pack('<I', position)
                result.extend(packed[:3])
            else:
                result.extend(struct.pack('<' + struct_format, position))

    # Write archive
    with open(output, 'wb') as f:
        f.write(result)

    # Calculate statistics
    original_size = sum(len(fc['text'].encode('utf-8')) for fc in file_contents)
    compressed_size = len(result)
    ratio = compressed_size / original_size if original_size > 0 else 0

    return {
        'original_size': original_size,
        'compressed_size': compressed_size,
        'ratio': ratio,
        'file_count': len(file_contents)
    }


def _parse_archive_header(data: bytes) -> Tuple[int, List[str], int]:
    """
    Parse archive header and extract position_bytes, dictionary, and data start position.

    Args:
        data: Archive data bytes

    Returns:
        Tuple of (position_bytes, dictionary, data_start_position)
    """
    if len(data) < 2:
        raise ValueError("Invalid archive: too short")

    # Read header byte
    position_bytes = data[0]

    # Parse dictionary
    dictionary = []
    i = 1
    current_token = bytearray()

    while i < len(data):
        byte = data[i]
        if byte == 0:
            dictionary.append(current_token.decode('utf-8'))
            current_token = bytearray()
        elif byte == 1:
            i += 1
            break
        else:
            current_token.append(byte)
        i += 1

    return position_bytes, dictionary, i


def list_archive(archive: Path) -> List[Dict]:
    """
    List files in archive with metadata.

    Args:
        archive: Path to ._t_ archive file

    Returns:
        List of dictionaries with file information:
        [{'name': filename, 'token_count': count, 'estimated_size': bytes}, ...]
    """
    with open(archive, 'rb') as f:
        data = f.read()

    position_bytes, dictionary, i = _parse_archive_header(data)
    struct_format = get_struct_format(position_bytes)

    files = []

    # Parse file entries
    while i < len(data):
        # Read filename length
        if i + 2 > len(data):
            break
        filename_length = struct.unpack('<H', data[i:i+2])[0]
        i += 2

        # Read filename
        if i + filename_length > len(data):
            break
        filename = data[i:i+filename_length].decode('utf-8')
        i += filename_length

        # Read separator (chr(2))
        if i >= len(data) or data[i] != 2:
            break
        i += 1

        # Read token count
        if i + 4 > len(data):
            break
        token_count = struct.unpack('<I', data[i:i+4])[0]
        i += 4

        # Skip encoded data
        encoded_size = token_count * position_bytes
        if i + encoded_size > len(data):
            break

        # Estimate decompressed size (rough estimate)
        estimated_size = token_count * 5  # Average token size estimate

        files.append({
            'name': filename,
            'token_count': token_count,
            'estimated_size': estimated_size,
            'encoded_size': encoded_size
        })

        i += encoded_size

    return files


def preview_file(archive: Path, filename: str) -> str:
    """
    Preview (decode and return) content of a file from archive without extracting.

    Args:
        archive: Path to ._t_ archive file
        filename: Name of file to preview

    Returns:
        Decoded text content
    """
    with open(archive, 'rb') as f:
        data = f.read()

    position_bytes, dictionary, i = _parse_archive_header(data)
    struct_format = get_struct_format(position_bytes)

    # Find the file entry
    while i < len(data):
        # Read filename length
        if i + 2 > len(data):
            break
        filename_length = struct.unpack('<H', data[i:i+2])[0]
        i += 2

        # Read filename
        if i + filename_length > len(data):
            break
        current_filename = data[i:i+filename_length].decode('utf-8')
        i += filename_length

        # Read separator
        if i >= len(data) or data[i] != 2:
            break
        i += 1

        # Read token count
        if i + 4 > len(data):
            break
        token_count = struct.unpack('<I', data[i:i+4])[0]
        i += 4

        # Calculate encoded data size
        encoded_size = token_count * position_bytes

        if current_filename == filename:
            # Found the file - decode it
            result = []
            end_pos = i + encoded_size

            while i < end_pos and i < len(data):
                if position_bytes == 3:
                    if i + 3 > len(data):
                        break
                    packed = data[i:i+3] + b'\x00'
                    position = struct.unpack('<I', packed)[0]
                    i += 3
                else:
                    if i + position_bytes > len(data):
                        break
                    packed = data[i:i+position_bytes]
                    position = struct.unpack('<' + struct_format, packed)[0]
                    i += position_bytes

                if position < len(dictionary):
                    result.append(dictionary[position])

            return ''.join(result)

        # Skip encoded data
        i += encoded_size

    raise ValueError(f"File '{filename}' not found in archive")


def extract_from_archive(archive: Path, filename: str, output: Path) -> None:
    """
    Extract a single file from archive.

    Args:
        archive: Path to ._t_ archive file
        filename: Name of file to extract
        output: Path for extracted file
    """
    content = preview_file(archive, filename)

    with open(output, 'w', encoding='utf-8') as f:
        f.write(content)


def extract_all(archive: Path, output_dir: Path) -> List[str]:
    """
    Extract all files from archive to a directory.

    Args:
        archive: Path to ._t_ archive file
        output_dir: Directory path for extracted files

    Returns:
        List of extracted filenames
    """
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get list of files in archive
    files = list_archive(archive)

    extracted = []
    for file_info in files:
        filename = file_info['name']
        output_path = output_dir / filename

        try:
            extract_from_archive(archive, filename, output_path)
            extracted.append(filename)
        except Exception as e:
            print(f"Warning: Failed to extract {filename}: {e}")

    return extracted


if __name__ == '__main__':
    # Simple test
    from pathlib import Path

    # Create test files
    test_dir = Path('test_archive_data')
    test_dir.mkdir(exist_ok=True)

    test_file1 = test_dir / 'file1.txt'
    test_file2 = test_dir / 'file2.txt'

    with open(test_file1, 'w', encoding='utf-8') as f:
        f.write("Hello world! This is file 1.\nHello world again!")

    with open(test_file2, 'w', encoding='utf-8') as f:
        f.write("This is file 2.\nHello world! Testing compression.")

    # Create archive
    archive_path = Path('test.t')
    stats = create_archive([test_file1, test_file2], archive_path)

    print(f"Archive created: {archive_path}")
    print(f"Files: {stats['file_count']}")
    print(f"Original size: {stats['original_size']} bytes")
    print(f"Compressed size: {stats['compressed_size']} bytes")
    print(f"Compression ratio: {stats['ratio']:.2%}")

    # List archive
    print("\nArchive contents:")
    for file_info in list_archive(archive_path):
        print(f"  {file_info['name']}: {file_info['token_count']} tokens")

    # Preview file
    print("\nPreview of file1.txt:")
    content = preview_file(archive_path, 'file1.txt')
    print(content)

    # Extract all
    extract_dir = Path('extracted')
    extracted = extract_all(archive_path, extract_dir)
    print(f"\nExtracted {len(extracted)} files to {extract_dir}")

    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    shutil.rmtree(extract_dir)
    archive_path.unlink()
    print("\nTest cleanup complete")
