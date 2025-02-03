import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import feedparser
from gnews import GNews
import hashlib
import pytz
import time
import re
from urllib.parse import urljoin

import praw
from dotenv import load_dotenv
from dateutil import parser
import ollama
from ollama import Client

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)  # Ensure debug logs are captured

class NewsAggregator:
    """
    Aggregates news from Google News, RSS feeds, and Reddit.
    Filters out duplicates and outdated items.
    Uses DeepSeek to rank and pick top 9 stories.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.language = config.get('language', 'en')
        self.country = config.get('country', 'US')
        self.max_age_hours = config.get('max_age_hours', 24)  # Increased to 24 hours
        self.gnews_period = config.get('update_interval', '24h')  # Updated to match max_age_hours
        self.max_results = config.get('max_results', 50)

        # Folders
        base_dir = os.path.join(os.path.dirname(__file__), '..')
        self.news_dir = os.path.join(base_dir, 'data', 'news')
        os.makedirs(self.news_dir, exist_ok=True)
        self.top_news_dir = os.path.join(base_dir, 'data', 'top_news')
        os.makedirs(self.top_news_dir, exist_ok=True)

        # GNews
        self.gnews_client = GNews(
            language=self.language,
            country=self.country,
            period=self.gnews_period,
            max_results=self.max_results
        )

        self.seen_hashes = set()
        self.utc_timezone = pytz.utc
        self._load_seen_hashes()

        # Reddit
        reddit_id = os.getenv("REDDIT_CLIENT_ID")
        reddit_secret = os.getenv("REDDIT_CLIENT_SECRET")
        if reddit_id and reddit_secret:
            try:
                self.reddit = praw.Reddit(
                    client_id=reddit_id,
                    client_secret=reddit_secret,
                    user_agent=config.get('reddit_user_agent', 'AutoNewsChannel/2.0')
                )
                logger.info("Reddit client initialized.")
            except Exception as e:
                logger.warning(f"Could not initialize Reddit client: {e}")
                self.reddit = None
        else:
            logger.info("Reddit credentials not found in environment. Skipping Reddit fetch.")
            self.reddit = None

        # DeepSeek local model for picking top stories
        self.deepseek_client = Client()
        self.deepseek_model = config.get('deepseek_model', 'deepseek-r1')

    def _load_seen_hashes(self):
        """Load previously saved news hashes to skip duplicates."""
        hash_file = self.config.get('hash_file', './data/seen_hashes.json')
        try:
            with open(hash_file, 'r', encoding='utf-8') as f:
                self.seen_hashes = set(json.load(f))
            logger.info(f"Loaded {len(self.seen_hashes)} seen hashes.")
        except (FileNotFoundError, json.JSONDecodeError):
            logger.info("No existing seen_hashes found. Starting fresh.")
        except Exception as e:
            logger.error(f"Error loading seen hashes: {e}")

    def _save_seen_hashes(self):
        """Save updated seen hashes after aggregation completes."""
        hash_file = self.config.get('hash_file', './data/seen_hashes.json')
        try:
            os.makedirs(os.path.dirname(hash_file), exist_ok=True)
            with open(hash_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.seen_hashes), f, indent=2)
            logger.info(f"Saved {len(self.seen_hashes)} seen hashes.")

            # Manage the size of seen_hashes to prevent excessive growth
            self._manage_seen_hashes(max_size=1000)

        except Exception as e:
            logger.error(f"Error saving seen hashes: {e}")

    def _manage_seen_hashes(self, max_size: int = 1000):
        """
        Ensures that the seen_hashes set does not exceed max_size.
        Removes the oldest hashes if necessary.
        """
        if len(self.seen_hashes) > max_size:
            # Convert set to list to remove the oldest entries
            seen_list = list(self.seen_hashes)
            # Remove the oldest entries
            seen_list = seen_list[-max_size:]
            self.seen_hashes = set(seen_list)
            logger.info(f"Managed seen_hashes to contain only the latest {max_size} entries.")

    def _parse_datetime(self, datestr: str) -> Optional[datetime]:
        """Parse string into timezone-aware datetime object (UTC), or None if fails."""
        try:
            if re.fullmatch(r'\d+(\.\d+)?', datestr):
                dt = datetime.utcfromtimestamp(float(datestr)).replace(tzinfo=self.utc_timezone)
            else:
                dt = parser.parse(datestr)
                if not dt.tzinfo:
                    dt = dt.replace(tzinfo=self.utc_timezone)
                dt = dt.astimezone(self.utc_timezone)
            return dt
        except Exception as e:
            logger.debug(f"Failed to parse date '{datestr}': {e}")
            return None

    def _hash_item(self, item: Dict) -> str:
        """Generate a unique hash from title, description, and link."""
        title = item.get('title', '').lower().strip()
        desc = item.get('description', '').lower().strip()
        link = item.get('link', '').lower().strip()
        combo = f"{title} {desc} {link}"
        return hashlib.sha256(combo.encode('utf-8')).hexdigest()

    def _filter_news(self, items: List[Dict]) -> List[Dict]:
        """Remove duplicates and items older than 'max_age_hours'."""
        cutoff = datetime.now(tz=self.utc_timezone) - timedelta(hours=self.max_age_hours)
        filtered = []
        old_count = 0
        duplicate_count = 0
        missing_date_count = 0

        for it in items:
            pub_str = it.get('published date', '')
            dt_obj = self._parse_datetime(pub_str)
            if not dt_obj:
                missing_date_count += 1
                continue
            if dt_obj < cutoff:
                old_count += 1
                continue
            c_hash = self._hash_item(it)
            if c_hash in self.seen_hashes:
                duplicate_count += 1
                continue
            self.seen_hashes.add(c_hash)
            filtered.append(it)

        logger.info(f"Filtered news: {old_count} old, {duplicate_count} duplicates, {missing_date_count} missing dates.")
        logger.info(f"{len(filtered)} items remain after filtering.")
        return filtered

    def fetch_gnews(self) -> List[Dict]:
        """Fetch news from Google News."""
        try:
            data = self.gnews_client.get_news_by_topic('WORLD') or []
            out = []
            for d in data:
                out.append({
                    'title': d.get('title', ''),
                    'description': d.get('description', ''),
                    'link': d.get('url', ''),
                    'published date': d.get('published_date', ''),
                    'source': 'GoogleNews'
                })
            logger.info(f"Fetched {len(out)} from GNews (WORLD).")
            return out
        except Exception as e:
            logger.error(f"GNews fetch error: {e}")
            return []

    def fetch_rss_feeds(self) -> List[Dict]:
        """Fetch news from RSS feeds."""
        items = []
        for feed_url in self.config.get('rss_feeds', []):
            try:
                fd = feedparser.parse(feed_url)
                entry_count = 0
                for entry in fd.entries:
                    dt_str = entry.get('published') or entry.get('updated', '')
                    dt_obj = self._parse_datetime(dt_str)
                    if not dt_obj and hasattr(entry, 'published_parsed') and entry.published_parsed:
                        dt_obj = datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=self.utc_timezone)
                    if not dt_obj and hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        dt_obj = datetime.fromtimestamp(time.mktime(entry.updated_parsed), tz=self.utc_timezone)
                    if not dt_obj:
                        continue
                    items.append({
                        'title': entry.get('title', ''),
                        'description': entry.get('description', ''),
                        'link': entry.get('link', ''),
                        'published date': dt_obj.isoformat(),
                        'source': feed_url
                    })
                    entry_count += 1
                logger.info(f"Fetched {entry_count} entries from RSS feed: {feed_url}")
            except Exception as e:
                logger.error(f"RSS fetch error for {feed_url}: {e}")
        return items

    def fetch_reddit_news(self) -> List[Dict]:
        """Fetch news from Reddit subreddits."""
        if not self.reddit:
            logger.info("Reddit client not initialized. Skipping Reddit fetch.")
            return []
        items = []
        for sub in self.config.get('reddit_subreddits', []):
            try:
                limit = self.config.get('reddit_limit', 15)
                submissions = self.reddit.subreddit(sub).hot(limit=limit)
                cnt = 0
                for post in submissions:
                    dt_obj = datetime.utcfromtimestamp(post.created_utc).replace(tzinfo=self.utc_timezone)
                    items.append({
                        'title': post.title,
                        'description': post.selftext,
                        'link': post.url,
                        'published date': dt_obj.isoformat(),
                        'source': f"reddit.com/r/{sub}"
                    })
                    cnt += 1
                logger.info(f"Fetched {cnt} posts from Reddit subreddit: r/{sub}")
            except Exception as e:
                logger.error(f"Reddit fetch error for r/{sub}: {e}")
        return items

    def aggregate_news(self) -> List[Dict]:
        """
        1. Fetch news from GNews, RSS feeds, and Reddit.
        2. Filter out duplicates and outdated items.
        3. Save all filtered news to data/news.
        4. Return the final list of news items.
        """
        logger.info("Starting news aggregation.")
        all_gnews = self.fetch_gnews()
        all_rss = self.fetch_rss_feeds()
        all_reddit = self.fetch_reddit_news()
        combined = all_gnews + all_rss + all_reddit
        logger.info(f"Combined total {len(combined)} news items before filtering.")
        filtered = self._filter_news(combined)
        logger.info(f"{len(filtered)} news items remain after filtering.")

        # Save all filtered news with timestamp
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        all_news_file = os.path.join(self.news_dir, f"all_news_{ts}.json")
        try:
            with open(all_news_file, 'w', encoding='utf-8') as f:
                json.dump(filtered, f, indent=2)
            logger.info(f"Saved all filtered news to {all_news_file}")
        except Exception as e:
            logger.error(f"Failed to save all_news file: {e}")

        # Save updated seen hashes
        self._save_seen_hashes()
        return filtered

    def pick_top_stories(self, items: List[Dict], count: int = 9) -> List[Dict]:
        """
        Use DeepSeek to rank news items by importance and entertainment.
        Pick the top 'count' stories and save them to data/top_news.
        """
        if not items:
            logger.warning("No news items available for picking top stories.")
            return []

        # Ensure there are enough stories to pick
        available_count = len(items)
        if available_count < count:
            logger.warning(f"Only {available_count} stories available. Expected {count}. Proceeding with available stories.")
            count = available_count

        # Build prompt for DeepSeek
        prompt_lines = []
        for i, it in enumerate(items, 1):
            prompt_lines.append(f"""STORY {i}:
