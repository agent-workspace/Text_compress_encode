"""
Comprehensive test suite for TextCompressor.

Tests tokenization, compression, decompression, and archive operations.
"""

import unittest
from pathlib import Path
import shutil
import tempfile

from compressor import tokenize, build_frequency_dict, encode, decode, compress_file, decompress_file
from archiver import create_archive, list_archive, preview_file, extract_from_archive, extract_all


class TestTokenization(unittest.TestCase):
    """Test tokenization accuracy."""

    def test_simple_words(self):
        """Test basic word tokenization."""
        text = "Hello world"
        tokens = tokenize(text)
        # Should tokenize as words with trailing space where applicable
        self.assertIn("Hello ", tokens)
        self.assertIn("world", tokens)

    def test_words_with_spaces(self):
        """Test words with various whitespace."""
        text = "word1 word2  word3   word4"
        tokens = tokenize(text)
        reconstructed = ''.join(tokens)
        self.assertEqual(text, reconstructed)

    def test_line_endings_crlf(self):
        """Test CRLF line endings are preserved."""
        text = "Line1\r\nLine2\r\nLine3"
        tokens = tokenize(text)
        reconstructed = ''.join(tokens)
        self.assertEqual(text, reconstructed)
        self.assertIn("\r\n", tokens)

    def test_line_endings_lf(self):
        """Test LF line endings are preserved."""
        text = "Line1\nLine2\nLine3"
        tokens = tokenize(text)
        reconstructed = ''.join(tokens)
        self.assertEqual(text, reconstructed)
        self.assertIn("\n", tokens)

    def test_punctuation_sequences(self):
        """Test punctuation grouping."""
        text = "Hello!!! World??? Test..."
        tokens = tokenize(text)
        reconstructed = ''.join(tokens)
        self.assertEqual(text, reconstructed)
        self.assertIn("!!!", tokens)
        self.assertIn("???", tokens)
        self.assertIn("...", tokens)

    def test_mixed_content(self):
        """Test mixed content with code-like text."""
        text = "def func():\n\treturn 42"
        tokens = tokenize(text)
        reconstructed = ''.join(tokens)
        self.assertEqual(text, reconstructed)

    def test_multiple_spaces(self):
        """Test multiple spaces are preserved."""
        text = "word1     word2"
        tokens = tokenize(text)
        reconstructed = ''.join(tokens)
        self.assertEqual(text, reconstructed)

    def test_tabs(self):
        """Test tabs are preserved."""
        text = "word1\t\tword2"
        tokens = tokenize(text)
        reconstructed = ''.join(tokens)
        self.assertEqual(text, reconstructed)

    def test_empty_string(self):
        """Test empty string."""
        text = ""
        tokens = tokenize(text)
        self.assertEqual(tokens, [])

    def test_unicode_characters(self):
        """Test Unicode characters."""
        text = "Hello 世界! Привет мир!"
        tokens = tokenize(text)
        reconstructed = ''.join(tokens)
        self.assertEqual(text, reconstructed)


