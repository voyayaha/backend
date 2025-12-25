import os
import httpx
import praw
from dotenv import load_dotenv
from urllib.parse import quote_plus
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# ENV
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

if not all([YOUTUBE_API_KEY, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT]):
    raise EnvironmentError("Missing environment variables")

# Reddit client
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# REDDIT
# -----------------------------
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
            "image": image,
            "url": f"https://www.reddit.com{post.permalink}"
        })

    return results


# -----------------------------
# YOUTUBE
# -----------------------------
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
                "image": s["thumbnails"]["medium"]["url"],
                "url": f"https://www.youtube.com/watch?v={vid}"
            })

        return results


# -----------------------------
# SOCIAL ENDPOINT
# -----------------------------
@app.get("/social")
async def social(location: str = "Mumbai", limit: int = 5):
    reddit_posts = await get_reddit_posts(location, limit)
    youtube_posts = await get_youtube_posts(location, limit)
    return youtube_posts + reddit_posts


# -----------------------------
# TRENDING SPOTS
# -----------------------------
@app.get("/trends")
async def trends(location: str = "Pune"):
    query = f"{location} travel OR {location} places OR {location} itinerary"
    return await get_reddit_posts(query, limit=8)
