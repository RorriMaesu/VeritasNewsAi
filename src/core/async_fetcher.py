import aiohttp
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class AsyncFetcher:
    def __init__(self, timeout: int = 10):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        
    async def fetch(self, session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
        try:
            async with session.get(url, timeout=self.timeout) as response:
                logger.debug(f"Fetching {url} - Status {response.status}")
                return {
                    "url": url,
                    "status": response.status,
                    "content": await response.json(),
                    "error": None
                }
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {str(e)}")
            return {
                "url": url,
                "status": 500,
                "content": None,
                "error": str(e)
            } 