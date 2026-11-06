# PRD: Mutual Fund FAQ Assistant (RAG Demo)

| | |
|---|---|
| **Product** | Facts-only Mutual Fund FAQ Assistant |
| **Platform context** | Groww (public pages only) |
| **Type** | Working prototype / RAG demonstration |
| **Status** | Draft v1.0 |
| **Source document** | Problem_Statement.txt |

---

## 1. Overview

Build a small FAQ assistant that answers **factual** questions about selected HDFC Mutual Fund schemes (expense ratio, exit load, minimum SIP, ELSS lock-in, riskometer, benchmark, how to download statements, etc.) using **only official public pages**. Every answer carries exactly one source link. The assistant gives **no investment advice**.

The project is also a **RAG teaching demo**: each pipeline stage (load, chunk, embed, store, retrieve, generate) must persist its output explicitly so it can be shown and inspected.

## 2. Goals and Non-Goals

### Goals
- Answer factual MF queries accurately from a small, fixed corpus.
- Cite one clear source link in every answer.
- Refuse opinion, advice and portfolio questions politely, with a relevant educational link.
- Make every RAG stage observable through stored artifacts.
- Keep models, DB and providers swappable via config / `.env`.

### Non-Goals
- Investment advice, recommendations, buy/sell/hold guidance.
- Computing, comparing or claiming returns/performance.
- Crawling links internal to the five source pages.
- Handling any personal or account data.
- Multi-turn personalisation or portfolio analysis.

## 3. Target Users

| User | Need |
|---|---|
| Retail investors comparing schemes | Quick, trustworthy facts with a verifiable source |
| Support / content teams | Fast answers to repetitive MF questions |

## 4. Scope

### 4.1 AMC and Schemes

| # | Item | URL |
|---|---|---|
| 1 | AMC overview: HDFC Mutual Fund | https://groww.in/mutual-funds/amc/hdfc-mutual-funds |
| 2 | Large Cap: HDFC Large Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |
| 3 | Flexi Cap: HDFC Flexi Cap Direct Plan Growth | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |
| 4 | ELSS: HDFC ELSS Tax Saver Fund Direct Plan Growth | https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth |
| 5 | Mid Cap: HDFC Mid Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth |

**Scraping rule:** scrape only these 5 pages. Do not follow internal links.

### 4.2 Supported Question Types
- Expense ratio of a scheme
- Exit load
- Minimum SIP / minimum lumpsum
- ELSS lock-in period
- Riskometer and benchmark
- How to download statements (e.g., capital-gains statement)

## 5. Functional Requirements

### 5.1 Data Pipeline (phase-wise)

Each phase writes its output to disk so it can be displayed in the demo.

| Phase | Description | Persisted artifact (suggested) |
|---|---|---|
| **1. Data Loading** | Fetch and scrape the 5 pages; extract clean text plus metadata (URL, scheme name, scrape timestamp). | `data/raw/` (HTML) and `data/processed/*.json` (clean text + metadata) |
| **2. Data Chunking** | Split text using a strategy suited to the data (see 5.2). | `data/chunks/chunks.jsonl` |
| **3. Embedding** | Embed chunks with `sentence-transformers/all-MiniLM-L6-v2`. | `data/embeddings/` (vectors + chunk IDs) |
| **4. Vector DB** | Store chunks, vectors and metadata in ChromaDB. | `data/chroma/` persistent store |

### 5.2 Chunking Strategy

The coding agent decides the final strategy based on the page structure. Recommended starting point:
- **Section/field-aware chunking:** group by logical blocks (e.g., Fund Details, Expense Ratio & Exit Load, Minimum Investment, Riskometer/Benchmark, FAQs) rather than fixed windows only.
- Fall back to recursive character splitting with a small overlap for long unstructured text.
- Every chunk carries metadata: `source_url`, `scheme_name`, `section`, `chunk_id`, `scraped_at`.
- Chunk size and overlap are config values.

### 5.3 Retrieval and Generation

