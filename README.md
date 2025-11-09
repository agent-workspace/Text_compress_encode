# TextCompressor - Frequency-Based Text Compression Utility

A Python-based text compression tool with a tkinter GUI that uses frequency-based dictionary encoding to compress single or multiple text files into a custom archive format with `._t_` extension.

## Features

- **Lossless Compression**: 100% byte-perfect compression and decompression
- **Smart Tokenization**: Preserves whitespace, line endings, and punctuation exactly
- **Directory Support**: Archive entire folder structures with preserved hierarchy
- **Multi-file Archives**: Compress multiple files with a shared dictionary for better compression
- **Recursive Scanning**: Automatically includes all files in subdirectories
- **User-Friendly GUI**: Easy-to-use tkinter interface with directory browser
- **Archive Browser**: Preview and extract files without full extraction
- **Unicode Support**: Full support for non-ASCII characters and emojis
- **Variable-Length Encoding**: Efficient varint encoding eliminates wasteful null bytes

## Installation

No external dependencies required! Uses only Python standard library.

```bash
git clone <repository-url>
cd Text_compress_encode
```

Requirements:
- Python 3.7 or higher
- tkinter (usually included with Python)

## Quick Start

### GUI Application

Launch the graphical interface:

```bash
python gui.py
```

The GUI provides three main sections:
1. **File Selection**: Add files, add directories, remove, and clear selection
2. **Operations**: Compress to archive or extract archives with compression stats
3. **Archive Browser**: Browse, preview, and extract files from archives

Features:
- **Add Files**: Select individual text files
- **Add Directory**: Browse and add entire directories (recursively scanned)
- Archive browser shows file paths with directory structure
- Extraction recreates original directory hierarchy

### Command Line Usage

#### Compress a Single File

```python
from compressor import compress_file

# Compress a text file
original_size, compressed_size = compress_file('input.txt', 'output._t_')
print(f"Compression ratio: {compressed_size/original_size*100:.1f}%")
```

#### Compress Multiple Files to Archive

```python
from pathlib import Path
from archiver import create_archive

# Create archive from multiple files
files = [Path('file1.txt'), Path('file2.txt'), Path('file3.txt')]
stats = create_archive(files, Path('archive._t_'))

print(f"Compressed {stats['file_count']} files")
print(f"Original: {stats['original_size']:,} bytes")
print(f"Compressed: {stats['compressed_size']:,} bytes")
print(f"Ratio: {stats['ratio']*100:.1f}%")
```

#### Archive Entire Directories

```python
from pathlib import Path
from archiver import create_archive

# Archive entire directory (recursively scans all files)
stats = create_archive([Path('my_project')], Path('project._t_'))

print(f"Archived directory with {stats['file_count']} files")
print(f"Compression ratio: {stats['ratio']*100:.1f}%")
```

#### Extract Archive (Preserves Directory Structure)

```python
from pathlib import Path
from archiver import extract_all

# Extract all files, recreating directory structure
extracted = extract_all(Path('project._t_'), Path('output_dir'))
print(f"Extracted {len(extracted)} files with directory structure")
```

#### Mixed Files and Directories

```python
from pathlib import Path
from archiver import create_archive

# Archive mix of individual files and directories
paths = [
    Path('file1.txt'),
    Path('docs/'),          # Entire directory
    Path('src/'),           # Another directory
    Path('config.json')
]
stats = create_archive(paths, Path('mixed._t_'))
```

#### Extract Archive

```python
from pathlib import Path
from archiver import extract_all

# Extract all files from archive
extracted = extract_all(Path('archive._t_'), Path('output_dir'))
print(f"Extracted {len(extracted)} files")
```

#### Preview File in Archive

```python
from pathlib import Path
from archiver import preview_file

# Preview a file without extracting
content = preview_file(Path('archive._t_'), 'file1.txt')
print(content)
```

## How It Works

### Compression Algorithm

TextCompressor uses frequency-based dictionary encoding:

1. **Tokenization**: Text is split into tokens using smart rules:
   - Words with trailing whitespace (spaces/tabs, but not line endings)
   - Line endings (CRLF treated as single token)
   - Punctuation sequences (grouped together)
   - Standalone whitespace

2. **Frequency Analysis**: Tokens are sorted by frequency (most common first)

3. **Variable-Length Encoding (Varint)**: Each token is replaced by its position in the frequency dictionary using efficient variable-length encoding:
   - Positions 0-127: 1 byte
   - Positions 128-16,383: 2 bytes
   - Larger positions: 3+ bytes
   - This eliminates wasteful null bytes and adapts to dictionary size!

4. **Archive Format**:
   ```
   [Dictionary] - Tokens separated by chr(0), ended with chr(1)
   [Encoded content] - Varint-encoded token positions
   ```

### Multi-File Archives

When compressing multiple files:
- A **shared dictionary** is built from all files combined
- This maximizes compression for files with similar content
- Each file entry includes filename, separator, token count, and encoded data

### Tokenization Examples

