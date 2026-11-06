import json
from datetime import datetime, timezone

import numpy as np

from src.config import ROOT, load_config


def run() -> int:
    from sentence_transformers import SentenceTransformer

    cfg = load_config()
    chunk_path = ROOT / cfg["paths"]["chunks"]
    chunks = [
        json.loads(line)
        for line in chunk_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not chunks:
        raise ValueError("No chunks found; run the chunking stage first")
    model_name = cfg["embedding"]["model"]
    model = SentenceTransformer(model_name)
    vectors = model.encode(
        [chunk["text"] for chunk in chunks],
        batch_size=cfg["embedding"]["batch_size"],
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    vectors = np.asarray(vectors, dtype=np.float32)
    output = ROOT / cfg["paths"]["embeddings"]
    output.mkdir(parents=True, exist_ok=True)
    np.save(output / "embeddings.npy", vectors)
    (output / "ids.json").write_text(
        json.dumps([chunk["chunk_id"] for chunk in chunks], indent=2),
        encoding="utf-8",
    )
    (output / "embedding_meta.json").write_text(
        json.dumps(
            {
                "model": model_name,
                "dimension": int(vectors.shape[1]),
                "count": int(vectors.shape[0]),
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    if vectors.shape[0] != len(chunks):
        raise RuntimeError("Embedding count does not match the input chunk count")
    print(f"Embedded {vectors.shape[0]} chunks, dimension {vectors.shape[1]}")
    return int(vectors.shape[0])


if __name__ == "__main__":
    run()
