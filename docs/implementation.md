# Implementation Plan: Mutual Fund FAQ Assistant (RAG Demo)

| | |
|---|---|
| **Derived from** | PRD.md and architecture.md |
| **Status** | Draft v1.0 |

Each phase lists its goal, tasks, files, code skeleton, commands and an exit check. Do not start a phase until the previous phase's exit check passes. Every ingestion phase writes its output to disk so it can be shown in the demo.

## Phase Overview

| Phase | Name | Output |
|---|---|---|
| 0 | Project setup and config | Skeleton, `config.yaml`, `.env.example` |
| 1 | Data loading | `data/raw/`, `data/processed/` |
| 2 | Data chunking | `data/chunks/chunks.jsonl` |
| 3 | Data embedding | `data/embeddings/` |
| 4 | Vector DB (ChromaDB) | `data/chroma/` |
| 5 | Retrieval | Retriever module and smoke test |
| 6 | LLM client and prompting | Provider-switchable generation |
| 7 | Guards, classifier, refusals, formatter | Safe, correctly shaped answers |
| 8 | Pipeline and UI | Working prototype |
| 9 | Testing and deliverables | Sample Q&A, README, source list, demo |

---

## Phase 0: Project Setup and Config

**Goal:** a runnable skeleton where all swappable settings come from config.

### Tasks
1. Create the folder structure from architecture.md section 9.
2. Create a virtual environment and `requirements.txt`.
3. Write `config.yaml`, `.env.example` and `src/config.py`.
4. Add `.gitignore` (`.env`, `data/chroma/`, `logs/`, `__pycache__/`).
5. Create `data/sources.csv` with the 5 URLs.

### `requirements.txt`
```
requests
beautifulsoup4
lxml
playwright
sentence-transformers
chromadb
numpy
pyyaml
python-dotenv
groq
google-generativeai
openai
anthropic
streamlit
pytest
```

### `data/sources.csv`
```
doc_id,scheme_name,page_type,url
hdfc-mutual-funds,HDFC Mutual Fund,amc,https://groww.in/mutual-funds/amc/hdfc-mutual-funds
hdfc-large-cap-fund-direct-growth,HDFC Large Cap Fund Direct Growth,scheme,https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
hdfc-equity-fund-direct-growth,HDFC Flexi Cap Direct Plan Growth,scheme,https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
hdfc-elss-tax-saver-fund-direct-plan-growth,HDFC ELSS Tax Saver Fund Direct Plan Growth,scheme,https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
hdfc-mid-cap-fund-direct-growth,HDFC Mid Cap Fund Direct Growth,scheme,https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
```

### `config.yaml`
```yaml
paths:
  sources: data/sources.csv
  raw: data/raw
  processed: data/processed
  chunks: data/chunks/chunks.jsonl
  embeddings: data/embeddings
  chroma: data/chroma
  logs: logs/queries.jsonl
chunking:
  strategy: section_aware      # section_aware | recursive
  chunk_size: 500              # characters
  chunk_overlap: 50
embedding:
  model: sentence-transformers/all-MiniLM-L6-v2
  batch_size: 32
vector_db:
  provider: chroma
  collection: hdfc_mf_faq
retrieval:
  top_k: 4
  min_score: 0.30
llm:
  provider: openrouter         # openrouter | groq | gemini | openai | anthropic
  max_sentences: 3
  temperature: 0.0
  timeout_seconds: 30
links:
  educational: https://www.amfiindia.com/investor-corner
  factsheet_fallback: https://groww.in/mutual-funds/amc/hdfc-mutual-funds
```

### `.env.example`
```
LLM_PROVIDER=openrouter
LLM_MODEL=qwen/qwen3.8-27b
OPENROUTER_API_KEY=
GROQ_API_KEY=
GEMINI_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

### `src/config.py`
```python
import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

