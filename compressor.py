"""
TextCompressor - Core compression and decompression functions.

Implements frequency-based dictionary encoding for text compression.
"""

import struct
import math
from typing import List, Tuple
from collections import Counter
import re


def tokenize(text: str) -> List[str]:
    """
    Tokenize text into words with trailing whitespace, line endings, and punctuation sequences.

    Tokenization rules:
    - Words: Alphabetic characters plus any following whitespace (spaces/tabs), but NOT line endings
    - Line endings: \r\n treated as single token
    - Punctuation: Consecutive identical or similar punctuation/special characters grouped together

    Args:
        text: Input text to tokenize

    Returns:
        List of tokens preserving all text content
    """
    tokens = []
    i = 0

    while i < len(text):
        # Check for CRLF line ending
        if i < len(text) - 1 and text[i:i+2] == '\r\n':
            tokens.append('\r\n')
            i += 2
        # Check for single newline
        elif text[i] == '\n':
            tokens.append('\n')
            i += 1
        # Check for single carriage return
        elif text[i] == '\r':
            tokens.append('\r')
            i += 1
        # Check for alphabetic word (with trailing spaces/tabs)
        elif text[i].isalpha():
            start = i
            # Collect alphabetic characters
            while i < len(text) and text[i].isalpha():
                i += 1
            # Collect trailing spaces/tabs (but not line endings)
            while i < len(text) and text[i] in (' ', '\t'):
                i += 1
            tokens.append(text[start:i])
        # Check for digit sequences
        elif text[i].isdigit():
            start = i
            while i < len(text) and text[i].isdigit():
                i += 1
            # Collect trailing spaces/tabs
            while i < len(text) and text[i] in (' ', '\t'):
                i += 1
            tokens.append(text[start:i])
        # Handle standalone spaces/tabs (not captured by words)
        elif text[i] in (' ', '\t'):
            start = i
            # Collect consecutive spaces/tabs
            while i < len(text) and text[i] in (' ', '\t'):
                i += 1
            tokens.append(text[start:i])
        # Punctuation and special characters
        else:
            start = i
            # Group consecutive similar punctuation
            # At minimum, consume one character
            i += 1
            while i < len(text) and not text[i].isalnum() and text[i] not in ('\r', '\n', ' ', '\t'):
                i += 1
            tokens.append(text[start:i])

    return tokens


def build_frequency_dict(tokens: List[str]) -> List[str]:
    """
    Build frequency dictionary from tokens, sorted by frequency (descending).

    Args:
        tokens: List of tokens to analyze

    Returns:
        List of unique tokens sorted by frequency (most frequent first)
    """
    # Count token frequencies
    freq_counter = Counter(tokens)

    # Sort by frequency (descending), then alphabetically for ties
    sorted_tokens = sorted(freq_counter.items(), key=lambda x: (-x[1], x[0]))

    # Return just the tokens
    return [token for token, _ in sorted_tokens]


def calculate_position_bytes(dictionary_size: int) -> int:
    """
    Calculate minimum bytes needed to encode dictionary positions.

    Args:
        dictionary_size: Number of unique tokens in dictionary

    Returns:
        Number of bytes needed (1, 2, 3, or 4)
    """
    if dictionary_size == 0:
        return 1

    # Calculate minimum bytes: ceil(log2(size) / 8)
    bits_needed = math.ceil(math.log2(dictionary_size + 1))
    bytes_needed = math.ceil(bits_needed / 8)

    # Cap at 4 bytes (supports up to ~4 billion unique tokens)
    return min(bytes_needed, 4)


def get_struct_format(position_bytes: int) -> str:
    """
    Get struct format string for the given number of bytes.

    Args:
        position_bytes: Number of bytes (1, 2, 3, or 4)

    Returns:
        Struct format string ('B', 'H', or 'I')
    """
    if position_bytes == 1:
        return 'B'  # unsigned char (0-255)
    elif position_bytes == 2:
        return 'H'  # unsigned short (0-65535)
    elif position_bytes in (3, 4):
        return 'I'  # unsigned int (0-4294967295)
    else:
        raise ValueError(f"Unsupported position_bytes: {position_bytes}")


