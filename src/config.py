import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def load_config(path: str | Path = "config.yaml") -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    with config_path.open(encoding="utf-8") as config_file:
        cfg = yaml.safe_load(config_file)
    if not isinstance(cfg, dict):
        raise ValueError(f"Configuration must be a YAML mapping: {config_path}")
    cfg.setdefault("llm", {})["provider"] = os.getenv(
        "LLM_PROVIDER", cfg["llm"].get("provider", "openrouter")
    ).strip().lower()
    cfg.setdefault("llm", {})["model"] = os.getenv("LLM_MODEL", "qwen/qwen3.8-27b")
    return cfg


def get_api_key(provider: str) -> str:
    key = os.getenv(f"{provider.upper()}_API_KEY", "").strip()
    if not key:
        raise RuntimeError(f"Missing {provider.upper()}_API_KEY in .env")
    return key