def load_config(path: str = "config.yaml") -> dict:
    with open(ROOT / path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["llm"]["provider"] = os.getenv("LLM_PROVIDER", cfg["llm"]["provider"])
    cfg["llm"]["model"] = os.getenv("LLM_MODEL", "qwen/qwen3.8-27b")
    return cfg

def get_api_key(provider: str) -> str:
    key = os.getenv(f"{provider.upper()}_API_KEY", "")
    if not key:
        raise RuntimeError(f"Missing {provider.upper()}_API_KEY in .env")
    return key
```

### Exit check
`python -c "from src.config import load_config; print(load_config())"` prints the config with the model from `.env`.

---

## Phase 1: Data Loading

**Goal:** fetch exactly the 5 pages and store raw HTML plus clean, sectioned JSON.

**Files:** `src/ingestion/load.py`

### Tasks
1. Read `sources.csv`.
2. Fetch each URL with `requests` (browser-like User-Agent, timeout, 2 retries).
3. If the extracted text is very short (page is JS-rendered), fall back to Playwright headless Chromium.
4. Save raw HTML to `data/raw/<doc_id>.html`.
5. Parse with BeautifulSoup: remove `script`, `style`, `nav`, `footer`, `header`; keep headings and their following content as sections.
6. Save `data/processed/<doc_id>.json` using the schema in architecture.md section 4.1.
7. **Never follow links** found on the page.

### Skeleton
```python
import csv, json, time
from datetime import datetime, timezone
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from src.config import load_config, ROOT

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MFFAQBot/1.0)"}
MIN_TEXT_LEN = 1500

def fetch_html(url: str) -> str:
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r.text
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}")

def fetch_html_browser(url: str) -> str:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        page.goto(url, wait_until="networkidle")
        html = page.content()
        b.close()
        return html

