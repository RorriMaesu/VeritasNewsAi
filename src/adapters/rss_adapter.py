from .base_adapter import NewsAdapter
import feedparser
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class RSSAdapter(NewsAdapter):
    def __init__(self, config):
        self.feeds = config.get('rss_feeds', [])
        
    def fetch(self) -> list:
        items = []
        for feed_url in self.feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    items.append(self._format_entry(entry, feed_url))
            except Exception as e:
                self.handle_errors(e, feed_url)
        return items

    def _format_entry(self, entry, feed_url):
        return {
            'title': entry.get('title', 'No Title'),
            'content': entry.get('description', ''),
            'source': feed_url,
            'published_at': self._parse_date(entry),
            'url': entry.get('link', '')
        }

    def _parse_date(self, entry):
        try:
            return datetime(*entry.published_parsed[:6]).isoformat()
        except:
            return datetime.now().isoformat()

    def handle_errors(self, error: Exception, feed_url: str = ''):
        logger.error(f"RSS Error ({feed_url}): {str(error)}")
