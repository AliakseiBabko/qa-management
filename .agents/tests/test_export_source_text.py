import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import struct

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from export_source_text import (
    ExtractionError, process_utf8_v1, docx_to_text_v1,
    source_text_requirement, SOURCE_TEXT_TYPES,
)


class TestSourceTextRequirement(unittest.TestCase):
    """source_text_requirement() decides whether a queue row's source must
    have a v1 text blob exported. Covers the existing M1/M2 behavior
    (unchanged) and the Project Knowledge lane types added after the
    20260721 PKF run found project_knowledge_transcript was falling
    through to 'optional' instead of 'required'."""

    def test_m1_m2_types_still_required_for_file_backed_sources(self):
        for src_type in ("qa_1to1", "strategy_chat", "meeting_transcript", "people_case_chat"):
            for ext in (".txt", ".md", ".docx"):
                row = {"Source type": src_type, "Source": f"00_Inbox/example{ext}"}
                self.assertEqual(source_text_requirement(row), "required",
                                 f"{src_type} + {ext} should still be required")

    def test_m1_m2_conversational_types_still_not_applicable(self):
        for src_type in ("admin_note", "m2_conversation"):
            row = {"Source type": src_type, "Source": "00_Inbox/example.txt"}
            self.assertEqual(source_text_requirement(row), "not_applicable")

    def test_project_knowledge_types_required_for_file_backed_sources(self):
        for src_type in ("project_knowledge_transcript", "project_knowledge_document",
                         "project_knowledge_chat", "project_knowledge_notes"):
            for ext in (".txt", ".md", ".docx"):
                row = {"Source type": src_type, "Source": f"00_Inbox/PKF/example{ext}"}
                self.assertEqual(source_text_requirement(row), "required",
                                 f"{src_type} + {ext} should be required")

    def test_project_knowledge_notes_optional_when_not_file_backed(self):
        # project_knowledge_notes with no recognized file extension (e.g. an
        # empty/blank Source, or an unsupported extension) must not be
        # forced to "required" - only file-backed sources with a supported
        # extension are required, same rule as every other type here.
        row = {"Source type": "project_knowledge_notes", "Source": ""}
        self.assertEqual(source_text_requirement(row), "optional")
        row_unsupported_ext = {"Source type": "project_knowledge_notes", "Source": "00_Inbox/PKF/example.pdf"}
        self.assertEqual(source_text_requirement(row_unsupported_ext), "optional")

    def test_project_knowledge_types_optional_for_unsupported_extension(self):
        for src_type in ("project_knowledge_transcript", "project_knowledge_document",
                         "project_knowledge_chat"):
            row = {"Source type": src_type, "Source": "00_Inbox/PKF/example.pdf"}
            self.assertEqual(source_text_requirement(row), "optional")

    def test_unknown_type_still_optional(self):
        row = {"Source type": "raw_transcript", "Source": "00_Inbox/example.txt"}
        self.assertEqual(source_text_requirement(row), "optional")

    def test_source_text_types_set_includes_project_knowledge(self):
        for src_type in ("project_knowledge_transcript", "project_knowledge_document",
                         "project_knowledge_chat", "project_knowledge_notes"):
            self.assertIn(src_type, SOURCE_TEXT_TYPES)
        # M1/M2 types must still be present - this is an addition, not a replacement.
        for src_type in ("qa_1to1", "strategy_chat", "meeting_transcript", "people_case_chat"):
            self.assertIn(src_type, SOURCE_TEXT_TYPES)


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
        with self.assertRaisesRegex(ExtractionError, "word/document.xml missing"):
            docx_to_text_v1(buf.getvalue())

    def test_docx_to_text_v1_too_large(self):
        import io
        import zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # Create a 5MB payload
            zf.writestr("word/document.xml", b"A" * (101 * 1024 * 1024))
        with self.assertRaisesRegex(ExtractionError, "Suspicious compression ratio"):
            docx_to_text_v1(buf.getvalue())

if __name__ == '__main__':
    unittest.main()
