from typing import Any

SYSTEM_PROMPT = """You are a facts-only assistant for HDFC Mutual Fund schemes.
Answer only from the provided context. If a fact is missing, say it was not found in the sources.
Use no more than three concise sentences. Give no investment advice or opinions and do not compute or compare returns.
Do not include URLs; the application adds the source link."""


def build_user_prompt(question: str, hits: list[dict[str, Any]]) -> str:
    context = "\n\n".join(
        f"[{index + 1}] {hit['text']}" for index, hit in enumerate(hits)
    )
    return f"CONTEXT:\n{context}\n\nQUESTION: {question}\n\nANSWER:"
