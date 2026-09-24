# language: Python, file: scrape.py
# frontend page එකේ HTML එකෙන් direct CDN mp4 URL එක extract කරනවා
import re
import sys
import requests
from urllib.parse import urlparse

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

CDN_PATTERNS = [
    r"https?://video\.maalcdn\.com/[^\s\"'<>]+\.mp4(?:\?[^\s\"'<>]*)?",
    r"https?://cdn\.azmaal\.com/[^\s\"'<>]+\.mp4(?:\?[^\s\"'<>]*)?",
    r"https?://[a-z0-9\-]+\.maalcdn\.com/[^\s\"'<>]+\.(?:mp4|m3u8)(?:\?[^\s\"'<>]*)?",
    r"https?://cdn\.[a-z0-9\-]+\.com/[^\s\"'<>]+\.(?:mp4|m3u8)(?:\?[^\s\"'<>]*)?",
]

def extract_urls(page_url: str) -> list[str]:
    host = urlparse(page_url).hostname or ""
    referer = f"https://{host}/"

    r = requests.get(page_url, headers={
        "User-Agent": UA,
        "Referer": referer,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }, timeout=30, allow_redirects=True)
    r.raise_for_status()
    html = r.text

    found = []
    for pat in CDN_PATTERNS:
        for m in re.findall(pat, html):
            m = m.replace("&amp;", "&")
            if m not in found:
                found.append(m)

    # <video src> / <source src> fallback
    for m in re.findall(r'<(?:video|source)[^>]+src=["\']([^"\']+)["\']', html, re.I):
        if m.startswith("//"):
            m = "https:" + m
        if (".mp4" in m or ".m3u8" in m) and m not in found:
            found.append(m)

    return found

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
