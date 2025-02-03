from abc import ABC, abstractmethod
from typing import List, Dict

class NewsAdapter(ABC):
    @abstractmethod
    def fetch(self) -> List[Dict]:
        """Return standardized news items:
        [{
            "title": str,
            "content": str,
            "source": str,
            "published_at": datetime,
            "url": str
        }]
        """
        pass

    @abstractmethod
    def handle_errors(self, error: Exception):
        """Adapter-specific error handling"""
        pass 