Title: {it.get('title', 'No Title')}
Description: {it.get('description', 'No Description')}

""")

        ranking_prompt = f"""We have {len(items)} news stories. For each story, assign:
- Importance score (0-10)
- Entertainment score (0-10)
- Combined rating (0-100)

Provide a short reasoning for each assignment.

Format EXACTLY:

STORY X
Importance: #
Entertainment: #
Combined: #
Reasoning: ...
STORY X
...
"""

        full_prompt = ranking_prompt + "\n".join(prompt_lines)

        # Call DeepSeek
        try:
            logger.info("Calling DeepSeek to rank news stories.")
            resp = self.deepseek_client.generate(
                model=self.deepseek_model,
                prompt=full_prompt,
                stream=False
            )
            if 'response' not in resp:
                logger.error("DeepSeek pick_top_stories missing 'response' key.")
                return []
            raw_response = resp['response']
            logger.debug(f"DeepSeek raw response:\n{raw_response}")  # Added for debugging
        except Exception as e:
            logger.error(f"DeepSeek error during ranking: {e}")
            return []

        # Parse DeepSeek response
        lines = raw_response.split("\n")
        parse_map = {}
        current = None
        for ln in lines:
            l = ln.strip()
            if l.startswith("STORY "):
                if current:
                    parse_map[current["idx"]] = current
                m = re.match(r"STORY\s+(\d+)", l)
                if m:
                    idx = int(m.group(1))
                    current = {"idx": idx, "scores": {}}
            elif ":" in l and current:
                kv = l.split(":", 1)
                if len(kv) == 2:
                    k = kv[0].strip().lower()
                    v = kv[1].strip()
                    if k in ["importance", "entertainment", "combined"]:
                        try:
                            current["scores"][k] = float(v)
                        except:
                            current["scores"][k] = 0
                    elif k == "reasoning":
                        current["reasoning"] = v
        if current:
            parse_map[current["idx"]] = current

        # Assign scores to items
        scored_items = []
        for i, item in enumerate(items, 1):
            if i in parse_map:
                c_score = parse_map[i]["scores"].get("combined", 0)
                item["deepseek_ranking"] = {
                    "importance": parse_map[i]["scores"].get("importance", 0),
                    "entertainment": parse_map[i]["scores"].get("entertainment", 0),
                    "combined": c_score,
                    "reasoning": parse_map[i].get("reasoning", "")
                }
                scored_items.append(item)
            else:
                # Handle missing ranking data
                item["deepseek_ranking"] = {
                    "importance": 0,
                    "entertainment": 0,
                    "combined": 0,
                    "reasoning": "No ranking data"
                }
                scored_items.append(item)

        # Sort by combined score descending
        scored_items.sort(key=lambda x: x["deepseek_ranking"]["combined"], reverse=True)
        picked = scored_items[:count]

        # Save top stories
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        top_file = os.path.join(self.top_news_dir, f"top_stories_{ts}.json")
        try:
            with open(top_file, 'w', encoding='utf-8') as f:
                json.dump(picked, f, indent=2)
            logger.info(f"Saved top {count} stories to {top_file}")
        except Exception as e:
            logger.error(f"Failed to save top_stories file: {e}")

        return picked
