
import html
import re
import requests
import xml.etree.ElementTree as ET

from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote

HANDLE = "ai-models.bsky.social"
PROFILE = f"https://bsky.app/profile/{HANDLE}"

# Адрес твоего GitHub Pages
SITE_URL = "https://ihoneylady95.github.io/bluesky-catalog".rstrip("/")

API = "https://public.api.bsky.app/xrpc"

OUT = Path(".")
POSTS_DIR = OUT / "posts"

GOOGLE_VERIFICATION = (
    "aeP5xq_dlUrhm_si1vi44UAUnbLv-mXyG4nIa3u8GFY"
)

session = requests.Session()
session.headers["User-Agent"] = "AIModelsBlueskyCatalog/2.0"


def get_posts():
    posts = {}
    cursor = None

    while True:
        params = {
            "actor": HANDLE,
            "limit": 100
        }

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

            # Пропускаем чужие репосты
            if author.get("handle", "").lower() != HANDLE.lower():
                continue

            uri = post.get("uri", "")
            rkey = uri.rsplit("/", 1)[-1]

            if not rkey:
                continue

            record = post.get("record", {})
            text = record.get("text", "")

            if not text.strip():
                continue

            url = f"{PROFILE}/post/{rkey}"

            posts[rkey] = {
                "rkey": rkey,
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


def format_date(value):
    try:
        dt = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return datetime.now(timezone.utc).date().isoformat()


def make_html(title, description, canonical, content):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<meta name="google-site-verification"
content="{GOOGLE_VERIFICATION}">

<title>{html.escape(title)}</title>
<meta name="description"
content="{html.escape(description[:250], quote=True)}">

<link rel="canonical"
href="{html.escape(canonical, quote=True)}">

<meta property="og:title"
content="{html.escape(title, quote=True)}">
<meta property="og:description"
content="{html.escape(description[:250], quote=True)}">
<meta property="og:type" content="article">
<meta property="og:url"
content="{html.escape(canonical, quote=True)}">

<style>
body {{
    max-width: 800px;
    margin: 35px auto;
    padding: 0 18px;
    font: 17px/1.7 Arial, sans-serif;
    color: #222;
}}
h1 {{
    font-size: 28px;
    line-height: 1.35;
}}
.post {{
    padding: 20px 0;
    border-bottom: 1px solid #ddd;
    overflow-wrap: anywhere;
}}
.post-footer {{
    margin-top: 15px;
    font-size: 14px;
}}
time {{
    color: #777;
}}
a {{
    color: #0759bd;
}}
.back {{
    display: inline-block;
    margin-bottom: 25px;
}}
</style>
</head>
<body>
{content}
</body>
</html>"""


def build_post_pages(posts):
    sitemap_urls = []

    POSTS_DIR.mkdir(exist_ok=True)

    for post in posts:
        rkey = post["rkey"]

        # У каждой публикации собственная папка
        post_dir = POSTS_DIR / rkey
        post_dir.mkdir(parents=True, exist_ok=True)

        page_url = f"{SITE_URL}/posts/{quote(rkey, safe='')}/"

        title = post["text"].strip().split("\n")[0]
        if len(title) > 100:
            title = title[:97] + "..."

        if not title:
            title = f"AI Models — {rkey}"

        description = post["text"].strip()

        post_text = html.escape(
            post["text"]
        ).replace("\n", "<br>\n")

        bluesky_url = html.escape(
            post["url"],
            quote=True
        )

        date = format_date(post["date"])

        content = f"""
<a class="back" href="{SITE_URL}/">
← All publications
</a>

<h1>{html.escape(title)}</h1>

<article class="post">
    <div>{post_text}</div>

    <div class="post-footer">
        <time datetime="{date}">{date}</time>
        <br>
        <a href="{bluesky_url}"
           target="_blank"
           rel="noopener noreferrer">
           View original post on Bluesky
        </a>
    </div>
</article>
"""

        page = make_html(
            title,
            description,
            page_url,
            content
        )

        (post_dir / "index.html").write_text(
            page,
            encoding="utf-8"
        )

        sitemap_urls.append((page_url, date))

    return sitemap_urls


def build_homepage(posts):
    cards = []

    for post in posts:
        rkey = post["rkey"]

        page_url = (
            f"{SITE_URL}/posts/{quote(rkey, safe='')}/"
        )

        title = post["text"].strip().split("\n")[0]

        if len(title) > 150:
            title = title[:147] + "..."

        if not title:
            title = "Bluesky publication"

        date = format_date(post["date"])

        cards.append(f"""
<article class="post">
    <h2>
      <a href="{html.escape(page_url, quote=True)}">
        {html.escape(title)}
      </a>
    </h2>
    <time datetime="{date}">{date}</time>
    <p>
      <a href="{html.escape(post["url"], quote=True)}">
        View original on Bluesky
      </a>
    </p>
</article>
""")

    profile = html.escape(PROFILE, quote=True)

    content = f"""
<header>
<h1>AI Models — <a href="{profile}">@{HANDLE}</a></h1>
</header>
<main>
{''.join(cards)}
</main>
"""

    page = make_html(
        f"AI Models — @{HANDLE}",
        f"Public publications by @{HANDLE} on Bluesky.",
        SITE_URL + "/",
        content
    )

    (OUT / "index.html").write_text(
        page,
        encoding="utf-8"
    )


def build_robots():
    (OUT / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n",
        encoding="utf-8"
    )


def build_sitemap(posts, post_urls):
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"

    ET.register_namespace("", ns)

    root = ET.Element(f"{{{ns}}}urlset")

    all_urls = [
        (
            SITE_URL + "/",
            datetime.now(timezone.utc).date().isoformat()
        )
    ] + post_urls

    for url, date in all_urls:
        entry = ET.SubElement(root, f"{{{ns}}}url")

        ET.SubElement(
            entry,
            f"{{{ns}}}loc"
        ).text = url

        ET.SubElement(
            entry,
            f"{{{ns}}}lastmod"
        ).text = date

    ET.ElementTree(root).write(
        OUT / "sitemap.xml",
        encoding="utf-8",
        xml_declaration=True
    )


def main():
    if not SITE_URL.startswith("https://"):
        raise ValueError("Неправильный SITE_URL")

    response = session.get(PROFILE, timeout=30)
    response.raise_for_status()

    print("Получение публикаций Bluesky...")

    posts = get_posts()

    print(f"Найдено публикаций: {len(posts)}")

    post_urls = build_post_pages(posts)

    build_homepage(posts)
    build_robots()
    build_sitemap(posts, post_urls)

    print("Главная страница обновлена.")
    print(f"Создано HTML-страниц: {len(post_urls)}")
    print(f"Всего URL в sitemap: {len(post_urls) + 1}")
    print("Готово!")


if __name__ == "__main__":
    main()
