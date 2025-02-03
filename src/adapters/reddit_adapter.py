from .base_adapter import NewsAdapter
import praw

class RedditAdapter(NewsAdapter):
    def __init__(self, config):
        self.client = praw.Reddit(
            client_id=config['client_id'],
            client_secret=config['client_secret'],
            user_agent=config['user_agent']
        )
        
    def fetch(self) -> list:
        try:
            submissions = self.client.subreddit('worldnews').hot(limit=10)
            return [self._format_post(post) for post in submissions]
        except Exception as e:
            self.handle_errors(e)
            return []
            
    def _format_post(self, post):
        return {
            'title': post.title,
            'content': post.selftext,
            'source': 'reddit',
            'published_at': post.created_utc,
            'url': post.url
        }
        
    def handle_errors(self, error: Exception):
        logger.error(f"Reddit API error: {str(error)}")
