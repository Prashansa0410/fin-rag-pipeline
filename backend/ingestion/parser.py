from typing import List, Dict, Any
import os

class DocumentParser:
    def __init__(self):
        pass

    def parse_document(self, file_path: str, mime_type: str) -> List[Dict[str, Any]]:
        """
        Parses a document into raw sections or pages.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at {file_path}")
            
        if mime_type == "application/pdf":
            return self._parse_pdf(file_path)
        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return self._parse_docx(file_path)
        elif mime_type == "text/plain":
            return self._parse_txt(file_path)
        else:
            raise ValueError(f"Unsupported mime type: {mime_type}")

    def _parse_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        sections = []
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text.strip():
                    sections.append({
                        "content": text,
                        "metadata": {
                            "page_number": i + 1,
                            "section": f"Page {i + 1}"
                        }
                    })
        return sections

    def _parse_docx(self, file_path: str) -> List[Dict[str, Any]]:
        sections = []
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
            
        sections.append({
            "content": "\n".join(full_text),
            "metadata": {
                "page_number": 1,
                "section": "Document Body"
            }
        })
        return sections

    def _parse_txt(self, file_path: str) -> List[Dict[str, Any]]:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
            
        return [{
            "content": text,
            "metadata": {
                "page_number": 1,
                "section": "Document Body"
            }
        }]

parser = DocumentParser()
