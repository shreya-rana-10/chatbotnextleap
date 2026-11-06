# Deployment

## Run the current Streamlit app

The current app is a long-running Streamlit process backed by a persistent local ChromaDB collection and a locally loaded sentence-transformer model. Deploy it to a Streamlit-compatible host (for example Streamlit Community Cloud or Render), not directly as a Vercel project.

On the Streamlit-compatible host:

1. Import the GitHub repository and select the app entry point `src/app.py`.
2. Use Python 3.12 and install `requirements.txt`.
3. Ensure the deployment has the generated `data/chunks/chunks.jsonl`, embedding artifacts, and `data/chroma/` collection. These runtime artifacts are intentionally excluded from Git; use a persistent disk or build/download them as part of deployment.
4. Add backend secrets/environment variables:
   - `LLM_PROVIDER=openrouter`
   - `LLM_MODEL=<an OpenRouter model ID enabled for your account>`
   - `OPENROUTER_API_KEY=<your key>`
5. Redeploy after adding or changing secrets. Never paste secrets into source files, commits, chat, or browser-visible variables.

## Vercel

The repository's Streamlit interface cannot run directly on Vercel's serverless runtime. The provided Vercel import URL does not change that runtime limitation, and a `vercel.json` pointing at Streamlit would not make it deployable.

To use the requested Vercel project flow, first make these architecture changes:

1. Replace `src/app.py` with a Vercel-supported frontend (for example Next.js/React) that reproduces the facts-only chat UI.
2. Deploy `src/pipeline.py` as a separate Python API service on a host that supports persistent Python services.
3. Move ChromaDB from local disk to a managed, persistent vector database and keep the query embedding model available to the backend.
4. Configure the Vercel frontend with `NEXT_PUBLIC_API_BASE_URL=<public backend API URL>` only. Do not put LLM or database credentials in `NEXT_PUBLIC_*` variables.
5. Configure these values as **backend-only** environment variables on the API host:
   - `LLM_PROVIDER=openrouter`
   - `LLM_MODEL=<an OpenRouter model ID enabled for your account>`
   - `OPENROUTER_API_KEY=<your key>`
   - Persistent vector database connection settings required by the chosen provider.
6. In Vercel, choose **Create New → Project**, import `shreya-rana-10/chatbotnextleap`, select the frontend root directory, add `NEXT_PUBLIC_API_BASE_URL`, and deploy. Connect the production branch so later pushes trigger Vercel deployments automatically.

Until that frontend/API/vector-store split is implemented, use a Streamlit-compatible host for a working deployment. Do not commit `.env`, ChromaDB data, or model/API credentials.
