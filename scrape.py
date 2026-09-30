# language: Python, file: scrape.py
# frontend page → direct CDN video URL extractor
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, unquote

import requests
import yaml

ROOT = Path(__file__).parent
SITES = yaml.safe_load((ROOT / "sites.yml").read_text())

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

CDN_PATTERNS = [
    # existing sites
    r"https?://video\.maalcdn\.com/[^\s\"'<>]+\.mp4(?:\?[^\s\"'<>]*)?",
    r"https?://cdn\.azmaal\.com/[^\s\"'<>]+\.mp4(?:\?[^\s\"'<>]*)?",
    r"https?://[a-z0-9\-]+\.maalcdn\.com/[^\s\"'<>]+\.(?:mp4|m3u8)(?:\?[^\s\"'<>]*)?",
    r"https?://cdn\.[a-z0-9\-]+\.com/[^\s\"'<>]+\.(?:mp4|m3u8)(?:\?[^\s\"'<>]*)?",
    # pornxnow / pxnw.xyz (signed URLs)
    r"https?://(?:[a-z0-9\-]+\.)*pxnw\.xyz/[^\s\"'<>]+\.(?:mp4|m3u8)(?:\?[^\s\"'<>]*)?",
]

# player config JSON — WP tube themes usually store file URL here
CONFIG_KEYS = ("file", "src", "url", "video_url", "videoUrl", "source", "hls", "mp4")


def cdn_base_for(page_url):
    """Relative path එකක් හම්බුනොත් prefix කරන්න CDN base එක."""
    host = urlparse(page_url).hostname or ""
    for site, cfg in SITES.get("sites", {}).items():
        if site in host:
            domains = cfg.get("cdn_domains") or []
            if domains:
                d = domains[0]
                return d if d.startswith("http") else f"https://{d}"
    return None


def abs_url(u, base_cdn):
    u = u.replace("\\/", "/").replace("&amp;", "&").strip()
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("http"):
        return u
    if u.startswith("/") and base_cdn:
        return base_cdn.rstrip("/") + u
    return None


def extract_urls(page_url):
    host = urlparse(page_url).hostname or ""
    referer = f"https://{host}/"
    base_cdn = cdn_base_for(page_url)

    r = requests.get(page_url, headers={
        "User-Agent": UA,
        "Referer": referer,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }, timeout=30, allow_redirects=True)
    r.raise_for_status()
    html = r.text

    raw = []

    # 1) direct CDN patterns
    for pat in CDN_PATTERNS:
        raw += re.findall(pat, html)

    # 2) <video> / <source> src
    for m in re.findall(r'<(?:video|source)[^>]+src=["\']([^"\']+)["\']', html, re.I):
        if ".mp4" in m or ".m3u8" in m:
            raw.append(m)

    # 3) player config JSON ("file":"...", "src":"...", etc.)
    for key in CONFIG_KEYS:
        for m in re.findall(rf'"{key}"\s*:\s*"([^"]+)"', html):
            if ".mp4" in m or ".m3u8" in m:
                raw.append(m)

    # normalize → absolute URLs
    norm = []
    for u in raw:
        a = abs_url(u, base_cdn)
        if a:
            norm.append(a)

    # dedupe by decoded form (%20 and space → same)
    seen = set()
    out = []
    for u in norm:
        key = unquote(u).strip()
        if key not in seen:
            seen.add(key)
            out.append(u)

    return out


if __name__ == "__main__":
    for page in sys.argv[1:]:
        print(f"# {page}")
        try:
            urls = extract_urls(page)
            if not urls:
                print(f"  [!] no video URL found on {page}", file=sys.stderr)
                continue
            for u in urls:
                print(u)
        except Exception as e:
            print(f"  [!] {page} → {e}", file=sys.stderr)
