#!/usr/bin/env python3
"""
TextCompressor CLI - Command-line interface for compression operations.
"""

import argparse
import sys
from pathlib import Path

from compressor import compress_file, decompress_file
from archiver import create_archive, list_archive, extract_all, extract_from_archive, preview_file


def cmd_compress(args):
    """Compress a single file."""
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix('._t_')

    if not input_path.exists():
        print(f"Error: Input file '{input_path}' not found", file=sys.stderr)
        return 1

    try:
        original, compressed = compress_file(str(input_path), str(output_path))
        ratio = compressed / original * 100
        savings = original - compressed

        print(f"Compressed: {input_path} → {output_path}")
        print(f"Original size: {original:,} bytes")
        print(f"Compressed size: {compressed:,} bytes")
        print(f"Compression ratio: {ratio:.1f}%")
        if savings > 0:
            print(f"Space saved: {savings:,} bytes ({100-ratio:.1f}%)")
        else:
            print(f"Size increased: {-savings:,} bytes (file too small or too diverse)")

        return 0

    except Exception as e:
        print(f"Error during compression: {e}", file=sys.stderr)
        return 1


def cmd_decompress(args):
    """Decompress a single file."""
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix('.txt')

    if not input_path.exists():
        print(f"Error: Input file '{input_path}' not found", file=sys.stderr)
        return 1

    try:
        size = decompress_file(str(input_path), str(output_path))
        print(f"Decompressed: {input_path} → {output_path}")
        print(f"Output size: {size:,} bytes")
        return 0

    except Exception as e:
        print(f"Error during decompression: {e}", file=sys.stderr)
        return 1


def cmd_archive(args):
    """Create an archive from files and/or directories."""
    paths = [Path(f) for f in args.paths]
    output_path = Path(args.output)

    # Check all paths exist
    missing = [f for f in paths if not f.exists()]
    if missing:
        print(f"Error: Paths not found: {', '.join(str(f) for f in missing)}", file=sys.stderr)
        return 1

    try:
        stats = create_archive(paths, output_path)
        ratio = stats['ratio'] * 100

        print(f"Archive created: {output_path}")
        print(f"Files archived: {stats['file_count']}")
        print(f"Original size: {stats['original_size']:,} bytes")
        print(f"Archive size: {stats['compressed_size']:,} bytes")
        print(f"Compression ratio: {ratio:.1f}%")

        if ratio < 100:
            savings = stats['original_size'] - stats['compressed_size']
            print(f"Space saved: {savings:,} bytes ({100-ratio:.1f}%)")

        return 0

    except Exception as e:
        print(f"Error creating archive: {e}", file=sys.stderr)
        return 1


def cmd_list(args):
    """List contents of an archive."""
    archive_path = Path(args.archive)

    if not archive_path.exists():
        print(f"Error: Archive '{archive_path}' not found", file=sys.stderr)
        return 1

    try:
        files = list_archive(archive_path)

        print(f"Archive: {archive_path}")
        print(f"Files: {len(files)}\n")

        if args.verbose:
            print(f"{'Filename':<40} {'Tokens':>10} {'Est. Size':>12}")
            print("-" * 65)
            for file_info in files:
                print(f"{file_info['name']:<40} {file_info['token_count']:>10,} "
                      f"{file_info['estimated_size']:>12,}")
        else:
            for file_info in files:
                print(f"  {file_info['name']}")

        return 0

    except Exception as e:
        print(f"Error listing archive: {e}", file=sys.stderr)
        return 1


def cmd_extract(args):
    """Extract files from an archive."""
    archive_path = Path(args.archive)
    output_dir = Path(args.output) if args.output else Path.cwd()

    if not archive_path.exists():
        print(f"Error: Archive '{archive_path}' not found", file=sys.stderr)
        return 1

    try:
        if args.file:
            # Extract single file
            output_path = output_dir / args.file if output_dir.is_dir() else output_dir
            extract_from_archive(archive_path, args.file, output_path)
            print(f"Extracted: {args.file} → {output_path}")
        else:
            # Extract all files
            extracted = extract_all(archive_path, output_dir)
            print(f"Extracted {len(extracted)} files to {output_dir}")
            if args.verbose:
                for filename in extracted:
                    print(f"  {filename}")

        return 0

    except Exception as e:
        print(f"Error extracting from archive: {e}", file=sys.stderr)
        return 1


def cmd_preview(args):
    """Preview a file in an archive."""
    archive_path = Path(args.archive)

    if not archive_path.exists():
        print(f"Error: Archive '{archive_path}' not found", file=sys.stderr)
        return 1

    try:
        content = preview_file(archive_path, args.file)
        print(content)
        return 0

    except Exception as e:
        print(f"Error previewing file: {e}", file=sys.stderr)
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='TextCompressor - Frequency-based text compression utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compress a single file
  %(prog)s compress input.txt -o output._t_

  # Decompress a file
  %(prog)s decompress compressed._t_ -o output.txt

  # Create archive from multiple files
  %(prog)s archive file1.txt file2.txt file3.txt -o archive._t_

  # Create archive from entire directory (preserves structure)
  %(prog)s archive my_project/ -o project.t_

  # List archive contents
  %(prog)s list archive._t_

  # Extract all files from archive
  %(prog)s extract archive._t_ -o output_dir/

  # Extract single file
  %(prog)s extract archive._t_ -f file1.txt -o output.txt

  # Preview file in archive
  %(prog)s preview archive._t_ file1.txt
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    subparsers.required = True

    # Compress command
    compress_parser = subparsers.add_parser('compress', help='Compress a single file')
    compress_parser.add_argument('input', help='Input file to compress')
    compress_parser.add_argument('-o', '--output', help='Output file (default: input._t_)')
    compress_parser.set_defaults(func=cmd_compress)

    # Decompress command
    decompress_parser = subparsers.add_parser('decompress', help='Decompress a file')
    decompress_parser.add_argument('input', help='Compressed file to decompress')
    decompress_parser.add_argument('-o', '--output', help='Output file (default: input.txt)')
    decompress_parser.set_defaults(func=cmd_decompress)

    # Archive command
    archive_parser = subparsers.add_parser('archive', help='Create archive from files and/or directories')
    archive_parser.add_argument('paths', nargs='+', help='Files and/or directories to archive (directories are recursively scanned)')
    archive_parser.add_argument('-o', '--output', required=True, help='Output archive file')
    archive_parser.set_defaults(func=cmd_archive)

    # List command
    list_parser = subparsers.add_parser('list', help='List archive contents')
    list_parser.add_argument('archive', help='Archive file to list')
    list_parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed information')
    list_parser.set_defaults(func=cmd_list)

    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract files from archive')
    extract_parser.add_argument('archive', help='Archive file to extract from')
    extract_parser.add_argument('-o', '--output', help='Output directory or file')
    extract_parser.add_argument('-f', '--file', help='Extract specific file only')
    extract_parser.add_argument('-v', '--verbose', action='store_true', help='Show extracted files')
    extract_parser.set_defaults(func=cmd_extract)

    # Preview command
    preview_parser = subparsers.add_parser('preview', help='Preview file in archive')
    preview_parser.add_argument('archive', help='Archive file')
    preview_parser.add_argument('file', help='File to preview')
    preview_parser.set_defaults(func=cmd_preview)

    # Parse arguments and execute command
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
