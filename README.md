# Series Downloader → Telegram

GitHub Actions workflow — page URL දුන්නම CDN එකෙන් video download කරලා Telegram channel එකට upload කරනවා. **Free tier එකේ run වෙනවා.**

## Supported sites

| Site | Method |
|---|---|
| xmaza.xxx | scrape → aria2c |
| uncutmaza.movie | scrape → aria2c |
| zmaal.net | scrape → aria2c (presigned aware) |
| eporner.com | yt-dlp native |
| aznude.com | yt-dlp native |

## Setup

1. **Repo හදන්න** — GitHub → New repository (`series-downloader`, private OK)
2. **Files upload** — මේ structure එකට:
   ```
   .github/workflows/download.yml
   sites.yml
   scrape.py
   download.py
   requirements.txt
   urls.txt
   README.md
   .gitignore
   ```
3. **Secrets add** — Settings → Secrets and variables → Actions → New repository secret:
   - `TELEGRAM_BOT_TOKEN` → @BotFather එකෙන්
   - `TELEGRAM_CHAT_ID` → `@yourchannel` හෝ `-100xxxxxxxxxx`
4. **Bot එක channel එකට admin** කරන්න (Post Messages permission එක්ක)

## Use

1. `urls.txt` edit කරන්න — එක URL එකක් per line
2. Actions tab → "Series Downloader → Telegram" → **Run workflow**
3. Log එකේ progress බලන්න
4. Videos Telegram channel එකට + artifacts 3 days backup

## Telegram bot setup

1. @BotFather → `/newbot` → token එක copy කරන්න
2. Bot එක channel එකට **admin** කරන්න
3. Private channel ID එක ගන්න:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```

## Test locally

```bash
pip install -r requirements.txt
python download.py --dry-run     # commands print only
```

## Add a new site

`sites.yml` එකේ block එකක් add කරන්න:

```yaml
sites:
  newsite.com:
    cdn_domains:
      - cdn.newsite.com
    referer: https://newsite.com/

referer_map:
  cdn.newsite.com:
    - https://newsite.com/
```

## Notes

- **Free tier:** private repo 2000 min/month. Public unlimited.
- **Job timeout:** 350 min. Series ලොකු නම් `urls.txt` කොටස් වලට බෙදන්න.
- **Telegram limit:** bot API 2GB per file. Larger → Local Bot API server.
- **Presigned URLs (zmaal):** 7 days expire. එදාම run කරන්න.
- **Archive:** `archive.txt` — download කරපු IDs skip වෙනවා re-run එකේ.
