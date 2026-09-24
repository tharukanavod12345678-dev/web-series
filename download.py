# language: Python, file: download.py
# urls.txt → scrape (page නම්) → download (aria2c හෝ yt-dlp)
import re
import sys
import subprocess
import argparse
from pathlib import Path
from urllib.parse import urlparse, unquote

import yaml

ROOT = Path(__file__).parent
SITES = yaml.safe_load((ROOT / "sites.yml").read_text())
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

def referer_for(url: str):
    host = urlparse(url).hostname or ""
    for cdn, refs in SITES.get("referer_map", {}).items():
        if cdn in host:
            return refs[0]
    for site, cfg in SITES.get("sites", {}).items():
        if site in host and cfg.get("referer"):
            return cfg["referer"]
    return None

def is_native(url: str) -> bool:
    host = urlparse(url).hostname or ""
    for site, cfg in SITES.get("sites", {}).items():
        if site in host and cfg.get("extractor") == "ytdlp-native":
            return True
    return False

def is_direct_media(url: str) -> bool:
    return bool(re.search(r"\.(mp4|m3u8|webm|mkv)(\?|$)", url, re.I))

def is_presigned(url: str) -> bool:
    return "X-Amz-Signature" in url or "Signature=" in url or "token=" in url

def safe_name(url: str) -> str:
    path = urlparse(url).path
    name = path.rsplit("/", 1)[-1] or "video.mp4"
    return unquote(name)

def cmd_aria2(url: str, out_dir: Path, referer):
    out_dir.mkdir(parents=True, exist_ok=True)
    name = safe_name(url)
    cmd = [
        "aria2c",
        "-x", "16", "-s", "16", "-k", "1M",
        "--file-allocation=none",
        "--continue=true",
        "--auto-file-renaming=false",
        "--allow-overwrite=false",
        "-d", str(out_dir),
        "-o", name,
        f"--user-agent={UA}",
    ]
    if referer:
        cmd += [f"--header=Referer: {referer}",
                f"--header=Origin: {referer.rstrip('/')}"]
    cmd.append(url)
    return cmd

def cmd_ytdlp(url: str, out_dir: Path, referer, playlist: bool):
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "yt-dlp",
        "--paths", str(out_dir),
        "--output", "%(title).150B [%(id)s].%(ext)s",
        "--format", "bv*+ba/b",
        "--merge-output-format", "mp4",
        "--no-overwrites", "--continue",
        "--download-archive", str(ROOT / "archive.txt"),
        "--retries", "15", "--fragment-retries", "15",
        "--concurrent-fragments", "4",
        "--ignore-errors",
        "--yes-playlist" if playlist else "--no-playlist",
    ]
    if referer:
        cmd += ["--add-header", f"Referer:{referer}",
                "--add-header", f"Origin:{referer.rstrip('/')}",
                "--user-agent", UA]
    cmd.append(url)
    return cmd

def run(cmd, dry: bool):
    print("+", " ".join(cmd))
    if dry:
        return
    subprocess.run(cmd, check=False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--urls", default=str(ROOT / "urls.txt"))
    args = ap.parse_args()

    out_dir = ROOT / "downloads"
    out_dir.mkdir(exist_ok=True)

    urls = [l.strip() for l in Path(args.urls).read_text().splitlines()
            if l.strip() and not l.strip().startswith("#")]

    for url in urls:
        print(f"\n=== {url} ===")

        # 1) direct mp4/m3u8 → aria2c
        if is_direct_media(url) and not is_native(url):
            ref = None if is_presigned(url) else referer_for(url)
            run(cmd_aria2(url, out_dir, ref), args.dry_run)
            continue

        # 2) native yt-dlp
        if is_native(url):
            ref = referer_for(url)
            is_pl = bool(re.search(r"/(playlist|channel|user|c/|@)", url, re.I))
            run(cmd_ytdlp(url, out_dir, ref, is_pl), args.dry_run)
            continue

        # 3) frontend page → scrape
        print(f"[scrape] {url}")
        r = subprocess.run([sys.executable, str(ROOT / "scrape.py"), url],
                           capture_output=True, text=True)
        print(r.stdout)
        if r.stderr:
            print(r.stderr, file=sys.stderr)

        for line in r.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            ref = None if is_presigned(line) else (referer_for(line) or referer_for(url))
            if is_direct_media(line):
                run(cmd_aria2(line, out_dir, ref), args.dry_run)
            else:
                run(cmd_ytdlp(line, out_dir, ref, False), args.dry_run)

if __name__ == "__main__":
    main()
