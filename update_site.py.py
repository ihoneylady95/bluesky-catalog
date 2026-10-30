
import html
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

HANDLE = "ai-models.bsky.social"
PROFILE = f"https://bsky.app/profile/{HANDLE}"

# ОБЯЗАТЕЛЬНО укажи свой настоящий адрес GitHub Pages
SITE_URL = "".rstrip("/")

API = "https://public.api.bsky.app/xrpc"
OUT = Path(".")

session = requests.Session()
session.headers["User-Agent"] = "AIModelsBlueskyCatalog/1.0"


def get_posts():
    posts = {}
    cursor = None

    while True:
        params = {"actor": HANDLE, "limit": 100}
        if cursor:
            params["cursor"] = cursor

        response = session.get(
            f"{API}/app.bsky.feed.getAuthorFeed",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        for item in data.get("feed", []):
            post = item.get("post", {})
            author = post.get("author", {})

            # Не добавляем чужие репосты
            if author.get("handle", "").lower() != HANDLE.lower():
                continue

            uri = post.get("uri", "")
            rkey = uri.rsplit("/", 1)[-1]
            if not rkey:
                continue

            url = f"{PROFILE}/post/{rkey}"
            record = post.get("record", {})
            text = record.get("text", "")

            posts[url] = {
                "url": url,
                "text": text,
                "date": record.get("createdAt", "")
            }

        cursor = data.get("cursor")
        if not cursor:
            break

    return sorted(
        posts.values(),
        key=lambda p: p["date"],
        reverse=True
    )


def build_site(posts):
    cards = []

    for post in posts:
        text = html.escape(post["text"]).replace("\n", "<br>\n")
        url = html.escape(post["url"], quote=True)
        date = html.escape(post["date"])

        cards.append(f"""
        <article class="post">
          <div class="post-text">{text}</div>
          <div class="post-footer">
            <time>{date}</time>
            <a href="{url}" target="_blank"
               rel="noopener noreferrer">View post on Bluesky</a>
          </div>
        </article>
        """)

    site = html.escape(SITE_URL + "/", quote=True)
    profile = html.escape(PROFILE, quote=True)

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Models — @{HANDLE}</title>
<meta name="description"
 content="Public posts by @{HANDLE} on Bluesky.">
<link rel="canonical" href="{site}">
<style>
body {{
  max-width: 800px;
  margin: 35px auto;
  padding: 0 18px;
  font: 17px/1.65 Arial, sans-serif;
  color: #222;
}}
h1 {{ font-size: 28px; line-height: 1.3; }}
.post {{
  padding: 22px 0;
  border-bottom: 1px solid #ddd;
  overflow-wrap: anywhere;
}}
.post-footer {{
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 10px;
  margin-top: 12px;
  font-size: 14px;
}}
time {{ color: #777; }}
a {{ color: #0759bd; }}
</style>
</head>
<body>
<header>
<h1>AI Models — <a href="{profile}">@{HANDLE}</a></h1>
</header>
<main>
{''.join(cards)}
</main>
</body>
</html>
"""

    (OUT / "index.html").write_text(page, encoding="utf-8")

    (OUT / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n",
        encoding="utf-8"
    )

    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    root = ET.Element(f"{{{ns}}}urlset")
    entry = ET.SubElement(root, f"{{{ns}}}url")
    ET.SubElement(entry, f"{{{ns}}}loc").text = SITE_URL + "/"
    ET.SubElement(entry, f"{{{ns}}}lastmod").text = (
        datetime.now(timezone.utc).date().isoformat()
    )

    ET.ElementTree(root).write(
        OUT / "sitemap.xml",
        encoding="utf-8",
        xml_declaration=True
    )

    print(f"Обновлено публикаций: {len(posts)}")


def main():
    if "YOUR_USERNAME" in SITE_URL:
        raise ValueError("Сначала укажи свой SITE_URL в коде.")

    response = session.get(PROFILE, timeout=30)
    response.raise_for_status()

    posts = get_posts()
    build_site(posts)


if __name__ == "__main__":
    main()
