import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import struct

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from export_source_text import ExtractionError, process_utf8_v1, docx_to_text_v1

class TestExportSourceText(unittest.TestCase):
    def test_process_utf8_v1_valid(self):
        content = "Hello world\nLine 2\n".encode("utf-8")
        extracted = process_utf8_v1(content)
        self.assertEqual(extracted, "Hello world\nLine 2\n")

    def test_process_utf8_v1_bom(self):
        content = b"\xef\xbb\xbfHello world"
        extracted = process_utf8_v1(content)
        self.assertEqual(extracted, "Hello world\n")

    def test_process_utf8_v1_invalid(self):
        content = b"\xff\xfeH\x00e\x00l\x00l\x00o\x00"  # UTF-16 LE
        with self.assertRaisesRegex(ExtractionError, "Invalid UTF-8"):
            process_utf8_v1(content)

    def test_docx_to_text_v1_valid(self):
        # We need a minimal valid ZIP file that contains word/document.xml
        import io
        import zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("word/document.xml", b"<?xml version=\"1.0\"?><w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\"><w:body><w:p><w:r><w:t>Hello DOCX</w:t></w:r></w:p></w:body></w:document>")
        extracted = docx_to_text_v1(buf.getvalue())
        self.assertEqual(extracted, "Hello DOCX\n")

    def test_docx_to_text_v1_missing_document_xml(self):
        import io
        import zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("word/other.xml", b"<xml/>")
        with self.assertRaisesRegex(ExtractionError, "word/document.xml not found"):
            docx_to_text_v1(buf.getvalue())

    def test_docx_to_text_v1_too_large(self):
        import io
        import zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # Create a 5MB payload
            zf.writestr("word/document.xml", b"A" * (101 * 1024 * 1024))
        with self.assertRaisesRegex(ExtractionError, "exceeds"):
            docx_to_text_v1(buf.getvalue())

if __name__ == '__main__':
    unittest.main()
