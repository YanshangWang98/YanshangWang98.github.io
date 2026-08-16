#!/usr/bin/env python3
"""Append newly published Crossref records matching Yanshang Wang's ORCID.

The script is intentionally conservative: it keeps the existing published list,
adds only DOI-backed journal articles that are not already present, and never
adds submitted or under-review records.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ORCID_ID = os.environ.get("ORCID_ID", "0000-0001-6110-6296")
CROSSREF_MAILTO = os.environ.get(
    "CROSSREF_MAILTO", "wangyanshang98@gmail.com"
)
ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "_data" / "publications.yml"
BLOCK_RE = re.compile(r"(?ms)^  - title:.*?(?=^  - title:|\Z)")


def first(value: Any) -> str:
    if isinstance(value, list):
        return str(value[0]).strip() if value else ""
    return str(value or "").strip()


def yaml_value(value: str) -> str:
    value = value.strip()
    if value.startswith('"'):
        try:
            return str(json.loads(value))
        except json.JSONDecodeError:
            pass
    return value


def parse_existing(text: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for block in BLOCK_RE.findall(text):
        record: dict[str, str] = {}
        for key in (
            "title",
            "authors",
            "conference_short",
            "conference",
            "page",
            "notes",
        ):
            match = re.search(
                rf"(?m)^\s*(?:-\s*)?{re.escape(key)}:\s*(.*)$", block
            )
            if match:
                record[key] = yaml_value(match.group(1))
        if record.get("notes") == "Published" and record.get("title"):
            records.append(record)
    return records


def normalize_title(title: str) -> str:
    return re.sub(r"\W+", " ", title.lower()).strip()


def normalize_orcid(value: str) -> str:
    return value.rstrip("/").split("/")[-1].lower()


def extract_doi(value: str) -> str:
    value = urllib.parse.unquote(value or "")
    match = re.search(
        r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", value, flags=re.I
    )
    if not match:
        return ""
    return match.group(0).rstrip(".,;)")


def record_key(record: dict[str, Any]) -> str:
    doi = record.get("_doi") or extract_doi(record.get("page", ""))
    return doi.lower() if doi else normalize_title(record.get("title", ""))


def initials(given: str) -> str:
    tokens = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", given)
    return " ".join(f"{token[0].upper()}." for token in tokens)


def format_authors(authors: list[dict[str, Any]]) -> str:
    names: list[str] = []
    for author in authors:
        family = str(author.get("family") or "").strip()
        given = str(author.get("given") or "").strip()
        if not family:
            continue
        name = f"{family}, {initials(given)}".rstrip(", ")
        is_user = (
            normalize_orcid(str(author.get("ORCID") or "")) == ORCID_ID.lower()
            or (
                family.lower() == "wang"
                and given.lower().startswith("yanshang")
            )
        )
        names.append(f"<strong>{name}</strong>" if is_user else name)

    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " & " + names[-1]


def publication_year(item: dict[str, Any]) -> int:
    for field in ("published-online", "published-print", "published"):
        date_parts = item.get(field, {}).get("date-parts", [])
        if date_parts and date_parts[0]:
            try:
                return int(date_parts[0][0])
            except (TypeError, ValueError):
                pass
    return 0


def fetch_crossref_items() -> list[dict[str, Any]]:
    params = {
        "filter": f"orcid:{ORCID_ID},type:journal-article",
        "rows": "1000",
        "select": (
            "DOI,title,author,container-title,short-container-title,"
            "published,published-online,published-print,type"
        ),
        "mailto": CROSSREF_MAILTO,
        "sort": "published",
        "order": "desc",
    }
    url = "https://api.crossref.org/v1/works?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": f"YanshangWang-homepage/1.0 (mailto:{CROSSREF_MAILTO})",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    items = payload.get("message", {}).get("items", [])
    if not items:
        raise RuntimeError("Crossref returned no works; refusing to rewrite the list.")
    return items


def crossref_record(item: dict[str, Any]) -> dict[str, Any] | None:
    doi = str(item.get("DOI") or "").strip()
    title = first(item.get("title"))
    journal = first(item.get("container-title"))
    authors = format_authors(item.get("author") or [])
    if not doi or not title or not journal or not authors:
        return None

    short_journal = first(item.get("short-container-title")) or journal
    return {
        "_doi": doi.lower(),
        "_year": publication_year(item),
        "title": title,
        "authors": authors,
        "conference_short": short_journal,
        "conference": journal,
        "page": f"https://doi.org/{doi}",
        "notes": "Published",
    }


def quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render(records: list[dict[str, str]]) -> str:
    lines = ["main:"]
    for record in records:
        lines.append(f"  - title: {quote(record['title'])}")
        lines.append(f"    authors: {quote(record['authors'])}")
        if record.get("conference_short"):
            lines.append(
                f"    conference_short: {quote(record['conference_short'])}"
            )
        lines.append(f"    conference: {quote(record['conference'])}")
        lines.append(f"    page: {quote(record['page'])}")
        lines.append("    notes: Published")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    current = DATA_FILE.read_text(encoding="utf-8")
    existing = parse_existing(current)
    seen = {record_key(record) for record in existing}

    discovered: list[dict[str, Any]] = []
    for item in fetch_crossref_items():
        record = crossref_record(item)
        if not record:
            continue
        key = record_key(record)
        if key in seen:
            continue
        seen.add(key)
        discovered.append(record)

    discovered.sort(
        key=lambda record: (record.get("_year", 0), record["title"].lower()),
        reverse=True,
    )
    output_records = discovered + existing
    DATA_FILE.write_text(render(output_records), encoding="utf-8")
    print(
        f"Crossref returned {len(existing) + len(discovered)} published records; "
        f"added {len(discovered)} new records."
    )


if __name__ == "__main__":
    main()