def encode(text: str, dictionary: List[str] = None) -> bytes:
    """
    Compress text using frequency-based dictionary encoding.

    Args:
        text: Input text to compress
        dictionary: Optional pre-built dictionary. If None, builds from text.

    Returns:
        Compressed data as bytes with format:
        [header_byte][dictionary][encoded_content]
    """
    # Tokenize the text
    tokens = tokenize(text)

    # Build dictionary if not provided
    if dictionary is None:
        dictionary = build_frequency_dict(tokens)

    # Calculate position bytes needed
    position_bytes = calculate_position_bytes(len(dictionary))

    # Build dictionary lookup
    token_to_position = {token: i for i, token in enumerate(dictionary)}

    # Start building compressed data
    result = bytearray()

    # Add header byte
    result.append(position_bytes)

    # Add dictionary (tokens separated by chr(0), ended with chr(1))
    for token in dictionary:
        result.extend(token.encode('utf-8'))
        result.append(0)
    result.append(1)

    # Encode tokens as positions
    struct_format = get_struct_format(position_bytes)
    for token in tokens:
        position = token_to_position.get(token, 0)
        if position_bytes == 3:
            # Special handling for 3 bytes - pack as 4 bytes then take first 3
            packed = struct.pack('<I', position)
            result.extend(packed[:3])
        else:
            result.extend(struct.pack('<' + struct_format, position))

    return bytes(result)


def decode(data: bytes) -> str:
    """
    Decompress data encoded with encode().

    Args:
        data: Compressed data bytes

    Returns:
        Original text
    """
    if len(data) < 2:
        raise ValueError("Invalid compressed data: too short")

    # Read header byte
    position_bytes = data[0]

    # Parse dictionary
    dictionary = []
    i = 1
    current_token = bytearray()

    while i < len(data):
        byte = data[i]
        if byte == 0:
            # End of token
            dictionary.append(current_token.decode('utf-8'))
            current_token = bytearray()
        elif byte == 1:
            # End of dictionary
            i += 1
            break
        else:
            current_token.append(byte)
        i += 1

    # Decode content
    result = []
    struct_format = get_struct_format(position_bytes)

    while i < len(data):
        if position_bytes == 3:
            # Special handling for 3 bytes
            if i + 3 > len(data):
                break
            # Pad to 4 bytes and unpack
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


def compress_file(input_path: str, output_path: str) -> Tuple[int, int]:
    """
    Compress a single file.

    Args:
        input_path: Path to input text file
        output_path: Path to output compressed file

    Returns:
        Tuple of (original_size, compressed_size)
    """
    # Read input file
    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()

    original_size = len(text.encode('utf-8'))

    # Compress
    compressed = encode(text)

    # Write output file
    with open(output_path, 'wb') as f:
        f.write(compressed)

    return original_size, len(compressed)


def decompress_file(input_path: str, output_path: str) -> int:
    """
    Decompress a single file.

    Args:
        input_path: Path to compressed file
        output_path: Path to output text file

    Returns:
        Size of decompressed data
    """
    # Read compressed file
    with open(input_path, 'rb') as f:
        compressed = f.read()

    # Decompress
    text = decode(compressed)

    # Write output file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)

    return len(text.encode('utf-8'))


if __name__ == '__main__':
    # Simple test
    test_text = """Hello world! This is a test.
This is a test of the compression algorithm.
Hello world! Hello world!"""

    print("Original text:")
    print(test_text)
    print(f"\nOriginal size: {len(test_text.encode('utf-8'))} bytes")

    # Compress
    compressed = encode(test_text)
    print(f"Compressed size: {len(compressed)} bytes")
    print(f"Compression ratio: {len(compressed) / len(test_text.encode('utf-8')):.2%}")

    # Decompress
    decompressed = decode(compressed)
    print("\nDecompressed text:")
    print(decompressed)

    # Verify
    if decompressed == test_text:
        print("\n✓ Compression is lossless!")
    else:
        print("\n✗ ERROR: Decompressed text doesn't match original!")
