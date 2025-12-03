"""
Lightweight, legal scrape of public Reddit search results.
No login, no API key: just Reddit’s JSON endpoint.
"""
import httpx
from urllib.parse import quote_plus
import os
import praw  # <-- ADD THIS
from dotenv import load_dotenv


load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Load environment vars
REDDIT_CLIENT_ID     = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT    = os.getenv("REDDIT_USER_AGENT")

# Reddit client
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

if not YOUTUBE_API_KEY:
    raise EnvironmentError("YOUTUBE_API_KEY not found. Check your .env file.")


HEADERS = {"User-Agent": "ai-concierge-prototype/0.2"}

async def scrape_social(query: str, limit: int = 5):
    """Combines Reddit posts and YouTube Shorts for a given keyword."""
    from asyncio import gather

    reddit = await get_reddit_posts(query, limit)
    youtube = await scrape_youtube(query, limit)

    # Merge and sort by source priority or score
    return youtube + reddit

async def scrape_reddit(query: str, limit: int = 5):
    url = f"https://www.reddit.com/search.json?q={quote_plus(query)}&sort=top&t=year&limit={limit}"
    async with httpx.AsyncClient(headers=HEADERS, timeout=10) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()
        results = []
        for child in data.get("data", {}).get("children", []):
            post = child["data"]
            results.append({
                "type": "reddit",
                "title": post["title"],
                "url": f"https://www.reddit.com{post['permalink']}",
                "score": post["score"],
                "subreddit": post["subreddit"]
            })
        return results[:limit]
        
async def get_reddit_posts(query: str, limit: int = 5):
    results = []
    for submission in reddit.subreddit("travel").search(query, limit=limit, sort="relevance"):
        results.append({
            "source": "Reddit",
            "title": submission.title,
            "url": submission.url,
            "thumbnail": submission.thumbnail if submission.thumbnail.startswith("http") else None

        })
    return results


async def scrape_youtube(query: str, limit: int = 5):
    q = quote_plus(query)
    url = (
        "https://www.googleapis.com/youtube/v3/search"
        f"?part=snippet&q={q}&type=video&videoDuration=short&maxResults={limit}&key={YOUTUBE_API_KEY}"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()
        results = []
        for item in data.get("items", []):
            vid = item["id"]["videoId"]
            results.append({
                "type": "youtube",
                "title": item["snippet"]["title"],
                "url": f"https://www.youtube.com/watch?v={vid}",
                "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
                "channel": item["snippet"]["channelTitle"]
            })
        return results


async def get_trending_spots(city: str):
    all_posts = await get_reddit_posts(f"{city} travel OR {city} places OR {city} itinerary", 20)
    filtered = [
        post for post in all_posts
        if city.lower() in post['title'].lower() or city.lower() in post.get('selftext', '').lower()
    ]
    return filtered[:10]  # return top 10 relevant