def extract_sections(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    sections, current = [], {"title": "Overview", "text": []}
    for el in soup.find_all(["h1", "h2", "h3", "p", "li", "td", "th", "div"]):
        if el.name in ("h1", "h2", "h3"):
            if current["text"]:
                sections.append({"title": current["title"], "text": " ".join(current["text"])})
            current = {"title": el.get_text(" ", strip=True), "text": []}
        elif el.name != "div":
            t = el.get_text(" ", strip=True)
            if t:
                current["text"].append(t)
    if current["text"]:
        sections.append({"title": current["title"], "text": " ".join(current["text"])})
    return sections

def run():
    cfg = load_config()
    raw_dir, proc_dir = ROOT / cfg["paths"]["raw"], ROOT / cfg["paths"]["processed"]
    raw_dir.mkdir(parents=True, exist_ok=True); proc_dir.mkdir(parents=True, exist_ok=True)
    with open(ROOT / cfg["paths"]["sources"], newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            html = fetch_html(row["url"])
            sections = extract_sections(html)
            if sum(len(s["text"]) for s in sections) < MIN_TEXT_LEN:
                html = fetch_html_browser(row["url"])
                sections = extract_sections(html)
            (raw_dir / f"{row['doc_id']}.html").write_text(html, encoding="utf-8")
            record = {
                "doc_id": row["doc_id"], "scheme_name": row["scheme_name"],
                "source_url": row["url"], "page_type": row["page_type"],
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "sections": sections,
            }
            (proc_dir / f"{row['doc_id']}.json").write_text(
                json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Loaded {row['doc_id']}: {len(sections)} sections")

if __name__ == "__main__":
    run()
```

### Commands
```
playwright install chromium
python -m src.ingestion.load
```

### Exit check
- 5 files in `data/raw/` and 5 in `data/processed/`.
- Open each JSON and confirm the key facts (expense ratio, exit load, minimum SIP, riskometer, benchmark) appear in the text. If a fact is missing, adjust extraction selectors before moving on.

---

## Phase 2: Data Chunking

**Goal:** turn sectioned documents into self-contained, metadata-rich chunks.

**Files:** `src/ingestion/chunk.py`

### Strategy
1. **Section-aware first:** each section becomes one chunk if it is within `chunk_size`.
2. **Recursive split** for oversized sections, using separators `". "`, `"; "`, `" "` with `chunk_overlap`.
3. **Context prefix:** every chunk text starts with `"<scheme_name> - <section title>: "` so short chunks still carry the scheme identity.
4. Drop chunks under about 20 characters.
5. Optional: add **fact chunks** for key fields (expense ratio, exit load, minimum SIP, lock-in, riskometer, benchmark) if a regex finds them, written as short statements. These improve retrieval for the supported question types.

### Skeleton
```python
import json
from src.config import load_config, ROOT

def split_text(text: str, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text]
    parts, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = max(text.rfind(". ", start, end), text.rfind(" ", start, end))
            if cut > start + size // 2:
                end = cut + 1
        parts.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap
    return parts

def slugify(s: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in s).strip("-")

def run():
    cfg = load_config()
    size, overlap = cfg["chunking"]["chunk_size"], cfg["chunking"]["chunk_overlap"]
    out = ROOT / cfg["paths"]["chunks"]
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(out, "w", encoding="utf-8") as f:
        for p in sorted((ROOT / cfg["paths"]["processed"]).glob("*.json")):
            doc = json.loads(p.read_text(encoding="utf-8"))
            for sec in doc["sections"]:
                prefix = f"{doc['scheme_name']} - {sec['title']}: "
                for i, piece in enumerate(split_text(sec["text"], size, overlap)):
                    if len(piece) < 20:
                        continue
                    chunk = {
                        "chunk_id": f"{doc['doc_id']}::{slugify(sec['title'])}::{i}",
                        "text": prefix + piece,
                        "metadata": {
                            "source_url": doc["source_url"],
                            "scheme_name": doc["scheme_name"],
                            "section": slugify(sec["title"]),
                            "page_type": doc["page_type"],
                            "scraped_at": doc["scraped_at"],
                        },
                    }
                    f.write(json.dumps(chunk, ensure_ascii=False) + "\n"); n += 1
    print(f"Wrote {n} chunks to {out}")

if __name__ == "__main__":
    run()
```

### Exit check
- `chunks.jsonl` exists; each line has `chunk_id`, `text`, full metadata.
- `chunk_id` values are unique.
- Print chunk counts per document and confirm every scheme has chunks covering expense ratio, exit load, SIP and riskometer.

---

## Phase 3: Data Embedding

**Goal:** embed every chunk with the configured model and store the vectors on disk.

**Files:** `src/ingestion/embed.py`

### Tasks
1. Read `chunks.jsonl`.
2. Load the model named in `config["embedding"]["model"]`.
3. Encode in batches with `normalize_embeddings=True`.
4. Save `embeddings.npy`, `ids.json` and `embedding_meta.json` (model name, dimension, count, timestamp).

### Skeleton
```python
import json
from datetime import datetime, timezone
import numpy as np
from sentence_transformers import SentenceTransformer
from src.config import load_config, ROOT

def run():
    cfg = load_config()
    chunks = [json.loads(l) for l in open(ROOT / cfg["paths"]["chunks"], encoding="utf-8")]
    model = SentenceTransformer(cfg["embedding"]["model"])
    vecs = model.encode([c["text"] for c in chunks],
                        batch_size=cfg["embedding"]["batch_size"],
                        normalize_embeddings=True, show_progress_bar=True)
    out = ROOT / cfg["paths"]["embeddings"]; out.mkdir(parents=True, exist_ok=True)
    np.save(out / "embeddings.npy", vecs)
    (out / "ids.json").write_text(json.dumps([c["chunk_id"] for c in chunks]))
    (out / "embedding_meta.json").write_text(json.dumps({
        "model": cfg["embedding"]["model"], "dimension": int(vecs.shape[1]),
        "count": int(vecs.shape[0]),
        "created_at": datetime.now(timezone.utc).isoformat()}, indent=2))
    print(f"Embedded {vecs.shape[0]} chunks, dim {vecs.shape[1]}")

if __name__ == "__main__":
    run()
```

### Exit check
Shape is `(N, 384)` where N equals the chunk count; `embedding_meta.json` records the model name.

---

## Phase 4: Vector DB (ChromaDB)

**Goal:** load chunks, vectors and metadata into a persistent ChromaDB collection.

**Files:** `src/ingestion/store.py`, `src/ingestion/run_all.py`

### Tasks
1. Create a `PersistentClient` at `paths.chroma`.
2. Delete and recreate the collection (idempotent re-runs) with cosine distance.
3. Add records in batches: id, embedding, document text, metadata.
4. Write the embedding model name into the collection metadata (used by the startup consistency check).
5. Run a smoke test with 3 sample queries.

### Skeleton
```python
import json
import numpy as np
import chromadb
from src.config import load_config, ROOT

def run():
    cfg = load_config()
    chunks = [json.loads(l) for l in open(ROOT / cfg["paths"]["chunks"], encoding="utf-8")]
    emb_dir = ROOT / cfg["paths"]["embeddings"]
    vecs = np.load(emb_dir / "embeddings.npy")
    client = chromadb.PersistentClient(path=str(ROOT / cfg["paths"]["chroma"]))
    name = cfg["vector_db"]["collection"]
    try:
        client.delete_collection(name)
    except Exception:
        pass
    col = client.create_collection(
        name, metadata={"hnsw:space": "cosine",
                        "embedding_model": cfg["embedding"]["model"]})
    B = 100
    for i in range(0, len(chunks), B):
        part = chunks[i:i + B]
        col.add(ids=[c["chunk_id"] for c in part],
                embeddings=vecs[i:i + B].tolist(),
                documents=[c["text"] for c in part],
                metadatas=[c["metadata"] for c in part])
    print(f"Stored {col.count()} chunks in '{name}'")

if __name__ == "__main__":
    run()
```

### `run_all.py`
```python
from src.ingestion import load, chunk, embed, store

if __name__ == "__main__":
    load.run(); chunk.run(); embed.run(); store.run()
```

### Smoke test (`scripts/smoke_test.py`)
Query "ELSS lock-in period", "exit load of mid cap fund" and "minimum SIP" using the retriever from Phase 5 and print the top 3 hits with scores.

### Exit check
Collection count equals the chunk count; smoke queries return the expected sections.

---

## Phase 5: Retrieval

**Goal:** retrieve the best chunks for a query using the same model and DB as ingestion.

**Files:** `src/retrieval/retriever.py`

### Tasks
1. Load the embedding model and Chroma collection from config.
2. **Startup consistency check:** compare `collection.metadata["embedding_model"]` with the config; raise if different.
3. Detect a scheme from the query with an alias map (for example "elss" or "tax saver" maps to the ELSS doc, "large cap", "flexi cap", "mid cap"); use it as a metadata filter when found.
4. Query top-k, convert cosine distance to similarity (`1 - distance`), and drop hits below `min_score`.
5. Return a list of `{text, metadata, score}`.

### Skeleton
```python
import chromadb
from sentence_transformers import SentenceTransformer
from src.config import load_config, ROOT

ALIASES = {
    "elss": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
    "tax saver": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
    "large cap": "HDFC Large Cap Fund Direct Growth",
    "flexi cap": "HDFC Flexi Cap Direct Plan Growth",
    "mid cap": "HDFC Mid Cap Fund Direct Growth",
}

class Retriever:
    def __init__(self, cfg=None):
        self.cfg = cfg or load_config()
        self.model = SentenceTransformer(self.cfg["embedding"]["model"])
        client = chromadb.PersistentClient(path=str(ROOT / self.cfg["paths"]["chroma"]))
        self.col = client.get_collection(self.cfg["vector_db"]["collection"])
        built_with = (self.col.metadata or {}).get("embedding_model")
        if built_with != self.cfg["embedding"]["model"]:
            raise RuntimeError("Embedding model mismatch. Re-run ingestion.")

    def detect_scheme(self, q: str):
        ql = q.lower()
        for k, v in ALIASES.items():
            if k in ql:
                return v
        return None

    def retrieve(self, query: str) -> list[dict]:
        r_cfg = self.cfg["retrieval"]
        qv = self.model.encode([query], normalize_embeddings=True).tolist()
        scheme = self.detect_scheme(query)
        where = {"scheme_name": scheme} if scheme else None
        res = self.col.query(query_embeddings=qv, n_results=r_cfg["top_k"], where=where)
        hits = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            score = 1 - dist
            if score >= r_cfg["min_score"]:
                hits.append({"text": doc, "metadata": meta, "score": round(score, 3)})
        return hits
```

### Exit check
For each question type (expense ratio, exit load, minimum SIP, lock-in, riskometer, benchmark) across the schemes, the correct chunk appears in the top 4. Record results in a small table for the demo.

---

## Phase 6: LLM Client and Prompting

**Goal:** a provider-switchable client and a strict, short-answer prompt.

**Files:** `src/llm/client.py`, `src/prompts.py`

### Tasks
1. Define an abstract `LLMClient.generate(system, user) -> str`.
2. Use OpenRouter by default through its OpenAI-compatible endpoint; support Groq, Gemini, OpenAI and Anthropic with the same interface.
3. `get_client(cfg)` picks the provider from `LLM_PROVIDER` / `llm.provider` and reads the model from `LLM_MODEL`.
4. Validate the API key at startup (`get_api_key`).
5. Retry once on timeout or API error.
6. Strip any reasoning tags such as `<think>...</think>` from outputs.

### Skeleton
```python
# base.py
from abc import ABC, abstractmethod
class LLMClient(ABC):
    @abstractmethod
    def generate(self, system: str, user: str) -> str: ...

# groq_client.py
import re
from groq import Groq
from src.config import get_api_key
from .base import LLMClient

class GroqClient(LLMClient):
    def __init__(self, model: str, temperature=0.0, timeout=30):
        self.client = Groq(api_key=get_api_key("groq"), timeout=timeout)
        self.model, self.temperature = model, temperature

    def generate(self, system, user):
        r = self.client.chat.completions.create(
            model=self.model, temperature=self.temperature,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}])
        text = r.choices[0].message.content or ""
        return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()

# factory.py
def get_client(cfg):
    p, model = cfg["llm"]["provider"], cfg["llm"]["model"]
    if p == "openrouter":
        from openai import OpenAI
        return OpenAI(api_key=get_api_key("openrouter"),
                      base_url="https://openrouter.ai/api/v1")
    if p == "groq":
        from .groq_client import GroqClient; return GroqClient(model, cfg["llm"]["temperature"], cfg["llm"]["timeout_seconds"])
    if p == "gemini":
        from .gemini_client import GeminiClient; return GeminiClient(model)
    if p == "openai":
        from .openai_client import OpenAIClient; return OpenAIClient(model)
    if p == "anthropic":
        from .anthropic_client import AnthropicClient; return AnthropicClient(model)
    raise ValueError(f"Unknown provider: {p}")
```

### `src/prompts.py`
```python
SYSTEM_PROMPT = """You are a facts-only assistant for HDFC Mutual Fund schemes.
Rules:
1. Answer ONLY from the CONTEXT. If the answer is not there, say you could not find it in the sources.
2. Maximum 3 sentences. Be direct and plain.
3. Never give advice, recommendations, or opinions. Never calculate or compare returns.
4. Do not include any URLs or links in your answer.
5. State figures exactly as written in the context."""

def build_user_prompt(question: str, hits: list[dict]) -> str:
    ctx = "\n\n".join(f"[{i+1}] {h['text']}" for i, h in enumerate(hits))
    return f"CONTEXT:\n{ctx}\n\nQUESTION: {question}\n\nANSWER:"
```

### Exit check
With a hand-built context and a mocked provider, the formatter returns a 3-sentence-or-shorter answer with no model-supplied URL. Set `LLM_PROVIDER=openrouter`, a valid `LLM_MODEL`, and `OPENROUTER_API_KEY` to use OpenRouter. Switching the provider changes the API client without code edits.

---

## Phase 7: Guards, Classifier, Refusals and Formatter

**Goal:** enforce the PRD's safety and format rules.

**Files:** `src/retrieval/pii_guard.py`, `src/retrieval/classifier.py`, `src/refusals.py`, `src/formatter.py`

### 7.1 PII Guard
```python
import re
PATTERNS = {
    "pan": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.I),
    "aadhaar": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "phone": re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)"),
    "otp": re.compile(r"\botp\b\D{0,10}\d{4,8}", re.I),
    "account": re.compile(r"\b(?:a/?c|account)\D{0,15}\d{9,18}\b", re.I),
}

