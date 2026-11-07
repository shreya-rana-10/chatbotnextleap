import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _streamlit_secret(name: str, default: str) -> str:
    try:
        import streamlit as st
        from streamlit.errors import StreamlitSecretNotFoundError

        return str(st.secrets.get(name, default))
    except StreamlitSecretNotFoundError:
        return default


def get_setting(name: str, default: str = "") -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    return _streamlit_secret(name, default).strip()


def load_config(path: str | Path = "config.yaml") -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    with config_path.open(encoding="utf-8") as config_file:
        cfg = yaml.safe_load(config_file)
    if not isinstance(cfg, dict):
        raise ValueError(f"Configuration must be a YAML mapping: {config_path}")
    cfg.setdefault("llm", {})["provider"] = get_setting(
        "LLM_PROVIDER", cfg["llm"].get("provider", "openrouter")
    ).lower()
    cfg.setdefault("llm", {})["model"] = get_setting(
        "LLM_MODEL", "qwen/qwen3.8-27b"
    )
    return cfg


def get_api_key(provider: str) -> str:
    key = get_setting(f"{provider.upper()}_API_KEY")
    if not key:
        raise RuntimeError(
            f"Missing {provider.upper()}_API_KEY in environment or Streamlit secrets"
        )
    return key