| Component | Requirement |
|---|---|
| Embedding model | Same as ingestion (`all-MiniLM-L6-v2`), read from config |
| Vector DB | Same ChromaDB store as ingestion |
| Retrieval | Top-k similarity search, with optional metadata filter by scheme |
| LLM provider (default) | **OpenRouter**, API key from `.env` |
| LLM model | OpenRouter model ID read from `.env` (`LLM_MODEL`) |
| Alternative providers | Groq, Gemini, OpenAI, Anthropic, selectable via config/`.env` without code changes |

Retrieval stage should log the query, retrieved chunks, scores and the final prompt so they can be shown in the demo.

### 5.4 Assistant Behaviour

**Answering (factual queries)**
- Answer is **3 sentences or fewer**.
- Includes **exactly one** citation link (the source page of the supporting chunk).
- Ends with: `Last updated from sources: <date>` (taken from scrape timestamp).
- Uses only retrieved context; if the answer is not in the corpus, say so and link the most relevant source page.

**Refusing (advice / opinion / portfolio)**
- Examples: "Should I buy/sell?", "Which fund is best?", "Is my portfolio good?"
- Respond with a polite, facts-only message plus one relevant educational link (e.g., AMFI / SEBI investor education page).
- No recommendation, even softened.

**Performance questions**
- Do not compute or compare returns.
- Point to the official factsheet link instead.

**PII handling**
- Do not accept or store PAN, Aadhaar, account numbers, OTPs, emails or phone numbers.
- Detect such patterns in input, discard them, and show a short warning. Do not log them.

### 5.5 Query Classification (Thinking Like a Model)

Before retrieval, classify each query:

| Class | Action |
|---|---|
| Factual, in scope | Retrieve, then answer with citation |
| Factual, out of corpus | Say it is not available, cite closest source |
| Advice / opinion / portfolio | Polite refusal + educational link |
| Performance / returns | Refuse to compute, link factsheet |
| Contains PII | Warn, discard, do not process |

Classification can be rule-based, LLM-based, or a hybrid.

### 5.6 UI

A minimal UI (e.g., Streamlit or Gradio) containing:
- A welcome line.
- **3 example questions** (clickable), e.g.:
  1. "What is the expense ratio of HDFC Large Cap Fund?"
  2. "What is the lock-in period for HDFC ELSS Tax Saver Fund?"
  3. "What is the minimum SIP for HDFC Mid Cap Fund?"
- A text input and answer area showing the answer, citation link and last-updated line.
- Persistent note: **"Facts-only. No investment advice."**
- Optional "Show RAG internals" panel for demo (retrieved chunks, scores, prompt).

## 6. Configuration Requirements

All of the following must be changeable without code edits.

**`config.yaml`**
```yaml
sources:
  urls_file: data/sources.csv
chunking:
  strategy: section_aware
  chunk_size: 500
  chunk_overlap: 50
embedding:
  model: sentence-transformers/all-MiniLM-L6-v2
vector_db:
  provider: chroma
  persist_dir: data/chroma
  collection: hdfc_mf_faq
retrieval:
  top_k: 4
llm:
  provider: openrouter  # openrouter | groq | gemini | openai | anthropic
  max_sentences: 3
```

**`.env`**
```
LLM_PROVIDER=openrouter
LLM_MODEL=qwen/qwen3.8-27b
OPENROUTER_API_KEY=
GROQ_API_KEY=
GEMINI_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

## 7. Constraints

| Constraint | Detail |
|---|---|
| Public sources only | No app back-end screenshots, no third-party blogs |
| No PII | Never accept or store PAN, Aadhaar, account numbers, OTPs, emails, phones |
| No performance claims | No return calculations or comparisons; link factsheet |
| Clarity | Answers of 3 sentences or fewer, with "Last updated from sources" |
| Citation | Exactly one source link per answer |

## 8. Proposed Project Structure

```
mf-faq-assistant/
├── PRD.md
├── README.md
├── config.yaml
├── .env.example
├── requirements.txt
├── data/
│   ├── sources.csv
│   ├── raw/
│   ├── processed/
│   ├── chunks/
│   ├── embeddings/
│   └── chroma/
├── src/
│   ├── ingestion/
│   │   ├── load.py
│   │   ├── chunk.py
│   │   ├── embed.py
│   │   └── store.py
│   ├── retrieval/
│   │   ├── retriever.py
│   │   ├── classifier.py
│   │   └── pii_guard.py
│   ├── llm/
│   │   └── client.py        # provider abstraction
│   └── app.py
├── samples/
│   └── sample_qa.md
└── docs/
    └── disclaimer.md
