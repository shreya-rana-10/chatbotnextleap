from src.config import ROOT, load_config
from src.ingestion import run_all
from src.ingestion.verify_store import run as verify_store


def ensure_corpus_ready() -> None:
    cfg = load_config()
    embeddings = ROOT / cfg["paths"]["embeddings"]
    required_artifacts = (
        ROOT / cfg["paths"]["chunks"],
        embeddings / "embeddings.npy",
        embeddings / "ids.json",
        embeddings / "embedding_meta.json",
    )
    chroma_dir = ROOT / cfg["paths"]["chroma"]
    if all(path.is_file() for path in required_artifacts) and chroma_dir.is_dir():
        verify_store()
        return

    run_all.run()
