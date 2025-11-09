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


def encode_varint(value: int) -> bytes:
    """
    Encode an integer using variable-length encoding (varint).

    Uses 7 bits per byte for data, with the high bit as a continuation flag:
    - High bit = 1: more bytes follow
    - High bit = 0: last byte

    This efficiently encodes small values in fewer bytes:
    - 0-127: 1 byte
    - 128-16383: 2 bytes
    - 16384-2097151: 3 bytes
    - etc.

    Args:
        value: Non-negative integer to encode

    Returns:
        Variable-length encoded bytes
    """
    if value < 0:
        raise ValueError("Cannot encode negative values")

    result = bytearray()

    while value >= 0x80:  # While value needs more than 7 bits
        # Take lower 7 bits and set continuation bit (0x80)
        result.append((value & 0x7F) | 0x80)
        value >>= 7

    # Last byte: lower 7 bits, no continuation bit
    result.append(value & 0x7F)

    return bytes(result)


def decode_varint(data: bytes, offset: int) -> Tuple[int, int]:
    """
    Decode a variable-length encoded integer.

    Args:
        data: Byte array containing encoded data
        offset: Starting position in data

    Returns:
        Tuple of (decoded_value, bytes_consumed)
    """
    value = 0
    shift = 0
    bytes_read = 0

    while offset + bytes_read < len(data):
        byte = data[offset + bytes_read]
        bytes_read += 1

        # Add the lower 7 bits to our value
        value |= (byte & 0x7F) << shift

        # If high bit is clear, we're done
        if (byte & 0x80) == 0:
            return value, bytes_read

        shift += 7

        # Safety check to prevent infinite loops
        if bytes_read > 10:  # Max needed for 64-bit value
            raise ValueError("Invalid varint encoding: too many bytes")

    raise ValueError("Invalid varint encoding: incomplete")


def encode(text: str, dictionary: List[str] = None) -> bytes:
    """
    Compress text using frequency-based dictionary encoding with variable-length positions.

    Uses varint encoding for token positions, which efficiently encodes:
    - Positions 0-127 in 1 byte
    - Positions 128-16383 in 2 bytes
    - Larger positions in 3+ bytes

    Args:
        text: Input text to compress
        dictionary: Optional pre-built dictionary. If None, builds from text.

    Returns:
        Compressed data as bytes with format:
        [dictionary][encoded_content]
        Dictionary: tokens separated by chr(0), ended with chr(1)
        Encoded content: varint-encoded token positions
    """
    # Tokenize the text
    tokens = tokenize(text)

    # Build dictionary if not provided
    if dictionary is None:
        dictionary = build_frequency_dict(tokens)

    # Build dictionary lookup
    token_to_position = {token: i for i, token in enumerate(dictionary)}

    # Start building compressed data
    result = bytearray()

    # Add dictionary (tokens separated by chr(0), ended with chr(1))
    for token in dictionary:
        result.extend(token.encode('utf-8'))
        result.append(0)
    result.append(1)

    # Encode tokens as varint positions
    for token in tokens:
        position = token_to_position.get(token, 0)
        result.extend(encode_varint(position))

    return bytes(result)


def decode(data: bytes) -> str:
    """
    Decompress data encoded with encode().

    Args:
        data: Compressed data bytes

    Returns:
        Original text
    """
    if len(data) < 1:
        raise ValueError("Invalid compressed data: too short")

    # Parse dictionary
    dictionary = []
    i = 0
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

    # Decode content using varint
    result = []

    while i < len(data):
        try:
            position, bytes_read = decode_varint(data, i)
            i += bytes_read

            if position < len(dictionary):
                result.append(dictionary[position])
        except (ValueError, IndexError):
            # End of data or corrupted
            break

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
