#!/usr/bin/env python3
"""Free, no-API backlink prospect discovery. Outputs a review-only CSV."""
from __future__ import annotations
import csv, os, re, sys, time, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "output"
OUT_FILE = OUT_DIR / "prospects.csv"
USER_AGENT = "ITSKHAYBacklinkResearchBot/1.0 (polite public-page research; no automated submissions)"
TIMEOUT = 15
DELAY_SECONDS = float(os.getenv("REQUEST_DELAY_SECONDS", "2"))
MAX_QUERIES = max(1, min(12, int(os.getenv("MAX_QUERIES", "12"))))
QUERIES = [
    '"submit your site" digital marketing directory',
    '"add your business" web design directory',
    'free business listing digital marketing agency',
    'web design agency directory submit listing',
    'digital marketing agency directory add listing',
    'free startup directory submit website',
    'website design portfolio directory submit',
    'SEO resources page suggest a resource',
    '"write for us" digital marketing guest post',
    'web design guest post guidelines',
    'Kerala business directory add listing',
    'India business directory submit website',
]
CATEGORY_RULES = [
    ("Digital marketing directory", ("digital marketing directory", "marketing agency directory", "seo agency directory")),
    ("Business listing", ("business listing", "add your business", "business directory", "local directory")),
    ("Portfolio / profile", ("portfolio", "designer directory", "agency profile", "professional profile")),
    ("Guest post", ("write for us", "guest post", "contributor guidelines", "submit an article")),
    ("Resource page", ("resources", "useful links", "suggest a resource", "recommended tools")),
    ("General directory", ("submit your site", "website directory", "add listing", "submit website")),
]

class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.title_parts = []
        self.links = []
        self.anchor = None
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == "title":
            self.in_title = True
        if tag.lower() == "a" and attrs.get("href"):
            self.anchor = {"href": attrs["href"], "text": []}
    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        if self.anchor is not None:
            self.anchor["text"].append(data)
    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False
        if tag.lower() == "a" and self.anchor is not None:
            self.links.append((self.anchor["href"], " ".join(self.anchor["text"]).strip()))
            self.anchor = None

def clean_url(url):
    url = url.strip()
    if url.startswith("//"):
        url = "https:" + url
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ("http", "https") or not p.netloc:
        return ""
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = re.sub(r"/{2,}", "/", p.path or "/")
    query = [(k, v) for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid", "ref"}]
    return urllib.parse.urlunsplit((p.scheme.lower(), host, path.rstrip("/") or "/", urllib.parse.urlencode(query), ""))

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        if "html" not in response.headers.get("Content-Type", "").lower():
            return "", response.geturl(), response.status
        data = response.read(1_500_000)
        encoding = response.headers.get_content_charset() or "utf-8"
        return data.decode(encoding, errors="replace"), response.geturl(), response.status

def allowed_by_robots(url):
    p = urllib.parse.urlsplit(url)
    robots_url = f"{p.scheme}://{p.netloc}/robots.txt"
    parser = RobotFileParser()
    try:
        req = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=8) as response:
            parser.parse(response.read(200_000).decode("utf-8", errors="replace").splitlines())
        return parser.can_fetch(USER_AGENT, url)
    except urllib.error.HTTPError as exc:
        return exc.code == 404
    except Exception:
        return False

def search_duckduckgo(query):
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote_plus(query)
    try:
        html, final_url, _ = fetch(url)
        parser = PageParser()
        parser.feed(html)
        found = []
        for href, label in parser.links:
            p = urllib.parse.urlsplit(href)
            qs = urllib.parse.parse_qs(p.query)
            if "uddg" in qs:
                href = qs["uddg"][0]
            candidate = clean_url(urllib.parse.urljoin(final_url, href))
            host = urllib.parse.urlsplit(candidate).hostname or ""
            if candidate and not any(x in host for x in ("duckduckgo.com", "bing.com", "google.com")):
                found.append((candidate, label))
        return found
    except Exception as exc:
        print(f"[WARN] Search failed for {query!r}: {exc}", file=sys.stderr)
        return []

def classify(text):
    text = text.lower()
    for category, words in CATEGORY_RULES:
        if any(word in text for word in words):
            return category
    return "Review manually"

def load_existing():
    rows = {}
    if OUT_FILE.exists():
        try:
            with OUT_FILE.open("r", newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    url = clean_url(row.get("URL", ""))
                    if url:
                        rows[url] = row
        except Exception as exc:
            print(f"[WARN] Could not read previous CSV: {exc}", file=sys.stderr)
    return rows

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    existing = load_existing()
    discovered = {}
    for i, query in enumerate(QUERIES[:MAX_QUERIES], 1):
        print(f"[{i}/{min(MAX_QUERIES, len(QUERIES))}] Searching: {query}")
        for url, label in search_duckduckgo(query):
            if url and url not in existing and url not in discovered:
                discovered[url] = {
                    "URL": url, "Domain": urllib.parse.urlsplit(url).hostname or "",
                    "Category": classify(query + " " + label + " " + url),
                    "Page title": label[:250], "Discovery query": query,
                    "HTTP status": "", "Robots allowed": "Not checked",
                    "Review status": "Needs human review",
                    "Notes": "Search result only. Manually verify relevance, legitimacy, submission rules, and link policy.",
                    "Discovered at (UTC)": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }
        time.sleep(DELAY_SECONDS)
    for i, row in enumerate(list(discovered.values())[:30], 1):
        url = row["URL"]
        try:
            if not allowed_by_robots(url):
                row["Robots allowed"] = "No / unable to verify"
                row["Notes"] += " Automated page check skipped because robots.txt disallows or could not be checked."
                continue
            row["Robots allowed"] = "Yes"
            html, final_url, status = fetch(url)
            row["HTTP status"] = str(status)
            row["URL"] = clean_url(final_url) or url
            parser = PageParser()
            parser.feed(html)
            if parser.title_parts:
                row["Page title"] = " ".join(" ".join(parser.title_parts).split())[:250]
            row["Category"] = classify(row["Category"] + " " + row["Page title"] + " " + row["URL"])
            row["Notes"] = "Page reachable. Human must confirm it is relevant and offers a legitimate, permitted opportunity."
        except Exception as exc:
            row["HTTP status"] = "Check failed"
            row["Notes"] += f" Automated check failed: {str(exc)[:180]}"
        print(f"Checked {i}: {url}")
        time.sleep(DELAY_SECONDS)
    merged = dict(existing)
    for url, row in discovered.items():
        key = clean_url(row["URL"]) or url
        if key not in merged:
            merged[key] = row
    columns = ["URL", "Domain", "Category", "Page title", "Discovery query", "HTTP status",
               "Robots allowed", "Review status", "Notes", "Discovered at (UTC)"]
    with OUT_FILE.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for key in sorted(merged):
            writer.writerow(merged[key])
    print(f"Finished. New prospects: {len(discovered)}; total saved: {len(merged)}")
    print(f"CSV: {OUT_FILE}")

if __name__ == "__main__":
    main()
