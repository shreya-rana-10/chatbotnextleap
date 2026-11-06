import json

import numpy as np

from src.config import ROOT, load_config


def verify_collection(collection, expected_ids: list[str]) -> int:
    count = collection.count()
    if count != len(expected_ids):
        raise RuntimeError(
            f"ChromaDB contains {count} chunks; expected {len(expected_ids)}"
        )
    stored_ids = set(collection.get(include=[])["ids"])
    missing = set(expected_ids) - stored_ids
    extra = stored_ids - set(expected_ids)
    if missing or extra:
        raise RuntimeError(
            f"ChromaDB chunk IDs do not match. Missing: {len(missing)}, extra: {len(extra)}"
        )
    return count


def run() -> int:
    import chromadb
    from chromadb.errors import NotFoundError

    cfg = load_config()
    chunk_path = ROOT / cfg["paths"]["chunks"]
    chunks = [
        json.loads(line)
        for line in chunk_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not chunks:
        raise ValueError("No chunks found; run the chunking stage first")
    embedding_dir = ROOT / cfg["paths"]["embeddings"]
    vectors = np.load(embedding_dir / "embeddings.npy")
    ids = json.loads((embedding_dir / "ids.json").read_text(encoding="utf-8"))
    chunk_ids = [chunk["chunk_id"] for chunk in chunks]
    if vectors.ndim != 2 or vectors.shape[0] != len(chunks) or ids != chunk_ids:
        raise ValueError("Embedding vectors/IDs do not align with the current chunks")
    client = chromadb.PersistentClient(path=str(ROOT / cfg["paths"]["chroma"]))
    name = cfg["vector_db"]["collection"]
    try:
        client.get_collection(name=name)
    except NotFoundError:
        pass
    else:
        client.delete_collection(name=name)
    collection = client.create_collection(
        name=name,
        metadata={
            "hnsw:space": "cosine",
            "embedding_model": cfg["embedding"]["model"],
            "expected_chunk_count": len(chunks),
        },
    )
    batch_size = 100
    for offset in range(0, len(chunks), batch_size):
        batch = chunks[offset : offset + batch_size]
        batch_vectors = vectors[offset : offset + batch_size].tolist()
        collection.add(
            ids=[chunk["chunk_id"] for chunk in batch],
            embeddings=batch_vectors,
            documents=[chunk["text"] for chunk in batch],
            metadatas=[chunk["metadata"] for chunk in batch],
        )
    count = verify_collection(collection, chunk_ids)
    print(
        f"Verified ChromaDB collection '{name}': "
        f"{count}/{len(chunks)} chunks present"
    )
    return count


if __name__ == "__main__":
    run()