```python
from compressor import tokenize

# Words with trailing spaces
text = "Hello world"
tokens = tokenize(text)
# Result: ['Hello ', 'world']

# Preserves multiple spaces
text = "word1     word2"
tokens = tokenize(text)
# Result: ['word1', '     ', 'word2']

# Preserves line endings
text = "Line1\r\nLine2"
tokens = tokenize(text)
# Result: ['Line1', '\r\n', 'Line2']

# Groups punctuation
text = "Hello!!! World???"
tokens = tokenize(text)
# Result: ['Hello', '!!!', ' ', 'World', '???']
```

## Performance

Compression performance depends on content characteristics:

- **Best for**: Repetitive text, code files, documents with common words
- **Example**: Python code with repeated keywords can achieve 80-90% compression
- **Note**: Small files with diverse content may increase in size due to dictionary overhead

Test results from sample files:
- `test_code.py`: 673 → 594 bytes (88.3%)
- `test_simple.txt`: 494 → 559 bytes (113.2%)
- `test_unicode.txt`: 685 → 1030 bytes (150.4%)

## Testing

Run the comprehensive test suite:

```bash
python test_suite.py
```

The test suite includes:
- **Tokenization Tests**: Verify correct handling of all character types
- **Compression Tests**: Verify lossless compression and decompression
- **Archive Tests**: Verify multi-file archive operations
- **Real File Tests**: Test with actual sample files

All tests verify byte-perfect reconstruction of original files.

## Project Structure

```
Text_compress_encode/
├── compressor.py       # Core compression/decompression functions
├── archiver.py         # Multi-file archive operations
├── gui.py              # Tkinter GUI application
├── test_suite.py       # Comprehensive test suite
├── test_data/          # Sample test files
│   ├── test_simple.txt
│   ├── test_code.py
│   ├── test_edge_cases.txt
│   └── test_unicode.txt
└── README.md           # This file
```

## API Reference

### compressor.py

- `tokenize(text: str) -> List[str]`: Tokenize text into smart tokens
- `build_frequency_dict(tokens: List[str]) -> List[str]`: Build frequency-sorted dictionary
- `encode(text: str, dictionary: List[str] = None) -> bytes`: Compress text
- `decode(data: bytes) -> str`: Decompress data
- `compress_file(input_path: str, output_path: str) -> Tuple[int, int]`: Compress file
- `decompress_file(input_path: str, output_path: str) -> int`: Decompress file

### archiver.py

- `create_archive(files: List[Path], output: Path) -> Dict`: Create multi-file archive
- `list_archive(archive: Path) -> List[Dict]`: List files in archive
- `preview_file(archive: Path, filename: str) -> str`: Preview file content
- `extract_from_archive(archive: Path, filename: str, output: Path) -> None`: Extract single file
- `extract_all(archive: Path, output_dir: Path) -> List[str]`: Extract all files

## Technical Details

### Binary Format

- **Variable-length encoding (Varint)**: Token positions are encoded efficiently
  - 1 byte: Positions 0-127 (most frequent tokens)
  - 2 bytes: Positions 128-16,383
  - 3 bytes: Positions 16,384-2,097,151
  - 4+ bytes: Even larger dictionaries
  - Uses 7 bits per byte for data, 1 bit for continuation flag
  - **No wasteful null bytes!** Adapts to actual position values

- **Benefits**:
  - Frequent tokens (positions 0-127) use only 1 byte
  - 25-50% smaller encoding for archives with 256+ unique tokens
  - Eliminates the "every other byte is 0x00" problem

- **Character encoding**: UTF-8 throughout

### Limitations

- Best suited for text files with repetitive content
- Small files may increase in size due to dictionary overhead
- Binary files are not supported (use for text only)
- Memory usage scales with file size (entire file loaded into memory)

## Examples

### Example 1: Compress Configuration Files

```python
from pathlib import Path
from archiver import create_archive

# Compress multiple config files (likely have common keywords)
config_files = list(Path('config/').glob('*.conf'))
stats = create_archive(config_files, Path('configs._t_'))
print(f"Saved {stats['original_size'] - stats['compressed_size']:,} bytes")
```

### Example 2: Archive Documentation

```python
from pathlib import Path
from archiver import create_archive, extract_all

# Archive all markdown documentation
docs = list(Path('docs/').glob('*.md'))
create_archive(docs, Path('documentation._t_'))

# Later, extract to different location
extract_all(Path('documentation._t_'), Path('extracted_docs/'))
```

### Example 3: Batch Processing

```python
from pathlib import Path
from compressor import compress_file
import os

# Compress all .txt files in a directory
for txt_file in Path('input/').glob('*.txt'):
    output = Path('compressed') / f"{txt_file.stem}._t_"
    original, compressed = compress_file(str(txt_file), str(output))
    savings = (1 - compressed/original) * 100
    print(f"{txt_file.name}: {savings:+.1f}% size change")
```

## Contributing

Contributions welcome! Areas for enhancement:
- Streaming compression for large files
- Command-line interface (CLI)
- Compression statistics and visualization
- Additional compression options
- Performance optimizations

## License

This project is open source and available under the MIT License.

## Acknowledgments

Built as a demonstration of frequency-based compression techniques and Python GUI development with tkinter.
