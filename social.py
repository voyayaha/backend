import os
import httpx
import praw
from dotenv import load_dotenv
from urllib.parse import quote_plus
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

load_dotenv()

# --------------------------------------------------
# CONFIG
# --------------------------------------------------



YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

if not API_BASE:
    raise EnvironmentError("API_BASE not set (example: https://your-backend-domain)")

if not all([YOUTUBE_API_KEY, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT]):
    raise EnvironmentError("Missing environment variables")

# --------------------------------------------------
# REDDIT CLIENT
# --------------------------------------------------

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

# --------------------------------------------------
# FASTAPI APP
# --------------------------------------------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# IMAGE PROXY (CRITICAL FIX)
# --------------------------------------------------

@app.get("/img")
async def proxy_image(url: str):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        return Response(
            content=r.content,
            media_type=r.headers.get("content-type", "image/jpeg")
        )

def proxify(url: str | None):
    if not url:
        return None
    return f"{API_BASE}/img?url={quote_plus(url)}"

# --------------------------------------------------
# REDDIT
# --------------------------------------------------

async def get_reddit_posts(query: str, limit: int = 5):
    results = []

    for post in reddit.subreddit("travel").search(query, limit=limit, sort="relevance"):
        image = None

        if hasattr(post, "preview"):
            imgs = post.preview.get("images", [])
            if imgs:
                image = imgs[0]["source"]["url"]

        if not image and post.thumbnail and post.thumbnail.startswith("http"):
            image = post.thumbnail

        results.append({
            "source": "reddit",
            "title": post.title,
            "description": post.selftext[:200] if post.selftext else f"From r/{post.subreddit}",
            "image": proxify(image),
            "url": f"https://www.reddit.com{post.permalink}"
        })

    return results

# --------------------------------------------------
# YOUTUBE
# --------------------------------------------------

async def get_youtube_posts(query: str, limit: int = 5):
    q = quote_plus(query)
    url = (
        "https://www.googleapis.com/youtube/v3/search"
        f"?part=snippet&type=video&maxResults={limit}"
        f"&q={q}&key={YOUTUBE_API_KEY}"
    )

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()

        results = []
        for item in data.get("items", []):
            s = item["snippet"]
            vid = item["id"]["videoId"]

            results.append({
                "source": "youtube",
                "title": s["title"],
                "description": s["description"][:200],
                "image": proxify(s["thumbnails"]["medium"]["url"]),
                "url": f"https://www.youtube.com/watch?v={vid}"
            })

        return results

