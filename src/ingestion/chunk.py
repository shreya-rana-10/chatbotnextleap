import json
import re
from collections import Counter

from src.config import ROOT, load_config


def split_text(text: str, size: int, overlap: int) -> list[str]:
    if size < 1 or overlap < 0 or overlap >= size:
        raise ValueError("chunk_size must be positive and 0 <= chunk_overlap < chunk_size")
    if len(text) <= size:
        return [text]
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            sentence_break = text.rfind(". ", start, end)
            word_break = text.rfind(" ", start, end)
            cut = max(sentence_break, word_break)
            if cut > start + size // 2:
                end = cut + 1
        pieces.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap
    return pieces


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "section"


def build_chunks(documents: list[dict], size: int, overlap: int) -> list[dict]:
    chunks: list[dict] = []
    seen_ids: set[str] = set()
    for document in documents:
        section_counts: dict[str, int] = {}
        for section in document["sections"]:
            title = section["title"]
            section_slug = slugify(title)
            section_counts[section_slug] = section_counts.get(section_slug, 0) + 1
            unique_section = (
                section_slug
                if section_counts[section_slug] == 1
                else f"{section_slug}-{section_counts[section_slug]}"
            )
            prefix = f"{document['scheme_name']} - {title}: "
            for index, piece in enumerate(split_text(section["text"], size, overlap)):
                if len(piece) < 20:
                    continue
                chunk_id = f"{document['doc_id']}::{unique_section}::{index}"
                if chunk_id in seen_ids:
                    raise ValueError(f"Duplicate chunk id generated: {chunk_id}")
                seen_ids.add(chunk_id)
                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "text": prefix + piece,
                        "metadata": {
                            "source_url": document["source_url"],
                            "scheme_name": document["scheme_name"],
                            "section": section_slug,
                            "page_type": document["page_type"],
                            "scraped_at": document["scraped_at"],
                        },
                    }
                )
    return chunks


def run() -> int:
    cfg = load_config()
    input_path = ROOT / cfg["paths"]["loaded"]
    documents = [
        json.loads(line)
        for line in input_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    chunk_cfg = cfg["chunking"]
    chunks = build_chunks(
        documents, chunk_cfg["chunk_size"], chunk_cfg["chunk_overlap"]
    )
    if not chunks:
        raise ValueError("No chunks were generated from the loaded documents")
    output = ROOT / cfg["paths"]["chunks"]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as output_file:
        for chunk in chunks:
            output_file.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    counts = Counter(chunk["chunk_id"].split("::", 1)[0] for chunk in chunks)
    for doc_id, count in sorted(counts.items()):
        print(f"{doc_id}: {count} chunks")
    print(f"Wrote {len(chunks)} unique chunks to {output}")
    return len(chunks)


if __name__ == "__main__":
    run()