class TestCompression(unittest.TestCase):
    """Test compression and decompression."""

    def test_lossless_simple(self):
        """Test lossless compression on simple text."""
        text = "Hello world! Hello world! Hello world!"
        compressed = encode(text)
        decompressed = decode(compressed)
        self.assertEqual(text, decompressed)

    def test_lossless_multiline(self):
        """Test lossless compression with multiple lines."""
        text = "Line 1\nLine 2\nLine 3\nLine 1\nLine 2"
        compressed = encode(text)
        decompressed = decode(compressed)
        self.assertEqual(text, decompressed)

    def test_lossless_crlf(self):
        """Test CRLF preservation."""
        text = "Line 1\r\nLine 2\r\nLine 3"
        compressed = encode(text)
        decompressed = decode(compressed)
        self.assertEqual(text, decompressed)

    def test_lossless_whitespace(self):
        """Test whitespace preservation."""
        text = "word1   word2\t\tword3     word4"
        compressed = encode(text)
        decompressed = decode(compressed)
        self.assertEqual(text, decompressed)

    def test_lossless_punctuation(self):
        """Test punctuation preservation."""
        text = "Hello!!! World??? Test... More—text—here."
        compressed = encode(text)
        decompressed = decode(compressed)
        self.assertEqual(text, decompressed)

    def test_lossless_unicode(self):
        """Test Unicode preservation."""
        text = "Hello 世界! Café résumé naïve. Привет мир!"
        compressed = encode(text)
        decompressed = decode(compressed)
        self.assertEqual(text, decompressed)

    def test_compression_ratio(self):
        """Test that repeated text compresses well."""
        # Highly repetitive text should compress well
        text = "test " * 100
        compressed = encode(text)
        original_size = len(text.encode('utf-8'))
        compressed_size = len(compressed)

        # Should achieve some compression
        self.assertLess(compressed_size, original_size)

    def test_empty_text(self):
        """Test empty text compression."""
        text = ""
        compressed = encode(text)
        decompressed = decode(compressed)
        self.assertEqual(text, decompressed)

    def test_single_character(self):
        """Test single character."""
        text = "a"
        compressed = encode(text)
        decompressed = decode(compressed)
        self.assertEqual(text, decompressed)

    def test_file_compression(self):
        """Test file-based compression."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            test_text = "Hello world! " * 50
            f.write(test_text)
            input_file = f.name

        output_file = input_file + '.compressed'

        try:
            # Compress
            original_size, compressed_size = compress_file(input_file, output_file)
            self.assertGreater(original_size, 0)
            self.assertGreater(compressed_size, 0)

            # Decompress
            decompressed_file = input_file + '.decompressed'
            decompressed_size = decompress_file(output_file, decompressed_file)

            # Verify
            with open(input_file, 'r', encoding='utf-8') as f:
                original = f.read()
            with open(decompressed_file, 'r', encoding='utf-8') as f:
                decompressed = f.read()

            self.assertEqual(original, decompressed)

        finally:
            # Cleanup
            Path(input_file).unlink(missing_ok=True)
            Path(output_file).unlink(missing_ok=True)
            Path(decompressed_file).unlink(missing_ok=True)


class TestArchive(unittest.TestCase):
    """Test archive operations."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_single_file_archive(self):
        """Test archive with single file."""
        # Create test file
        file1 = self.test_dir / "file1.txt"
        text1 = "Hello world! This is file 1.\nHello world again!"
        file1.write_text(text1, encoding='utf-8')

        # Create archive
        archive_path = self.test_dir / "test.t"
        stats = create_archive([file1], archive_path)

        self.assertEqual(stats['file_count'], 1)
        self.assertGreater(stats['original_size'], 0)
        self.assertGreater(stats['compressed_size'], 0)

        # List archive
        files = list_archive(archive_path)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]['name'], 'file1.txt')

        # Preview
        content = preview_file(archive_path, 'file1.txt')
        self.assertEqual(content, text1)

        # Extract
        extract_dir = self.test_dir / "extracted"
        extracted = extract_all(archive_path, extract_dir)
        self.assertEqual(len(extracted), 1)

        # Verify extracted content
        extracted_file = extract_dir / "file1.txt"
        self.assertTrue(extracted_file.exists())
        extracted_text = extracted_file.read_text(encoding='utf-8')
        self.assertEqual(extracted_text, text1)

    def test_multiple_file_archive(self):
        """Test archive with multiple files."""
        # Create test files
        file1 = self.test_dir / "file1.txt"
        text1 = "Hello world! This is file 1."
        file1.write_text(text1, encoding='utf-8')

        file2 = self.test_dir / "file2.txt"
        text2 = "This is file 2. Hello world!"
        file2.write_text(text2, encoding='utf-8')

        file3 = self.test_dir / "file3.txt"
        text3 = "File 3 content here. Different text."
        file3.write_text(text3, encoding='utf-8')

        # Create archive
        archive_path = self.test_dir / "multi.t"
        stats = create_archive([file1, file2, file3], archive_path)

        self.assertEqual(stats['file_count'], 3)

        # List archive
        files = list_archive(archive_path)
        self.assertEqual(len(files), 3)

        # Extract all
        extract_dir = self.test_dir / "extracted"
        extracted = extract_all(archive_path, extract_dir)
        self.assertEqual(len(extracted), 3)

        # Verify all files
        self.assertEqual((extract_dir / "file1.txt").read_text(encoding='utf-8'), text1)
        self.assertEqual((extract_dir / "file2.txt").read_text(encoding='utf-8'), text2)
        self.assertEqual((extract_dir / "file3.txt").read_text(encoding='utf-8'), text3)

    def test_extract_single_file(self):
        """Test extracting single file from archive."""
        # Create test files
        file1 = self.test_dir / "file1.txt"
        text1 = "Content 1"
        file1.write_text(text1, encoding='utf-8')

        file2 = self.test_dir / "file2.txt"
        text2 = "Content 2"
        file2.write_text(text2, encoding='utf-8')

        # Create archive
        archive_path = self.test_dir / "test.t"
        create_archive([file1, file2], archive_path)

        # Extract only file2
        output_path = self.test_dir / "extracted_file2.txt"
        extract_from_archive(archive_path, 'file2.txt', output_path)

        # Verify
        self.assertTrue(output_path.exists())
        self.assertEqual(output_path.read_text(encoding='utf-8'), text2)

    def test_shared_dictionary_compression(self):
        """Test that shared dictionary improves compression."""
        # Create files with overlapping content
        file1 = self.test_dir / "file1.txt"
        text1 = "The quick brown fox jumps over the lazy dog. " * 10
        file1.write_text(text1, encoding='utf-8')

        file2 = self.test_dir / "file2.txt"
        text2 = "The lazy dog sleeps under the quick brown fox. " * 10
        file2.write_text(text2, encoding='utf-8')

        # Create archive
        archive_path = self.test_dir / "shared.t"
        stats = create_archive([file1, file2], archive_path)

        # Shared dictionary should provide good compression
        self.assertLess(stats['ratio'], 0.5)  # Should compress to less than 50%


