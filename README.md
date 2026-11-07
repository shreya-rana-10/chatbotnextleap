# HDFC Mutual Fund FAQ (RAG demo)

This prototype builds a traceable retrieval pipeline over exactly five public Groww HDFC Mutual Fund pages. It never follows links found on those pages. Answers are facts-only, limited to three sentences, and cite the source URL selected from retrieved metadata.

## Setup

1. Install Python 3.10+ and run `python -m venv .venv`.
2. Activate the environment and install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env`, add your `OPENROUTER_API_KEY`, and set `LLM_MODEL` to an OpenRouter model ID enabled for your account.
4. For JavaScript-rendered page fallback, install Playwright's browser once with `playwright install chromium`.
5. To start locally, run `python -m src.ingestion.run_all` once (the first app question also builds the corpus automatically if artifacts are missing).
6. Confirm vector completeness: `python -m src.ingestion.verify_store`.
7. Check retrieval hits: `python -m scripts.smoke_test`.
8. Start the FAQ: `streamlit run src/app.py`.

OpenRouter is the default LLM provider and uses its OpenAI-compatible API. Set `LLM_PROVIDER` and the matching API key to switch to `groq`, `gemini`, `openai`, or `anthropic`. Select models using the provider's model IDs. API keys belong only in the ignored local `.env`, never in `.env.example` or source control.

## Phase artifacts

| Stage | Command/module | Persisted output |
|---|---|---|
| 1. Directory and configuration | `config.yaml`, `src/config.py` | Project layout and settings |
| 2. Scraping | `python -m src.ingestion.scrape` | `data/raw/` and `data/scraped/`; selected scheme facts are extracted from the same page payload |
| 3. Loading/validation | `python -m src.ingestion.load_docs` | `data/loaded/documents.jsonl` |
| 4. Chunking | `python -m src.ingestion.chunk` | `data/chunks/chunks.jsonl` |
| 5. Embedding | `python -m src.ingestion.embed` | `data/embeddings/` |
| 6. ChromaDB storage | `python -m src.ingestion.store` | `data/chroma/` |
| 7. Retrieval and FAQ UI | `streamlit run src/app.py` | Query traces in `logs/queries.jsonl` |

`verify_store` checks the collection count and exact chunk IDs against the chunk artifact. It exits with an error if any IDs are missing or extra, or if the collection's embedding model differs from config.

## Privacy and scope

- The source list is fixed in `data/sources.csv`; the scraper has no link-crawling logic and rejects redirects.
- Questions that match common PII formats are discarded before retrieval and are not logged.
- Do not enter PAN, Aadhaar, OTP, account, phone, or email details.
- Advice and performance questions are refused. Out-of-scope questions receive an educational link.
- Ingestion data, local vector DB, `.env`, and query logs are excluded from version control.
- The prototype depends on source-page availability and extraction structure; review the saved JSON before treating any answer as authoritative.

Run tests with `pytest`.

## Deployment

The current UI is Streamlit and the local retrieval store is persistent ChromaDB. This app is not directly deployable to Vercel's serverless runtime. See [docs/deployment.md](./docs/deployment.md) for the Vercel frontend/backend split, required environment settings, and a deployment option for the current Streamlit app.

On Streamlit Community Cloud, the first question automatically scrapes the five approved public pages and builds the local embedding and ChromaDB artifacts if they are missing. The first request can take several minutes. Add `LLM_PROVIDER`, `LLM_MODEL`, and `OPENROUTER_API_KEY` under the app's Streamlit Secrets settings.
