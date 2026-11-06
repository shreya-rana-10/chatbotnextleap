from pathlib import Path
from typing import Any

from src.config import ROOT, load_config

ALIASES = {
    "tax saver": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
    "elss": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
    "large cap": "HDFC Large Cap Fund Direct Growth",
    "flexi cap": "HDFC Flexi Cap Direct Plan Growth",
    "mid cap": "HDFC Mid Cap Fund Direct Growth",
}
FACT_SECTIONS = {
    "expense ratio": "expense-ratio",
    "expense ratios": "expense-ratio",
    "exit load": "exit-load",
    "minimum sip": "minimum-sip",
    "min sip": "minimum-sip",
    "minimum investment": "minimum-investment",
    "minimum amount": "minimum-investment",
    "minimum lump sum": "minimum-investment",
    "minimum lumpsum": "minimum-investment",
    "lock-in": "lock-in-period",
    "lock in": "lock-in-period",
    "riskometer": "riskometer",
    "benchmark": "benchmark",
}


class Retriever:
    def __init__(
        self,
        cfg: dict[str, Any] | None = None,
        model: Any = None,
        collection: Any = None,
    ) -> None:
        self.cfg = cfg or load_config()
        if model is None:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(self.cfg["embedding"]["model"])
        self.model = model
        if collection is None:
            import chromadb

            client = chromadb.PersistentClient(
                path=str(ROOT / self.cfg["paths"]["chroma"])
            )
            collection = client.get_collection(self.cfg["vector_db"]["collection"])
        self.collection = collection
        built_with = (self.collection.metadata or {}).get("embedding_model")
        if built_with != self.cfg["embedding"]["model"]:
            raise RuntimeError(
                "Embedding model mismatch. Re-run ingestion with the configured model."
            )

    @staticmethod
    def detect_scheme(query: str) -> str | None:
        normalized = query.casefold()
        return next(
            (scheme for alias, scheme in ALIASES.items() if alias in normalized),
            None,
        )

    @staticmethod
    def detect_fact_sections(query: str) -> list[str]:
        normalized = query.casefold()
        return list(
            dict.fromkeys(
                section
                for phrase, section in FACT_SECTIONS.items()
                if phrase in normalized
            )
        )

    def retrieve(self, query: str) -> list[dict[str, Any]]:
        retrieval_cfg = self.cfg["retrieval"]
        query_vector = self.model.encode([query], normalize_embeddings=True).tolist()
        scheme = self.detect_scheme(query)
        conditions = []
        if scheme:
            conditions.append({"scheme_name": scheme})
        fact_sections = self.detect_fact_sections(query)
        if fact_sections:
            section_filter = (
                fact_sections[0]
                if len(fact_sections) == 1
                else {"$in": fact_sections}
            )
            conditions.append({"section": section_filter})
        filters = (
            conditions[0]
            if len(conditions) == 1
            else {"$and": conditions}
            if conditions
            else None
        )
        result = self.collection.query(
            query_embeddings=query_vector,
            n_results=retrieval_cfg["top_k"],
            where=filters,
            include=["documents", "metadatas", "distances"],
        )
        documents = result["documents"][0] or []
        metadata = result["metadatas"][0] or []
        distances = result["distances"][0] or []
        hits: list[dict[str, Any]] = []
        for document, details, distance in zip(documents, metadata, distances):
            score = 1 - float(distance)
            if score >= retrieval_cfg["min_score"]:
                hits.append(
                    {"text": document, "metadata": details, "score": round(score, 3)}
                )
        return hits
