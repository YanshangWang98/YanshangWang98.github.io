#!/usr/bin/env python3
"""Email newly discovered publication candidates through Gmail SMTP."""

from __future__ import annotations

import json
import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from html import escape
from pathlib import Path


def plain_authors(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value or "")


def main() -> None:
    report_file = Path(
        os.environ.get("PUBLICATION_REPORT_FILE", "publication-candidates.json")
    )
    candidates = json.loads(report_file.read_text(encoding="utf-8"))
    if not candidates:
        print("No new publication candidates; no email sent.")
        return

    username = os.environ.get("GMAIL_USERNAME", "").strip()
    app_password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    recipient = os.environ.get("GMAIL_TO", "wangyanshang98@gmail.com").strip()
    pr_url = os.environ.get("PUBLICATION_PR_URL", "").strip()

    if not username or not app_password or not recipient:
        raise RuntimeError(
            "Gmail is not configured. Add GMAIL_USERNAME, GMAIL_APP_PASSWORD, "
            "and GMAIL_TO as GitHub Actions secrets."
        )

    subject = (
        f"[Publication review] {len(candidates)} new publication "
        f"candidate{'s' if len(candidates) != 1 else ''}"
    )
    lines = [
        "Dear Yanshang,",
        "",
        "The weekly publication scan found the following candidate(s). "
        "Please confirm that they are your research before merging the website update.",
        "",
    ]
    html_items = []
    for index, candidate in enumerate(candidates, start=1):
        title = candidate.get("title", "")
        authors = plain_authors(candidate.get("authors", ""))
        journal = candidate.get("conference", "")
        year = candidate.get("_year") or "Year not available"
        page = candidate.get("page", "")
        lines.extend(
            [
                f"{index}. {title}",
                f"   Authors: {authors}",
                f"   Journal: {journal} ({year})",
                f"   Article: {page}",
                "",
            ]
        )
        html_items.append(
            "<li>"
            f"<strong>{escape(title)}</strong><br>"
            f"Authors: {escape(authors)}<br>"
            f"Journal: {escape(journal)} ({escape(str(year))})<br>"
            f'<a href="{escape(page)}">View article</a>'
            "</li>"
        )

    if pr_url:
        lines.extend(
            [
                "Review and merge the website update here:",
                pr_url,
                "",
            ]
        )
        html_items.append(
            f'<p><a href="{escape(pr_url)}">Review the GitHub Pull Request</a></p>'
        )

    lines.append(
        "The website will only change after the Pull Request is reviewed and merged."
    )
    html_body = (
        "<p>Dear Yanshang,</p>"
        "<p>The weekly publication scan found the following candidate(s). "
        "Please confirm that they are your research before merging the website update.</p>"
        f"<ol>{''.join(html_items)}</ol>"
        "<p>The website will only change after the Pull Request is reviewed and merged.</p>"
    )

    message = EmailMessage()
    message["From"] = username
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content("\n".join(lines))
    message.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(username, app_password)
        server.send_message(message)

    print(f"Sent {len(candidates)} publication candidate(s) to {recipient}.")


if __name__ == "__main__":
    main()
