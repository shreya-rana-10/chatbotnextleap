import json

from src.config import ROOT, load_config
from src.ingestion.store import verify_collection


def run() -> int:
    import chromadb

    cfg = load_config()
    chunks = [
        json.loads(line)
        for line in (ROOT / cfg["paths"]["chunks"])
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    if not chunks:
        raise ValueError("No chunk artifact exists; run ingestion first")
    client = chromadb.PersistentClient(path=str(ROOT / cfg["paths"]["chroma"]))
    collection = client.get_collection(cfg["vector_db"]["collection"])
    model = (collection.metadata or {}).get("embedding_model")
    if model != cfg["embedding"]["model"]:
        raise RuntimeError(
            f"Embedding model mismatch: ChromaDB={model!r}, config={cfg['embedding']['model']!r}"
        )
    count = verify_collection(collection, [chunk["chunk_id"] for chunk in chunks])
    print(f"ChromaDB verification passed: all {count} chunks are present")
    return count


if __name__ == "__main__":
    run()