class TestRealFiles(unittest.TestCase):
    """Test with actual test data files."""

    def setUp(self):
        """Set up test environment."""
        self.test_data_dir = Path(__file__).parent / 'test_data'
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_simple_file(self):
        """Test test_simple.txt."""
        if not self.test_data_dir.exists():
            self.skipTest("Test data directory not found")

        test_file = self.test_data_dir / 'test_simple.txt'
        if not test_file.exists():
            self.skipTest(f"{test_file} not found")

        original_text = test_file.read_text(encoding='utf-8')
        compressed = encode(original_text)
        decompressed = decode(compressed)

        self.assertEqual(original_text, decompressed)
        print(f"\ntest_simple.txt: {len(original_text)} → {len(compressed)} bytes "
              f"({len(compressed)/len(original_text)*100:.1f}%)")

    def test_code_file(self):
        """Test test_code.py."""
        if not self.test_data_dir.exists():
            self.skipTest("Test data directory not found")

        test_file = self.test_data_dir / 'test_code.py'
        if not test_file.exists():
            self.skipTest(f"{test_file} not found")

        original_text = test_file.read_text(encoding='utf-8')
        compressed = encode(original_text)
        decompressed = decode(compressed)

        self.assertEqual(original_text, decompressed)
        print(f"\ntest_code.py: {len(original_text)} → {len(compressed)} bytes "
              f"({len(compressed)/len(original_text)*100:.1f}%)")

    def test_edge_cases_file(self):
        """Test test_edge_cases.txt."""
        if not self.test_data_dir.exists():
            self.skipTest("Test data directory not found")

        test_file = self.test_data_dir / 'test_edge_cases.txt'
        if not test_file.exists():
            self.skipTest(f"{test_file} not found")

        original_text = test_file.read_text(encoding='utf-8')
        compressed = encode(original_text)
        decompressed = decode(compressed)

        self.assertEqual(original_text, decompressed)
        print(f"\ntest_edge_cases.txt: {len(original_text)} → {len(compressed)} bytes "
              f"({len(compressed)/len(original_text)*100:.1f}%)")

    def test_unicode_file(self):
        """Test test_unicode.txt."""
        if not self.test_data_dir.exists():
            self.skipTest("Test data directory not found")

        test_file = self.test_data_dir / 'test_unicode.txt'
        if not test_file.exists():
            self.skipTest(f"{test_file} not found")

        original_text = test_file.read_text(encoding='utf-8')
        compressed = encode(original_text)
        decompressed = decode(compressed)

        self.assertEqual(original_text, decompressed)
        print(f"\ntest_unicode.txt: {len(original_text)} → {len(compressed)} bytes "
              f"({len(compressed)/len(original_text)*100:.1f}%)")

    def test_all_files_archive(self):
        """Test creating archive from all test files."""
        if not self.test_data_dir.exists():
            self.skipTest("Test data directory not found")

        # Find all .txt files in test_data
        test_files = list(self.test_data_dir.glob('*.txt'))
        if not test_files:
            self.skipTest("No test files found")

        # Create archive
        archive_path = self.temp_dir / 'all_tests.t'
        stats = create_archive(test_files, archive_path)

        print(f"\nArchive stats:")
        print(f"  Files: {stats['file_count']}")
        print(f"  Original: {stats['original_size']:,} bytes")
        print(f"  Compressed: {stats['compressed_size']:,} bytes")
        print(f"  Ratio: {stats['ratio']*100:.1f}%")

        # Extract and verify
        extract_dir = self.temp_dir / 'extracted'
        extracted = extract_all(archive_path, extract_dir)
        self.assertEqual(len(extracted), len(test_files))

        # Verify each file
        for test_file in test_files:
            original = test_file.read_text(encoding='utf-8')
            extracted_file = extract_dir / test_file.name
            extracted_content = extracted_file.read_text(encoding='utf-8')
            self.assertEqual(original, extracted_content)


def run_tests():
    """Run all tests with verbose output."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestTokenization))
    suite.addTests(loader.loadTestsFromTestCase(TestCompression))
    suite.addTests(loader.loadTestsFromTestCase(TestArchive))
    suite.addTests(loader.loadTestsFromTestCase(TestRealFiles))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n✓ ALL TESTS PASSED!")
    else:
        print("\n✗ SOME TESTS FAILED")

    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
