#!/usr/bin/env python3
"""Append newly published Crossref records matching Yanshang Wang's ORCID.

The script is intentionally conservative: it keeps the existing published list,
adds only DOI-backed journal articles that are not already present, and never
adds submitted or under-review records.
"""

from __future__ import annotations

import argparse
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
MAIN_DATA_FILE = ROOT / "_data" / "publications.yml"
OTHER_DATA_FILE = ROOT / "_data" / "other_author.yml"
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
            "pdf",
            "image",
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
    title = title.lower().replace("t2dm", "diabetes")
    title = title.replace("community-based", "community based")
    title = title.replace("cic-pdd", "cic pdd")
    return re.sub(r"\W+", " ", title).strip()


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


def is_user_author(author: dict[str, Any]) -> bool:
    family = str(author.get("family") or "").strip()
    given = str(author.get("given") or "").strip()
    return (
        normalize_orcid(str(author.get("ORCID") or "")) == ORCID_ID.lower()
        or (
            family.lower() == "wang"
            and given.lower().startswith("yanshang")
        )
    )


def format_authors(authors: list[dict[str, Any]]) -> str:
    names: list[str] = []
    for author in authors:
        family = str(author.get("family") or "").strip()
        given = str(author.get("given") or "").strip()
        if not family:
            continue
        name = f"{family}, {initials(given)}".rstrip(", ")
        names.append(
            f"<strong>{name}</strong>" if is_user_author(author) else name
        )

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
    raw_authors = item.get("author") or []
    user_author_index = next(
        (
            index
            for index, author in enumerate(raw_authors)
            if is_user_author(author)
        ),
        None,
    )
    if (
        re.search(
            r"\b(correction|erratum|retraction|corrigendum|expression of concern)\b",
            title,
            flags=re.I,
        )
        or not raw_authors
        or user_author_index is None
    ):
        return None

    authors = format_authors(raw_authors)
    if not doi or not title or not journal or not authors:
        return None

    short_journal = first(item.get("short-container-title")) or journal
    return {
        "_doi": doi.lower(),
        "_year": publication_year(item),
        "_category": "main" if user_author_index == 0 else "other",
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
        if record.get("pdf"):
            lines.append(f"    pdf: {quote(record['pdf'])}")
        if record.get("image"):
            lines.append(f"    image: {quote(record['image'])}")
        lines.append("    notes: Published")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report-file",
        help="Write newly discovered candidates as JSON for the email step.",
    )
    args = parser.parse_args()

    existing_main = parse_existing(
        MAIN_DATA_FILE.read_text(encoding="utf-8")
    )
    existing_other = parse_existing(
        OTHER_DATA_FILE.read_text(encoding="utf-8")
    )
    existing = existing_main + existing_other
    seen = {record_key(record) for record in existing}
    seen_titles = {normalize_title(record.get("title", "")) for record in existing}

    discovered_main: list[dict[str, Any]] = []
    discovered_other: list[dict[str, Any]] = []
    for item in fetch_crossref_items():
        record = crossref_record(item)
        if not record:
            continue
        key = record_key(record)
        title_key = normalize_title(record.get("title", ""))
        if key in seen or title_key in seen_titles:
            continue
        seen.add(key)
        seen_titles.add(title_key)
        if record.get("_category") == "main":
            discovered_main.append(record)
        else:
            discovered_other.append(record)

    sort_key = lambda record: (
        record.get("_year", 0),
        record["title"].lower(),
    )
    discovered_main.sort(key=sort_key, reverse=True)
    discovered_other.sort(key=sort_key, reverse=True)
    discovered = discovered_main + discovered_other

    MAIN_DATA_FILE.write_text(
        render(discovered_main + existing_main),
        encoding="utf-8",
    )
    OTHER_DATA_FILE.write_text(
        render(discovered_other + existing_other),
        encoding="utf-8",
    )
    if args.report_file:
        report_path = Path(args.report_file)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(discovered, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(
        f"Crossref returned {len(existing)} published records; "
        f"added {len(discovered)} new records "
        f"({len(discovered_main)} first-author, "
        f"{len(discovered_other)} other-author)."
    )


if __name__ == "__main__":
    main()
