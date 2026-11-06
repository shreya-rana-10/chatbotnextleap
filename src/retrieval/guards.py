import re

PII_PATTERNS = [
    re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE),
    re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)"),
    re.compile(r"\botp\b\D{0,10}\d{4,8}", re.IGNORECASE),
    re.compile(r"\b(?:a/?c|account)\D{0,15}\d{9,18}\b", re.IGNORECASE),
]

ADVICE_TERMS = (
    "should i",
    "buy",
    "sell",
    "invest in",
    "best fund",
    "which fund",
    "recommend",
    "better than",
    "good fund",
    "worth it",
    "my portfolio",
    "switch",
    "redeem now",
)
DIRECT_ADVICE_TERMS = tuple(term for term in ADVICE_TERMS if term != "invest in")
PERFORMANCE_TERMS = (
    "return",
    "returns",
    "cagr",
    "performance",
    "performed",
    "profit",
    "xirr",
    "outperform",
    "compare",
)
FACTUAL_TERMS = (
    "expense ratio",
    "exit load",
    "minimum sip",
    "minimum investment",
    "minimum amount",
    "sip",
    "lock-in",
    "lock in",
    "riskometer",
    "benchmark",
    "statement",
    "capital gains",
    "download",
    "fund",
    "scheme",
    "elss",
    "large cap",
    "flexi cap",
    "mid cap",
    "hdfc",
)
FACT_QUESTION_TERMS = (
    "expense ratio",
    "exit load",
    "minimum sip",
    "minimum investment",
    "minimum amount",
    "lock-in",
    "lock in",
    "riskometer",
    "benchmark",
    "statement",
    "capital gains",
    "download",
)


def has_pii(text: str) -> bool:
    return any(pattern.search(text) for pattern in PII_PATTERNS)


def classify(query: str) -> str:
    normalized = query.casefold()
    if any(term in normalized for term in PERFORMANCE_TERMS):
        return "performance"
    if any(term in normalized for term in DIRECT_ADVICE_TERMS):
        return "advice"
    if "invest in" in normalized:
        return (
            "factual"
            if any(term in normalized for term in FACT_QUESTION_TERMS)
            else "advice"
        )
    if any(term in normalized for term in FACTUAL_TERMS):
        return "factual"
    return "out_of_scope"
