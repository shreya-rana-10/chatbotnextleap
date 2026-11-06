import json
from types import SimpleNamespace

import pytest

from src.formatter import format_answer
from src.ingestion.chunk import build_chunks, split_text
from src.ingestion.scrape import (
    ALLOWED_SOURCE_URLS,
    extract_fund_facts,
    extract_sections,
    read_sources,
)
from src.pipeline import Assistant
from src.llm.client import ProviderClient
from src.retrieval.guards import classify, has_pii
from src.retrieval.retriever import Retriever


@pytest.mark.parametrize(
    "text",
    [
        "My PAN is ABCDE1234F",
        "Aadhaar 1234 5678 9012",
        "Call me on 9876543210",
        "Email me at a@b.com",
        "OTP is 482910",
        "Account number 123456789012",
    ],
)
def test_pii_detection(text):
    assert has_pii(text)


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Should I buy HDFC Mid Cap Fund?", "advice"),
        ("What is the minimum amount to invest in HDFC ELSS?", "factual"),
        ("What are the 3-year returns of Large Cap?", "performance"),
        ("Compare Large Cap vs Mid Cap performance", "performance"),
        ("What is the exit load?", "factual"),
        ("What is the weather today?", "out_of_scope"),
    ],
)
def test_classification(question, expected):
    assert classify(question) == expected


def test_sources_are_the_five_fixed_urls():
    from src.config import ROOT

    sources = read_sources(ROOT / "data" / "sources.csv")
    assert {source["url"] for source in sources} == ALLOWED_SOURCE_URLS
    assert len(sources) == 5


def test_extraction_uses_visible_page_text_without_following_links():
    html = """
    <html><body><nav>Navigation text</nav><main>
      <h1>Fund details</h1><p>Expense ratio is listed here.</p>
      <a href="/mutual-funds/another-page">Related page</a>
      <script>ignore this</script>
    </main></body></html>
    """
    sections = extract_sections(html)
    text = " ".join(section["text"] for section in sections)
    assert "Expense ratio is listed here." in text
    assert "Related page" not in text
    assert "Navigation text" not in text
    assert "ignore this" not in text


def test_fund_facts_are_extracted_from_allowlisted_page_data():
    html = """
    <html><script id="__NEXT_DATA__" type="application/json">
    {"props":{"pageProps":{"mfServerSideData":{
      "expense_ratio":"1.2","exit_load":"Exit load of 1% if redeemed within 1 year",
      "min_sip_investment":500,
      "min_investment_amount":100,"lock_in":{"years":3,"months":0,"days":0},
      "benchmark_name":"NIFTY 500 Total Return Index",
      "return_stats":[{"risk":"Very High"}]
    }}}}
    </script></html>
    """
    facts = extract_fund_facts(html)
    assert {
        "title": "Expense ratio",
        "text": "Expense ratio for this scheme is 1.2%.",
    } in facts
    assert {
        "title": "Exit load",
        "text": "Exit load for this scheme is 1% if redeemed within 1 year.",
    } in facts
    assert {
        "title": "Minimum SIP",
        "text": "The minimum SIP for this scheme is INR 500.",
    } in facts
    assert {
        "title": "Minimum investment",
        "text": "The minimum lump-sum investment for this scheme is INR 100.",
    } in facts
    assert {
        "title": "Lock-in period",
        "text": "ELSS lock-in period for this scheme is 3 years.",
    } in facts
    assert {
        "title": "Benchmark",
        "text": "Benchmark for this scheme is NIFTY 500 Total Return Index.",
    } in facts
    assert {
        "title": "Riskometer",
        "text": "Riskometer for this scheme is Very High.",
    } in facts


def test_section_chunks_preserve_metadata_and_unique_ids():
    doc = {
        "doc_id": "sample-fund",
        "scheme_name": "Sample Fund",
        "page_type": "scheme",
        "source_url": next(iter(ALLOWED_SOURCE_URLS)),
        "scraped_at": "2026-11-06T10:00:00+00:00",
        "sections": [{"title": "Expense Ratio", "text": "Expense ratio information. " * 30}],
    }
    chunks = build_chunks([doc], size=100, overlap=20)
    assert len(chunks) > 1
    assert len({chunk["chunk_id"] for chunk in chunks}) == len(chunks)
    assert all(chunk["metadata"]["source_url"] == doc["source_url"] for chunk in chunks)
    assert all(chunk["text"].startswith("Sample Fund - Expense Ratio: ") for chunk in chunks)
    assert split_text("short text", size=30, overlap=5) == ["short text"]


def test_repeated_section_titles_produce_unique_chunk_ids():
    doc = {
        "doc_id": "sample-fund",
        "scheme_name": "Sample Fund",
        "page_type": "scheme",
        "source_url": next(iter(ALLOWED_SOURCE_URLS)),
        "scraped_at": "2026-11-06T10:00:00+00:00",
        "sections": [
            {"title": "Understand Terms", "text": "First section text is long enough."},
            {"title": "Understand Terms", "text": "Second section text is long enough."},
        ],
    }
    chunks = build_chunks([doc], size=100, overlap=10)
    assert [chunk["chunk_id"] for chunk in chunks] == [
        "sample-fund::understand-terms::0",
        "sample-fund::understand-terms-2::0",
    ]


def test_chunking_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        split_text("a long string", size=10, overlap=10)


