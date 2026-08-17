import os
import sys
import glob
import uuid
from sqlalchemy.orm import Session
from backend.database.session import SessionLocal, Base, engine
from backend.database.models import Organization, Document, DocumentVersion, DocumentChunk, DocumentStatus
from backend.ingestion.parser import parser
from backend.ingestion.chunker import chunker
from backend.embeddings.provider import embedding_provider
import datetime

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def parse_metadata_from_path(file_path: str):
    # Extracts basic metadata from directory structure for the synthetic data
    parts = file_path.split("/")
    filename = os.path.basename(file_path)
    
    partner = None
    if "partner_a" in filename.lower():
        partner = "Partner A"
    elif "partner_b" in filename.lower():
        partner = "Partner B"
        
    domain = None
    if "compliance" in file_path.lower() or "regulatory" in file_path.lower():
        domain = "Compliance"
    elif "payment" in file_path.lower():
        domain = "Payments"
    elif "settlement" in file_path.lower():
        domain = "Settlement"
    elif "incident" in file_path.lower():
        domain = "Operations"
        
    version = 1
    if "v2" in filename.lower():
        version = 2
        
    return {
        "filename": filename,
        "partner": partner,
        "domain": domain,
        "version": version
    }

def main():
    db: Session = next(get_db())
    
    # Ensure an organization exists
    org = db.query(Organization).first()
    if not org:
        org = Organization(name="FinResearch Inc")
        db.add(org)
        db.commit()
        db.refresh(org)

    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))
    
    files = []
    for root, _, filenames in os.walk(data_dir):
        if "evaluation" in root:
            continue
        for fn in filenames:
            if fn.endswith(".md"):
                files.append(os.path.join(root, fn))
                
    print(f"Found {len(files)} files to ingest.")
    
    for file_path in files:
        meta = parse_metadata_from_path(file_path)
        
        # Check if document already exists
        doc = db.query(Document).filter(
            Document.filename == meta["filename"],
            Document.organization_id == org.id
        ).first()
        
        if not doc:
            doc = Document(
                organization_id=org.id,
                filename=meta["filename"],
                document_type="Markdown",
                partner=meta["partner"],
                business_domain=meta["domain"],
                status=DocumentStatus.READY
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            
        # Check version
        doc_version = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == doc.id,
            DocumentVersion.version == meta["version"]
        ).first()
        
        if doc_version:
            print(f"Skipping {meta['filename']} v{meta['version']} - already ingested.")
            continue
            
        print(f"Ingesting {meta['filename']} (v{meta['version']})...")
        
        doc_version = DocumentVersion(
            document_id=doc.id,
            version=meta["version"],
            file_path=file_path,
            mime_type="text/markdown",
            is_current_version=True
        )
        db.add(doc_version)
        db.commit()
        db.refresh(doc_version)
        
        # Parse and Chunk
        sections = parser.parse_document(file_path, "text/plain")
        chunks = chunker.chunk_sections(sections)
        
        for c in chunks:
            text = c["content"]
            embedding = embedding_provider.embed_text(text)
            
            # Simple metadata attachment
            combined_meta = c.get("metadata", {})
            combined_meta.update(meta)
            combined_meta["source_id"] = meta["filename"] # Crucial for evaluation mapping
            
            db_chunk = DocumentChunk(
                version_id=doc_version.id,
                content=text,
                embedding=embedding,
                chunk_metadata=combined_meta
            )
            db.add(db_chunk)
            
        db.commit()
        print(f"  -> Generated {len(chunks)} chunks.")

    print("Ingestion complete.")

if __name__ == "__main__":
    main()