def contains_pii(text: str) -> bool:
    return any(p.search(text) for p in PATTERNS.values())
```
On a match, return the PII message and stop. Do not log the text.

### 7.2 Classifier
```python
ADVICE = ["should i", "buy", "sell", "invest in", "best fund", "which fund", "recommend",
          "better than", "good fund", "worth it", "my portfolio", "switch", "redeem now"]
PERFORMANCE = ["return", "returns", "cagr", "performance", "performed", "profit",
               "xirr", "outperform", "compare"]

def classify(q: str) -> str:
    ql = q.lower()
    if any(k in ql for k in PERFORMANCE): return "performance"
    if any(k in ql for k in ADVICE): return "advice"
    return "factual"
```
Optional: for ambiguous queries, add a one-shot LLM classification with a labels-only output.

### 7.3 Refusals (`src/refusals.py`)
| Type | Message | Link |
|---|---|---|
| advice | "I can only share facts about these schemes, not advice on buying or selling. For learning about investing, see the link below." | `links.educational` |
| performance | "I don't calculate or compare returns. The official factsheet has performance details." | scheme page URL if a scheme is detected, else `links.factsheet_fallback` |
| pii | "Please don't share personal or account details. I've ignored that message." | none |
| not found | "I couldn't find that in my sources." | closest source or fallback |

### 7.4 Formatter (`src/formatter.py`)
```python
import re
from datetime import datetime