```

## 9. Deliverables

1. **Working prototype** link (app/notebook), or a demo video of 3 minutes or less if hosting is not possible.
2. **Source list** (CSV/MD) of the 15-25 URLs used (see Open Questions).
3. **README** with setup steps, scope (AMC + schemes) and known limits.
4. **Sample Q&A file** with 5-10 queries, the assistant's answers and links.
5. **Disclaimer snippet** used in the UI (facts-only, no advice).

## 10. Skills Demonstrated

| Skill | How it is shown |
|---|---|
| W1: Thinking Like a Model | Identify the exact fact asked; decide answer vs. refuse |
| W2: LLMs and Prompting | Concise instructions, polite safe refusals, citation wording |
| W3: RAG | Small-corpus retrieval with accurate citations |

## 11. Success Criteria / Acceptance Tests

| # | Criterion |
|---|---|
| 1 | All 5 pages are scraped and stored; no internal links are followed |
| 2 | Each pipeline stage produces an inspectable stored artifact |
| 3 | Embedding model, vector DB, chunking and LLM are changeable via config / `.env` |
| 4 | 100% of factual answers have one citation, are 3 sentences or fewer, and include the last-updated line |
| 5 | "Should I buy/sell X?" is refused politely with an educational link |
| 6 | Return/performance questions are not computed; factsheet link is given |
| 7 | PII in input is rejected and never stored or logged |
| 8 | UI shows welcome line, 3 example questions and the facts-only note |
| 9 | Sample Q&A covers at least 5 queries, including at least 1 refusal |

## 12. Risks and Known Limits

| Risk | Mitigation |
|---|---|
| Groww pages may be JS-rendered, making scraping fragile | Use a headless browser fallback; save raw HTML |
| Page data changes over time (expense ratio, exit load) | Show scrape date; allow re-run of the pipeline |
| LLM hallucination | Strict context-only prompt; "not found" fallback |
| Small corpus gives limited coverage | Document limits in README |
| Selected model may not be enabled by the provider | Set `LLM_MODEL` to an available model ID for the selected provider |

## 13. Open Questions

1. **Source count conflict:** the deliverables ask for a list of 15-25 URLs, but the scraping scope is limited to 5 pages. Should the source list include additional official pages (AMFI, SEBI, HDFC AMC factsheets, statement-download help) used for citations and refusal links? If so, they would need to be added to the corpus, which conflicts with the "just these 5 pages" rule.
2. **"Official" sources:** the five pages are on Groww, a distribution platform rather than the AMC or regulator. Confirm this is acceptable for the "official public pages" requirement.
3. **Statement-download questions:** the 5 pages may not contain this answer. Confirm which source to cite (Groww help page, AMC, or CAMS/KFintech).
4. **LLM model name:** set `LLM_MODEL` to an OpenRouter model ID enabled for the account.
5. **UI framework:** Streamlit vs. Gradio vs. notebook.

## 14. Phased Delivery Plan

| Phase | Deliverable |
|---|---|
| 1 | Data loading (scraper + stored raw/processed data) |
| 2 | Chunking with stored chunks and metadata |
| 3 | Embedding with stored vectors |
| 4 | ChromaDB ingestion and verification queries |
| 5 | Retrieval and LLM generation (Groq default, provider-switchable) |
| 6 | Classifier, refusal flow and PII guard |
| 7 | UI, sample Q&A, README, disclaimer, demo |

## 15. Disclaimer (UI snippet)

> **Facts-only. No investment advice.** This assistant shares factual information from public pages and does not recommend, rate or compare investments. Please consult the official scheme documents or a SEBI-registered advisor before investing.
