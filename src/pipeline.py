import json
import logging
from datetime import datetime, timezone
from typing import Any

from src.config import ROOT, load_config
from src.formatter import format_answer
from src.llm.client import get_client
from src.prompts import SYSTEM_PROMPT, build_user_prompt
from src.retrieval.guards import classify, has_pii
from src.retrieval.retriever import Retriever

logger = logging.getLogger(__name__)
PII_MESSAGE = "Please don't share personal or account details. I've ignored that message."


def _citation(answer: str, url: str, scraped_at: str, max_sentences: int) -> str:
    return format_answer(answer, url, scraped_at, max_sentences)


class Assistant:
    def __init__(
        self,
        cfg: dict[str, Any] | None = None,
        retriever: Any = None,
        llm: Any = None,
    ) -> None:
        self.cfg = cfg or load_config()
        self.retriever = retriever or Retriever(self.cfg)
        self.llm = llm or get_client(self.cfg)

    def _log_trace(self, trace: dict[str, Any]) -> None:
        path = ROOT / self.cfg["paths"]["logs"]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(trace, ensure_ascii=False) + "\n")

    def ask(self, question: str) -> dict[str, Any]:
        if not question.strip():
            return {
                "answer": "Please enter a question about the listed HDFC Mutual Fund pages.",
                "trace": {"class": "empty"},
            }
        if has_pii(question):
            return {"answer": PII_MESSAGE, "trace": {"class": "pii"}}
        if len(question) > 500:
            return {
                "answer": "Please keep your question under 500 characters.",
                "trace": {"class": "too_long"},
            }

        label = classify(question)
        if label == "advice":
            link = self.cfg["links"]["educational"]
            return {
                "answer": f"I can share scheme facts, but not advice on buying or selling.\n\nLearn more: {link}",
                "trace": {"class": label},
            }
        if label == "performance":
            scheme = self.retriever.detect_scheme(question)
            link = next(
                (
                    hit["metadata"]["source_url"]
                    for hit in self.retriever.retrieve(question)
                    if hit["metadata"].get("scheme_name") == scheme
                ),
                self.cfg["links"]["factsheet_fallback"],
            ) if scheme else self.cfg["links"]["factsheet_fallback"]
            return {
                "answer": f"I don't calculate or compare returns. Please consult the official scheme page for performance details.\n\nSource: {link}",
                "trace": {"class": label},
            }
        if label == "out_of_scope":
            link = self.cfg["links"]["educational"]
            return {
                "answer": f"I can answer factual questions about the listed HDFC Mutual Fund pages only.\n\nLearn more: {link}",
                "trace": {"class": label},
            }

        if (
            self.retriever.detect_fact_sections(question)
            and not self.retriever.detect_scheme(question)
        ):
            link = self.cfg["links"]["factsheet_fallback"]
            return {
                "answer": (
                    "Which HDFC scheme do you mean: Large Cap, Flexi Cap, "
                    f"ELSS, or Mid Cap?\n\nSource: {link}"
                ),
                "trace": {"class": "needs_scheme"},
            }

        hits = self.retriever.retrieve(question)
        if not hits:
            link = self.cfg["links"]["factsheet_fallback"]
            return {
                "answer": f"I couldn't find that in my sources.\n\nSource: {link}",
                "trace": {"class": label, "hits": []},
            }
        prompt = build_user_prompt(question, hits)
        metadata = hits[0]["metadata"]
        try:
            generated = self.llm.generate(SYSTEM_PROMPT, prompt)
        except RuntimeError:
            logger.exception("LLM provider failed while answering a non-PII query")
            answer = _citation(
                "I couldn't generate an answer right now. Please try again.",
                metadata["source_url"],
                metadata["scraped_at"],
                self.cfg["llm"]["max_sentences"],
            )
            return {
                "answer": answer,
                "trace": {"class": label, "hits": hits, "error": "llm_generation_failed"},
            }
        answer = _citation(
            generated,
            metadata["source_url"],
            metadata["scraped_at"],
            self.cfg["llm"]["max_sentences"],
        )
        trace = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": question,
            "class": label,
            "hits": hits,
            "prompt": prompt,
        }
        self._log_trace(trace)
        return {"answer": answer, "trace": trace}
