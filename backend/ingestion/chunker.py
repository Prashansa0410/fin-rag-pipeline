from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentChunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        # We use a semantic chunker that respects paragraphs, sentences, and words
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ".", " ", ""]
        )

    def chunk_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes parsed sections and splits them into smaller overlapping chunks suitable for embeddings.
        """
        chunks = []
        for section in sections:
            content = section.get("content", "")
            if not content.strip():
                continue
                
            text_chunks = self.splitter.split_text(content)
            
            for i, text_chunk in enumerate(text_chunks):
                chunk_metadata = section.get("metadata", {}).copy()
                chunk_metadata["chunk_index"] = i
                
                chunks.append({
                    "content": text_chunk,
                    "metadata": chunk_metadata
                })
                
        return chunks

chunker = DocumentChunker()