def clip_sentences(text: str, n: int) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(parts[:n])

def strip_urls(text: str) -> str:
    return re.sub(r"https?://\S+", "", text).strip()

def format_answer(answer: str, url: str, scraped_at: str, max_sentences: int = 3) -> str:
    body = clip_sentences(strip_urls(answer), max_sentences)
    date = datetime.fromisoformat(scraped_at).strftime("%d %b %Y")
    return f"{body}\n\nSource: {url}\nLast updated from sources: {date}"
```
The URL and date come from the top hit's metadata, never from the LLM.

### Exit check
Unit tests: PII samples are caught; "Should I buy HDFC Mid Cap?" is `advice`; "1 year returns of Large Cap" is `performance`; formatter output has at most 3 sentences, exactly one URL and the last-updated line.

---

## Phase 8: Pipeline and UI

**Goal:** wire everything into one query flow and a minimal UI.

**Files:** `src/pipeline.py`, `src/app.py`

**Design source:** adapt `docs/stitch_groww_inspired_fintech_ui.zip` (`DESIGN.md`, `screen.png`, `code.html`) for its mint-and-white palette, Inter type, mobile chat layout, suggestion buttons, and rounded cards. Do not reproduce the portfolio/returns/advice content in the mock; the product remains facts-only and every factual answer cites its source.

### 8.1 Pipeline
```python
import json, time
from src.config import load_config, ROOT
from src.retrieval.pii_guard import contains_pii
from src.retrieval.classifier import classify
from src.retrieval.retriever import Retriever
from src.llm.factory import get_client
from src.prompts import SYSTEM_PROMPT, build_user_prompt
from src.formatter import format_answer
from src import refusals

