import aiohttp
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class TwitterClient:
    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
        self.base_url = "https://api.twitter.com/2"
        self.session = None

    async def init(self):
        """Initialize async HTTP session"""
        if not self.bearer_token or self.bearer_token == "your_twitter_bearer_token":
            logger.warning("Twitter bearer token not set. Twitter client will not be active.")
            return
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.bearer_token}"}
        )

    async def close(self):
        """Close async session"""
        if self.session:
            await self.session.close()

    async def search_tweets(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for recent tweets based on a query.
        Requires 'tweet.fields=created_at,author_id,text' in params for full tweet data.
        """
        if not self.session:
            logger.debug("Twitter client not initialized, skipping tweet search.")
            return []

        endpoint = f"{self.base_url}/tweets/search/recent"
        params = {
            "query": query,
            "max_results": limit,
            "tweet.fields": "created_at,author_id,text",
            "expansions": "author_id",
            "user.fields": "username"
        }

        try:
            async with self.session.get(endpoint, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    tweets = []
                    users = {user["id"]: user for user in data.get("includes", {}).get("users", [])}

                    for tweet in data.get("data", []):
                        author = users.get(tweet["author_id"], {})
                        tweets.append({
                            "id": tweet["id"],
                            "text": tweet["text"],
                            "created_at": tweet["created_at"],
                            "author_id": tweet["author_id"],
                            "username": author.get("username", "Unknown"),
                            "source": "twitter"
                        })
                    return tweets
                else:
                    logger.error(f"Failed to search tweets (status {resp.status}): {await resp.text()}")
                    return []
        except aiohttp.ClientError as e:
            logger.error(f"Network error while searching tweets: {e}")
            return []
        except Exception as e:
            logger.error(f"Error searching tweets: {e}", exc_info=True)
            return []
