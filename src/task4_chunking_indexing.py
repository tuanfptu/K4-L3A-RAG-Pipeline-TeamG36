"""
Task 4 — Chunking, embedding và indexing.

Hướng dẫn:
    1. Đọc toàn bộ Markdown/JSON/JSONL trong data/standardized/.
    2. Chia văn bản bằng strategy đã chọn (structure_aware).
    3. Embed chunks bằng một provider duy nhất.
    4. Upsert vào ChromaDB với cosine distance.
"""

import json
import os
import re
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "structure_aware"

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "gemini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
EMBEDDING_DIM = 3072 if "gemini" in EMBEDDING_PROVIDER else 1024

COLLECTION_NAME = "rag_documents"


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed danh sách text bằng provider được cấu hình trong .env (Gemini hoặc SentenceTransformer)."""
    if not texts:
        return []

    provider = os.getenv("EMBEDDING_PROVIDER", "gemini").lower()
    if provider == "gemini":
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required in .env")

        client = genai.Client(api_key=api_key)
        model_name = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")

        # Chia nhỏ thành các batch 50 items để không vượt quá giới hạn API
        batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "50"))
        request_interval = float(os.getenv("EMBEDDING_REQUEST_INTERVAL_SECONDS", "4.2"))
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            last_error = None
            for attempt in range(3):
                try:
                    response = client.models.embed_content(
                        model=model_name,
                        contents=batch,
                    )
                    time.sleep(request_interval)
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt == 2:
                        raise RuntimeError(
                            f"Embedding batch {i // batch_size + 1} failed after 3 attempts"
                        ) from exc
                    delay = max(request_interval, 2**attempt)
                    if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                        delay = max(delay, 60 * (attempt + 1))
                    print(f"[RETRY] embedding batch in {delay:.1f}s: {exc}")
                    time.sleep(delay)
            all_embeddings.extend([e.values for e in response.embeddings])
        return all_embeddings
    else:
        from sentence_transformers import SentenceTransformer

        if not hasattr(embed_texts, "_model"):
            embed_texts._model = SentenceTransformer(EMBEDDING_MODEL)

        return embed_texts._model.encode(texts).tolist()


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def extract_url(content: str) -> str | None:
    """Trích xuất URL nguồn từ header Markdown nếu có."""
    match = re.search(r"(?:\*\*Source:\*\*|Source:|URL:)\s*(https?://[^\s\)]+)", content, re.IGNORECASE)
    return match.group(1).strip() if match else None


def load_documents() -> list[dict]:
    """Đọc dữ liệu chuẩn hóa (JSONL, JSON, Markdown) và trả về danh sách Document."""
    documents = []
    legal_dir = STANDARDIZED_DIR / "legal"
    news_dir = STANDARDIZED_DIR / "news"

    legal_files = list(legal_dir.glob("*.jsonl")) if legal_dir.exists() else []
    news_files = list(news_dir.glob("*.json")) if news_dir.exists() else []

    # Đọc cấu trúc pháp luật chi tiết nếu có
    for path in sorted(legal_files):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            x = json.loads(line)
            m = {
                "source": x.get("issuer") or x.get("document_title") or x.get("file_name") or path.name,
                "title": x.get("document_title") or x.get("source_id") or path.stem,
                "doc_type": "legal",
                "url": x.get("source_url"),
                "source_id": x.get("source_id"),
                "document_number": x.get("document_number"),
                "issued_date": x.get("issued_date"),
                "effective_date": x.get("effective_date"),
                "page_start": x.get("page_start"),
                "page_end": x.get("page_end"),
                "chapter_number": x.get("chapter_number"),
                "section_number": x.get("section_number"),
                "article_number": x.get("article_number"),
                "clause_number": x.get("clause_number"),
                "point_number": x.get("point_number"),
                "legal_path": x.get("legal_path") or "",
                "issuer": x.get("issuer"),
                "trust_level": "official",
                "structured_record_id": x.get("id"),
                "file_name": x.get("file_name"),
                "file_sha256": x.get("file_sha256"),
            }
            documents.append({
                "id": x["id"],
                "content": x.get("normalized_text") or x.get("content", ""),
                "metadata": m,
            })

    # Đọc tin tức JSON có metadata đầy đủ nếu có
    for path in sorted(news_files):
        x = json.loads(path.read_text(encoding="utf-8"))
        m = {
            "source": x.get("publisher") or path.name,
            "title": x.get("title") or path.stem,
            "doc_type": "news",
            "url": x.get("canonical_url") or x.get("url"),
            "source_id": x.get("source_id") or path.stem,
            "publisher": x.get("publisher"),
            "published_date": x.get("published_date"),
            "source_type": x.get("source_type"),
            "trust_level": x.get("trust_level"),
            "content_sha256": x.get("content_sha256"),
        }
        documents.append({
            "id": x.get("source_id") or path.stem,
            "content": x.get("content") or x.get("content_markdown", ""),
            "metadata": m,
        })

    # Đọc các file .md chuẩn nếu chưa được đọc qua jsonl/json
    canonical = {p.stem for p in legal_files + news_files}
    if STANDARDIZED_DIR.exists():
        for path in STANDARDIZED_DIR.rglob("*.md"):
            if path.stem in canonical:
                continue
            doc_type = "legal" if "legal" in path.parts else "news"
            content = path.read_text(encoding="utf-8")
            url = extract_url(content)
            documents.append({
                "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
                "content": content,
                "metadata": {
                    "source": path.name,
                    "title": path.stem,
                    "doc_type": doc_type,
                    "url": url,
                },
            })

    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks theo cấu trúc pháp luật (Điều, Chương, Khoản)."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=[
            "\n### Điều ",
            "\n## Điều ",
            "\n# Điều ",
            "\nĐiều ",
            "\nChương ",
            "\n\n",
            "\n",
            ";\n",
            ". ",
            " ",
            "",
        ],
    )

    chunks = []
    for document in documents:
        for index, text in enumerate(splitter.split_text(document["content"])):
            chunks.append({
                "id": f"{document['id']}::chunk-{index}",
                "content": text,
                "metadata": {**document["metadata"], "chunk_index": index},
            })

    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    if not chunks:
        return []
    vectors = embed_texts([chunk["content"] for chunk in chunks])
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector
    return chunks


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB."""
    if not chunks:
        return
    collection = get_collection()
    # Loại bỏ giá trị None trong metadata vì ChromaDB có thể reject None
    clean_metadatas = [
        {k: v for k, v in chunk["metadata"].items() if v is not None}
        for chunk in chunks
    ]
    collection.upsert(
        ids=[chunk["id"] for chunk in chunks],
        documents=[chunk["content"] for chunk in chunks],
        embeddings=[chunk["embedding"] for chunk in chunks],
        metadatas=clean_metadatas,
    )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    chunks = chunk_documents(documents)
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks")


if __name__ == "__main__":
    run_pipeline()