class Assistant:
    def __init__(self):
        self.cfg = load_config()
        self.retriever = Retriever(self.cfg)
        self.llm = get_client(self.cfg)

    def ask(self, question: str) -> dict:
        trace = {"ts": time.time()}
        if contains_pii(question):
            return {"answer": refusals.pii(), "trace": {**trace, "class": "pii"}}
        label = classify(question); trace["class"] = label
        if label == "advice":
            return {"answer": refusals.advice(self.cfg), "trace": trace}
        scheme_url = self._scheme_url(question)
        if label == "performance":
            return {"answer": refusals.performance(self.cfg, scheme_url), "trace": trace}
        hits = self.retriever.retrieve(question); trace["hits"] = hits
        if not hits:
            return {"answer": refusals.not_found(self.cfg), "trace": trace}
        prompt = build_user_prompt(question, hits); trace["prompt"] = prompt
        try:
            raw = self.llm.generate(SYSTEM_PROMPT, prompt)
        except Exception:
            return {"answer": refusals.llm_error(hits[0]["metadata"]["source_url"]), "trace": trace}
        top = hits[0]["metadata"]
        answer = format_answer(raw, top["source_url"], top["scraped_at"],
                               self.cfg["llm"]["max_sentences"])
        self._log(question, trace)
        return {"answer": answer, "trace": trace}