def test_formatter_keeps_one_citation_and_limits_sentences():
    answer = format_answer(
        "One. Two. Three. Four. https://not-a-source.example/",
        "https://groww.in/mutual-funds/fund",
        "2026-11-06T10:00:00+00:00",
    )
    assert answer.count("http") == 1
    assert "Four" not in answer
    assert "Last updated from sources: 06 Nov 2026" in answer


class FakeModel:
    def encode(self, texts, normalize_embeddings):
        class FakeVector:
            def tolist(self):
                return [[1.0, 0.0]]

        return FakeVector()


class FakeCollection:
    metadata = {"embedding_model": "test-model"}

    def query(self, **kwargs):
        self.query_kwargs = kwargs
        return {
            "documents": [["ELSS lock-in is three years."]],
            "metadatas": [[
                {
                    "source_url": "https://groww.in/mutual-funds/hdfc-elss",
                    "scheme_name": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
                    "scraped_at": "2026-11-06T10:00:00+00:00",
                }
            ]],
            "distances": [[0.1]],
        }


def test_retriever_checks_model_and_filters_by_scheme():
    config = {
        "embedding": {"model": "test-model"},
        "retrieval": {"top_k": 4, "min_score": 0.3},
    }
    retriever = Retriever(config, model=FakeModel(), collection=FakeCollection())
    hits = retriever.retrieve("ELSS lock-in?")
    assert len(hits) == 1
    assert hits[0]["score"] == 0.9
    assert retriever.collection.query_kwargs["where"] == {
        "$and": [
            {"scheme_name": "HDFC ELSS Tax Saver Fund Direct Plan Growth"},
            {"section": "lock-in-period"},
        ]
    }

    with pytest.raises(RuntimeError, match="Embedding model mismatch"):
        Retriever(
            {"embedding": {"model": "another-model"}},
            model=FakeModel(),
            collection=FakeCollection(),
        )


class FakeRetriever:
    def __init__(self):
        self.called = False

    def retrieve(self, question):
        self.called = True
        return [
            {
                "text": "The expense ratio is 0.5%.",
                "score": 0.9,
                "metadata": {
                    "source_url": "https://groww.in/mutual-funds/fund",
                    "scheme_name": "HDFC Large Cap Fund Direct Growth",
                    "scraped_at": "2026-11-06T10:00:00+00:00",
                },
            }
        ]

    @staticmethod
    def detect_scheme(question):
        return None

    @staticmethod
    def detect_fact_sections(question):
        return []


class FakeLLM:
    def generate(self, system, user):
        return "The expense ratio is 0.5%. See https://example.com."


def test_pipeline_refuses_pii_without_retrieval_or_logging(tmp_path, monkeypatch):
    import src.pipeline as pipeline_module

    monkeypatch.setattr(pipeline_module, "ROOT", tmp_path)
    retriever = FakeRetriever()
    assistant = Assistant(
        cfg={
            "paths": {"logs": "logs/queries.jsonl"},
            "llm": {"max_sentences": 3},
            "links": {
                "educational": "https://www.amfiindia.com/investor-corner",
                "factsheet_fallback": "https://groww.in/mutual-funds/amc/hdfc-mutual-funds",
            },
        },
        retriever=retriever,
        llm=FakeLLM(),
    )
    result = assistant.ask("My PAN is ABCDE1234F. What is the expense ratio?")
    assert result["trace"]["class"] == "pii"
    assert not retriever.called
    assert not (tmp_path / "logs" / "queries.jsonl").exists()


def test_pipeline_answers_from_top_hit_and_logs_non_pii_trace(tmp_path, monkeypatch):
    import src.pipeline as pipeline_module

    monkeypatch.setattr(pipeline_module, "ROOT", tmp_path)
    assistant = Assistant(
        cfg={
            "paths": {"logs": "logs/queries.jsonl"},
            "llm": {"max_sentences": 3},
            "links": {
                "educational": "https://www.amfiindia.com/investor-corner",
                "factsheet_fallback": "https://groww.in/mutual-funds/amc/hdfc-mutual-funds",
            },
        },
        retriever=FakeRetriever(),
        llm=FakeLLM(),
    )
    result = assistant.ask("What is the expense ratio of HDFC Large Cap Fund?")
    assert result["answer"].count("http") == 1
    assert "Last updated from sources:" in result["answer"]
    logged = json.loads((tmp_path / "logs" / "queries.jsonl").read_text(encoding="utf-8"))
    assert logged["query"] == "What is the expense ratio of HDFC Large Cap Fund?"


def test_openrouter_uses_openai_compatible_client_without_network(monkeypatch):
    import openai

    calls = {}

    def create_completion(**kwargs):
        calls["completion"] = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Answer from context."))]
        )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=create_completion)
        )
    )

    def create_openai_client(**kwargs):
        calls["client"] = kwargs
        return fake_client

    monkeypatch.setattr(openai, "OpenAI", create_openai_client)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-sent-over-network")
    client = ProviderClient(
        {
            "llm": {
                "provider": "openrouter",
                "model": "provider/test-model",
                "temperature": 0.0,
                "timeout_seconds": 5,
            }
        }
    )
    assert client.client is None
    assert client.generate("system rules", "question") == "Answer from context."
    assert calls["client"]["base_url"] == "https://openrouter.ai/api/v1"
    assert calls["client"]["api_key"] == "test-key-not-sent-over-network"
    assert calls["completion"]["model"] == "provider/test-model"
    assert calls["completion"]["max_tokens"] == 400
