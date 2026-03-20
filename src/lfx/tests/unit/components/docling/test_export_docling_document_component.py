import pytest

pytest.importorskip("docling_core")

from lfx.components.docling.export_docling_document import ExportDoclingDocumentComponent


class _DummyDoc:
    def export_to_markdown(self, **_kwargs):
        return "exported markdown"


class TestExportDoclingDocumentComponent:
    def test_export_document_preserves_input_metadata(self, monkeypatch):
        component = ExportDoclingDocumentComponent()
        component.export_format = "Markdown"
        component.image_mode = "placeholder"
        component.md_image_placeholder = "<!-- image -->"
        component.md_page_break_placeholder = ""
        component.doc_key = "doc"

        metadata = {"file_path": "docs/report.pdf", "source": "docling-remote"}
        monkeypatch.setattr(
            "lfx.components.docling.export_docling_document.extract_docling_documents_with_metadata",
            lambda *_args, **_kwargs: ([_DummyDoc()], [metadata], None),
        )

        result = component.export_document()

        assert len(result) == 1
        assert result[0].text == "exported markdown"
        assert result[0].data["file_path"] == "docs/report.pdf"
        assert result[0].data["source"] == "docling-remote"
        assert "doc" not in result[0].data
