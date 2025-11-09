"""
TextCompressor Archiver - Multi-file archive operations.

Handles creation and extraction of ._t_ archive files with shared dictionary.
"""

import struct
import os
from pathlib import Path
from typing import List, Dict, Tuple, Union
from compressor import tokenize, build_frequency_dict, encode_varint, decode_varint


def _collect_files(paths: List[Path], base_path: Path = None) -> List[Tuple[Path, str]]:
    """
    Collect all text files from given paths (files and directories).

    Args:
        paths: List of file or directory paths
        base_path: Base path for calculating relative paths (optional)

    Returns:
        List of tuples: (absolute_path, relative_path_in_archive)
    """
    collected = []

    for path in paths:
        if not path.exists():
            raise ValueError(f"Path does not exist: {path}")

        if path.is_file():
            # Single file
            if base_path:
                # Calculate relative path from base
                try:
                    rel_path = path.relative_to(base_path)
                except ValueError:
                    # If not relative to base, just use filename
                    rel_path = path.name
            else:
                # No base path, just use filename
                rel_path = path.name

            collected.append((path, str(rel_path)))

        elif path.is_dir():
            # Directory - recursively scan for all files
            if not base_path:
                base_path = path  # Use directory itself as base

            for file_path in sorted(path.rglob('*')):
                if file_path.is_file():
                    # Calculate relative path from base directory
                    rel_path = file_path.relative_to(base_path)
                    collected.append((file_path, str(rel_path)))

    return collected


def create_archive(paths: Union[List[Path], List[str]], output: Path, base_path: Path = None) -> Dict[str, any]:
    """
    Create a ._t_ archive from files and/or directories with a shared dictionary.

    Supports:
    - Individual files
    - Entire directories (recursively scanned)
    - Mixed files and directories
    - Preserves directory structure in archive

    Archive format:
    [shared_dictionary: token + chr(0) + token + chr(0) + ... + chr(1)]
    [file_entry_1]
    [file_entry_2]
    ...

    Each file entry:
    [filepath_length: 2 bytes]
    [filepath: UTF-8 bytes (relative path with directories)]
    [chr(2): separator]
    [token_count: 4 bytes]
    [encoded_data: varint-encoded token positions]

    Args:
        paths: List of Path objects or strings for input files/directories
        output: Path object for output archive
        base_path: Optional base path for calculating relative paths

    Returns:
        Dictionary with statistics (original_size, compressed_size, ratio, file_count)
    """
    # Convert strings to Paths
    path_list = [Path(p) if isinstance(p, str) else p for p in paths]

    if not path_list:
        raise ValueError("No paths provided for archiving")

    # Collect all files from paths (handles directories recursively)
    file_list = _collect_files(path_list, base_path)

    if not file_list:
        raise ValueError("No files found in provided paths")

    # Read all files and collect all tokens
    all_tokens = []
    file_contents = []

    for file_path, rel_path in file_list:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
                tokens = tokenize(text)
                file_contents.append({
                    'path': rel_path,  # Store relative path with directories
                    'text': text,
                    'tokens': tokens
                })
                all_tokens.extend(tokens)
        except Exception as e:
            # Skip non-text files or unreadable files
            print(f"Warning: Skipping {file_path}: {e}")
            continue

    # Build shared dictionary from all tokens
    dictionary = build_frequency_dict(all_tokens)
    token_to_position = {token: i for i, token in enumerate(dictionary)}

    # Start building archive
    result = bytearray()

    # Add shared dictionary
    for token in dictionary:
        result.extend(token.encode('utf-8'))
        result.append(0)
    result.append(1)

    # Add file entries
    for file_data in file_contents:
        # File path length (2 bytes) - now includes directory structure
        filepath_bytes = file_data['path'].encode('utf-8')
        result.extend(struct.pack('<H', len(filepath_bytes)))

        # File path (with directory structure)
        result.extend(filepath_bytes)

        # Separator
        result.append(2)

        # Token count (4 bytes)
        token_count = len(file_data['tokens'])
        result.extend(struct.pack('<I', token_count))

        # Encoded tokens using varint
        for token in file_data['tokens']:
            position = token_to_position.get(token, 0)
            result.extend(encode_varint(position))

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


def _parse_archive_header(data: bytes) -> Tuple[List[str], int]:
    """
    Parse archive header and extract dictionary and data start position.

    Args:
        data: Archive data bytes

    Returns:
        Tuple of (dictionary, data_start_position)
    """
    if len(data) < 1:
        raise ValueError("Invalid archive: too short")

    # Parse dictionary
    dictionary = []
    i = 0
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

    return dictionary, i


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

    dictionary, i = _parse_archive_header(data)

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

        # Skip varint-encoded data by reading token_count varints
        start_pos = i
        for _ in range(token_count):
            if i >= len(data):
                break
            try:
                _, bytes_read = decode_varint(data, i)
                i += bytes_read
            except ValueError:
                break

        encoded_size = i - start_pos

        # Estimate decompressed size (rough estimate)
        estimated_size = token_count * 5  # Average token size estimate

        files.append({
            'name': filename,
            'token_count': token_count,
            'estimated_size': estimated_size,
            'encoded_size': encoded_size
        })

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

    dictionary, i = _parse_archive_header(data)

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

        if current_filename == filename:
            # Found the file - decode it using varint
            result = []

            for _ in range(token_count):
                if i >= len(data):
                    break
                try:
                    position, bytes_read = decode_varint(data, i)
                    i += bytes_read

                    if position < len(dictionary):
                        result.append(dictionary[position])
                except ValueError:
                    break

            return ''.join(result)

        # Skip varint-encoded data
        for _ in range(token_count):
            if i >= len(data):
                break
            try:
                _, bytes_read = decode_varint(data, i)
                i += bytes_read
            except ValueError:
                break

    raise ValueError(f"File '{filename}' not found in archive")


def extract_from_archive(archive: Path, filename: str, output: Path) -> None:
    """
    Extract a single file from archive.

    Args:
        archive: Path to ._t_ archive file
        filename: Relative path of file to extract (may include directories)
        output: Path for extracted file
    """
    content = preview_file(archive, filename)

    # Create parent directories if they don't exist
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, 'w', encoding='utf-8') as f:
        f.write(content)


def extract_all(archive: Path, output_dir: Path) -> List[str]:
    """
    Extract all files from archive to a directory, preserving directory structure.

    Args:
        archive: Path to ._t_ archive file
        output_dir: Directory path for extracted files

    Returns:
        List of extracted file paths (with directory structure)
    """
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get list of files in archive
    files = list_archive(archive)

    extracted = []
    for file_info in files:
        filepath = file_info['name']  # This may include directory paths
        output_path = output_dir / filepath  # Preserves directory structure

        try:
            extract_from_archive(archive, filepath, output_path)
            extracted.append(filepath)
        except Exception as e:
            print(f"Warning: Failed to extract {filepath}: {e}")

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
