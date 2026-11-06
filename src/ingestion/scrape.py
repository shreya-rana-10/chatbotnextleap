import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from src.config import ROOT, load_config

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MFFAQBot/1.0; public-page-only)"}
ALLOWED_SOURCE_URLS = {
    "https://groww.in/mutual-funds/amc/hdfc-mutual-funds",
    "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
    "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
}


def read_sources(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        sources = list(csv.DictReader(source_file))
    required = {"doc_id", "scheme_name", "page_type", "url"}
    if not sources or not required.issubset(sources[0]):
        raise ValueError(f"Sources CSV must contain columns: {', '.join(sorted(required))}")
    urls = [row["url"] for row in sources]
    if len(urls) != len(set(urls)):
        raise ValueError("Source URLs must be unique")
    if set(urls) != ALLOWED_SOURCE_URLS:
        raise ValueError("Source list must contain exactly the five approved public pages")
    for row in sources:
        if not row["doc_id"].replace("-", "").isalnum():
            raise ValueError(f"Invalid document ID: {row['doc_id']}")
        parsed = urlparse(row["url"])
        if parsed.scheme != "https" or parsed.netloc.lower() != "groww.in":
            raise ValueError(f"Source URL is not an allowed public Groww page: {row['url']}")
    return sources


def extract_sections(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        tag.decompose()
    main = soup.find("main") or soup.body or soup
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] = {"title": "Overview", "text": []}
    for element in main.find_all(["h1", "h2", "h3", "p", "li", "td", "th"]):
        if element.name in {"h1", "h2", "h3"}:
            if current["text"]:
                sections.append(
                    {"title": current["title"], "text": " ".join(current["text"])}
                )
            current = {"title": element.get_text(" ", strip=True) or "Overview", "text": []}
        else:
            text = element.get_text(" ", strip=True)
            if text:
                current["text"].append(text)
    if current["text"]:
        sections.append({"title": current["title"], "text": " ".join(current["text"])})
    return sections


def extract_fund_facts(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    payload = soup.find("script", id="__NEXT_DATA__")
    if payload is None:
        return []
    try:
        page_data = json.loads(payload.string or payload.get_text())
    except json.JSONDecodeError as exc:
        raise ValueError("Could not parse the public page's embedded data") from exc
    server_data = (
        page_data.get("props", {})
        .get("pageProps", {})
        .get("mfServerSideData", {})
    )
    if not isinstance(server_data, dict):
        return []

    facts: list[dict[str, str]] = []

    def add_fact(title: str, text: str) -> None:
        facts.append({"title": title, "text": text})

    expense_ratio = server_data.get("expense_ratio")
    if isinstance(expense_ratio, (int, float, str)) and str(expense_ratio).strip():
        add_fact("Expense ratio", f"Expense ratio for this scheme is {expense_ratio}%.")
    exit_load = server_data.get("exit_load")
    if isinstance(exit_load, str) and exit_load.strip():
        exit_text = exit_load.strip().rstrip(".")
        if exit_text.casefold().startswith("exit load"):
            exit_text = exit_text[len("exit load") :].strip()
            exit_text = exit_text.removeprefix("of ").strip()
        add_fact("Exit load", f"Exit load for this scheme is {exit_text}.")
    min_sip = server_data.get("min_sip_investment")
    if isinstance(min_sip, (int, float)):
        add_fact("Minimum SIP", f"The minimum SIP for this scheme is INR {min_sip:g}.")
    min_lumpsum = server_data.get("min_investment_amount")
    if isinstance(min_lumpsum, (int, float)):
        add_fact(
            "Minimum investment",
            f"The minimum lump-sum investment for this scheme is INR {min_lumpsum:g}.",
        )
    lock_in = server_data.get("lock_in")
    if isinstance(lock_in, dict):
        years = lock_in.get("years", 0) or 0
        months = lock_in.get("months", 0) or 0
        days = lock_in.get("days", 0) or 0
        if years or months or days:
            parts = []
            if years:
                parts.append(f"{years} years")
            if months:
                parts.append(f"{months} months")
            if days:
                parts.append(f"{days} days")
            add_fact("Lock-in period", f"ELSS lock-in period for this scheme is {', '.join(parts)}.")
    benchmark = server_data.get("benchmark_name") or server_data.get("benchmark")
    if isinstance(benchmark, str) and benchmark.strip():
        add_fact("Benchmark", f"Benchmark for this scheme is {benchmark.strip()}.")
    return_stats = server_data.get("return_stats")
    riskometer = next(
        (
            entry.get("risk")
            for entry in return_stats or []
            if isinstance(entry, dict)
            and isinstance(entry.get("risk"), str)
            and entry["risk"].strip()
        ),
        None,
    )
    riskometer = riskometer or server_data.get("nfo_risk")
    if isinstance(riskometer, str) and riskometer.strip():
        add_fact("Riskometer", f"Riskometer for this scheme is {riskometer.strip()}.")
    return facts


def _validate_response_url(response: requests.Response, requested_url: str) -> None:
    if response.url != requested_url:
        raise RuntimeError(
            f"Refusing redirect outside the explicitly configured source URL: {requested_url}"
        )


def fetch_html(url: str, retries: int, timeout: int) -> str:
    last_error: requests.RequestException | None = None
    for attempt in range(retries + 1):
        try:
            response = requests.get(
                url, headers=HEADERS, timeout=timeout, allow_redirects=False
            )
            if 300 <= response.status_code < 400:
                raise RuntimeError(f"Refusing redirect from allowlisted source: {url}")
            response.raise_for_status()
            _validate_response_url(response, url)
            return response.text
        except requests.RequestException as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(attempt + 1)
    raise RuntimeError(f"Failed to fetch public source {url}") from last_error


def fetch_html_browser(url: str, timeout: int) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            response = page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            if response is None or not response.ok:
                status = response.status if response else "no response"
                raise RuntimeError(f"Browser fetch failed for {url}: {status}")
            if page.url != url:
                raise RuntimeError(f"Refusing browser redirect outside the source URL: {url}")
            return page.content()
        finally:
            browser.close()


def run() -> int:
    cfg = load_config()
    raw_dir = ROOT / cfg["paths"]["raw"]
    scraped_dir = ROOT / cfg["paths"]["scraped"]
    raw_dir.mkdir(parents=True, exist_ok=True)
    scraped_dir.mkdir(parents=True, exist_ok=True)
    scraping = cfg["scraping"]
    sources = read_sources(ROOT / cfg["paths"]["sources"])
    for source in sources:
        html = fetch_html(
            source["url"], scraping["retries"], scraping["timeout_seconds"]
        )
        sections = extract_sections(html)
        if source["page_type"] == "scheme":
            sections.extend(extract_fund_facts(html))
        if (
            sum(len(section["text"]) for section in sections)
            < scraping["min_text_chars"]
            and scraping["browser_fallback"]
        ):
            html = fetch_html_browser(source["url"], scraping["timeout_seconds"])
            sections = extract_sections(html)
            if source["page_type"] == "scheme":
                sections.extend(extract_fund_facts(html))
        if not sections:
            raise RuntimeError(f"No visible text could be extracted from {source['url']}")
        (raw_dir / f"{source['doc_id']}.html").write_text(html, encoding="utf-8")
        record = {
            **source,
            "source_url": source["url"],
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "sections": sections,
        }
        (scraped_dir / f"{source['doc_id']}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Scraped {source['doc_id']}: {len(sections)} sections")
    return len(sources)


if __name__ == "__main__":
    run()
