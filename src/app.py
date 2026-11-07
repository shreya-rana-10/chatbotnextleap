import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from src.bootstrap import ensure_corpus_ready
from src.config import load_config
from src.pipeline import Assistant
from src.retrieval.guards import has_pii

st.set_page_config(
    page_title="HDFC Fund Facts",
    page_icon="●",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    :root {
        --ink: #1e2229;
        --muted: #68736f;
        --mint: #00b386;
        --mint-soft: #e6faf5;
        --line: #e5e9e7;
        --canvas: #f7faf8;
    }
    html, body, [class*="css"] { font-family: Inter, sans-serif; }
    [data-testid="stAppViewContainer"] { background: var(--canvas); }
    [data-testid="stHeader"] { background: transparent; }
    .block-container { max-width: 920px; padding: 1.4rem 1rem 5rem; }
    .topbar {
        display:flex; align-items:center; justify-content:space-between;
        padding: .2rem 0 1.1rem; border-bottom:1px solid var(--line); margin-bottom:2rem;
    }
    .brand { color:var(--ink); font-size:1.15rem; font-weight:700; letter-spacing:-.03em; }
    .brand span { color:var(--mint); }
    .trust-pill {
        display:inline-flex; align-items:center; gap:.4rem; border:1px solid #cceee4;
        background:#effbf7; color:#087456; border-radius:999px; padding:.35rem .7rem;
        font-size:.75rem; font-weight:600;
    }
    .hero { text-align:center; max-width:690px; margin:0 auto 1.5rem; }
    .eyebrow {
        color:#087456; text-transform:uppercase; letter-spacing:.12em;
        font-size:.72rem; font-weight:700;
    }
    .hero h1 { color:var(--ink); font-size:clamp(2rem,5vw,3rem); line-height:1.12; letter-spacing:-.045em; margin:.6rem 0; }
    .hero p { color:var(--muted); font-size:1rem; line-height:1.65; }
    .welcome-card {
        background:white; border:1px solid var(--line); border-radius:20px; padding:1.15rem 1.25rem;
        box-shadow:0 3px 14px rgba(30,34,41,.035); margin:1.2rem auto; max-width:720px;
    }
    .welcome-title { color:#087456; font-size:.8rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; }
    .scope-note { color:var(--muted); font-size:.86rem; margin:.35rem 0 0; }
    [data-testid="stChatMessage"] {
        border:1px solid var(--line); border-radius:18px; padding:.55rem .85rem;
        box-shadow:0 2px 8px rgba(30,34,41,.025);
    }
    [data-testid="stChatInput"] {
        width: min(100%, 680px); margin-inline: auto;
        border:1px solid #dfe7e3; border-radius:18px; box-shadow:0 6px 20px rgba(30,34,41,.06);
    }
    [data-testid="stChatInput"] textarea { font-family:Inter,sans-serif; }
    .stButton > button {
        min-height:48px; border:1px solid var(--line); border-radius:999px;
        background:white; color:var(--ink); font-weight:500;
    }
    .stButton > button:hover { border-color:#8adbc2; color:#087456; background:var(--mint-soft); }
    a { color:#087456 !important; }
    .footer-note { text-align:center; color:var(--muted); font-size:.78rem; padding:1.1rem 0; }
    @media (max-width: 600px) {
        .block-container { padding:1rem .75rem 4rem; }
        .topbar { margin-bottom:1.4rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="topbar">
      <div class="brand">HDFC <span>Fund Facts</span></div>
      <div class="trust-pill">● Public sources only</div>
    </div>
    <div class="hero">
      <div class="eyebrow">Mutual fund FAQ assistant</div>
      <h1>Clear facts. Cited sources.</h1>
      <p>Ask about expense ratio, exit load, minimum SIP, ELSS lock-in,
      riskometer, or benchmark for the listed HDFC schemes.</p>
    </div>
    <div class="welcome-card">
      <div class="welcome-title">Facts-only assistant</div>
      <p class="scope-note">Answers use the five configured public pages, include a source link,
      and are not investment advice.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

examples = [
    "What is the expense ratio of HDFC Large Cap Fund?",
    "What is the lock-in period for HDFC ELSS Tax Saver Fund?",
    "What is the minimum SIP for HDFC Mid Cap Fund?",
]

@st.cache_resource
def get_assistant() -> Assistant:
    with st.spinner("Preparing the fund facts index for this deployment..."):
        ensure_corpus_ready()
    return Assistant(load_config())


if "messages" not in st.session_state:
    st.session_state.messages = []
if "suggested_question" not in st.session_state:
    st.session_state.suggested_question = None

for item in st.session_state.messages:
    with st.chat_message(item["role"]):
        st.markdown(item["content"])
        if item.get("trace"):
            with st.expander("RAG internals"):
                st.json(item["trace"])

if not st.session_state.messages:
    st.markdown("#### Suggested questions")
    columns = st.columns(3)
    for column, example in zip(columns, examples):
        if column.button(example, use_container_width=True):
            st.session_state.suggested_question = example
            st.rerun()

question = st.session_state.suggested_question or st.chat_input(
    "Ask a factual question about these HDFC schemes",
    max_chars=500,
)
st.session_state.suggested_question = None

if question:
    try:
        result = get_assistant().ask(question)
    except (RuntimeError, ValueError, FileNotFoundError) as error:
        st.error(f"Assistant is not ready. Check the corpus and provider settings. ({error})")
    else:
        if has_pii(question):
            st.session_state.messages.append(
                {"role": "assistant", "content": result["answer"]}
            )
        else:
            st.session_state.messages.extend(
                [
                    {"role": "user", "content": question},
                    {
                        "role": "assistant",
                        "content": result["answer"],
                        "trace": result["trace"],
                    },
                ]
            )
        st.rerun()

st.markdown(
    '<div class="footer-note">Facts-only. No investment advice. '
    'Please verify scheme details at the cited public source.</div>',
    unsafe_allow_html=True,
)