```
`_log` writes only the sanitized question, class and chunk IDs to `logs/queries.jsonl`.

### 8.2 UI (`src/app.py`, Streamlit)
Elements:
1. A mobile-first header, welcome card and title: "Clear facts. Cited sources."
2. Three example buttons:
   - "What is the expense ratio of HDFC Large Cap Fund?"
   - "What is the lock-in period for HDFC ELSS Tax Saver Fund?"
   - "What is the minimum SIP for HDFC Mid Cap Fund?"
3. Streamlit chat input, conversational answer cards and a clear public-source citation.
4. Persistent note: **"Facts-only. No investment advice."**
5. Expander "RAG internals": query class, retrieved chunks with scores, and final prompt.
6. Never retain or display a PII-containing user message; the PII guard runs before the query is logged.

Use `st.cache_resource` to create `Assistant` once.

### Command
```
streamlit run src/app.py
```

### Exit check
All 3 example questions return correct, cited, 3-sentence-or-shorter answers; an advice question is refused with a link; a PII string is rejected.

### 8.3 Stitch design implementation

Use the checked-in `docs/stitch_groww_inspired_fintech_ui.zip` as the visual source: Inter typography, white/slate surfaces, mint accent, rounded chat cards, suggestion chips, and comfortable mobile spacing. The shipped Streamlit UI uses a welcome card, the three supported example questions, conversational messages, linked citations, and an expandable RAG trace. Do not copy portfolio charts, returns, buy/sell actions, or advice from the sample screen.

---

## Phase 9: Testing and Deliverables

### 9.1 Tests (`tests/`)
| File | Covers |
|---|---|
| `test_ingestion.py` | 5 docs loaded, unique chunk IDs, metadata complete |
| `test_retrieval.py` | Correct chunk in top-k for each fact type and scheme |
| `test_guards.py` | PII patterns, classifier labels |
| `test_formatter.py` | Sentence limit, single URL, last-updated line |
| `test_pipeline.py` | End-to-end with a stubbed LLM client |

Run with `pytest -q`.

### 9.2 Deliverables checklist
| Deliverable | File / action |
|---|---|
| Working prototype | Streamlit app, or a 3-minute demo video |
| Source list | `data/sources.csv` plus `sources.md` (the 15-25 URL requirement is an open question in the PRD) |
| README | Setup steps, scope (AMC + 4 schemes), known limits |
| Sample Q&A | `samples/sample_qa.md` with 5-10 queries and answers with links, including at least one refusal |
| Disclaimer | `docs/disclaimer.md`, and the same text in the UI |

### 9.3 Hosting

The current Streamlit application and local persistent ChromaDB store are not directly deployable on Vercel. Use a Streamlit-compatible host for this version. A Vercel deployment requires a Vercel-supported frontend, a separately hosted Python API, and a managed persistent vector database. Follow `docs/deployment.md`; keep `OPENROUTER_API_KEY` on the backend only.

### Suggested sample queries
1. Expense ratio of HDFC Large Cap Fund Direct Growth?
2. Exit load of HDFC Flexi Cap?
3. ELSS lock-in period?
4. Minimum SIP for HDFC Mid Cap?
5. Riskometer and benchmark of HDFC Large Cap?
6. How to download a capital-gains statement? (may be "not found" until an extra source is approved)
7. Should I buy HDFC Mid Cap Fund? (refusal)
8. What were the 3-year returns of the ELSS fund? (refusal, factsheet link)

### README outline
1. What it is and the scope.
2. Setup: Python version, `pip install -r requirements.txt`, `playwright install chromium`, copy `.env.example` to `.env`.
3. Run ingestion (per phase or `run_all`) and where each artifact is stored.
4. Run the app.
5. How to switch the embedding model, chunking strategy, vector DB settings or LLM provider.
6. Known limits.

---

## Execution Order Summary

```
python -m src.ingestion.load       # Phase 1
python -m src.ingestion.chunk      # Phase 2
python -m src.ingestion.embed      # Phase 3
python -m src.ingestion.store      # Phase 4
python scripts/smoke_test.py       # Phase 4/5 check
pytest -q                          # Phase 9
streamlit run src/app.py           # Phase 8
```

## Risks to Watch During Build

| Risk | When it shows | Response |
|---|---|---|
| JS-rendered pages return thin text | Phase 1 | Playwright fallback; inspect saved HTML |
| Key facts missing from extracted text | Phase 1 exit check | Tune selectors before chunking |
| Facts split across chunks | Phase 5 | Add fact chunks; raise `top_k` |
| Qwen model name rejected by Groq | Phase 6 | Check Groq's model list and update `LLM_MODEL` |
| Qwen output includes reasoning text | Phase 6 | Strip `<think>` blocks; set temperature to 0 |
| Answers exceed 3 sentences | Phase 7 | Formatter clips; tighten the prompt |
