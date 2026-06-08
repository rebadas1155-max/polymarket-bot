import aiohttp
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class MetaculusClient:
    def __init__(self):
        # Metaculus API base URL (this is a common pattern for their API, though may need adjustment)
        self.base_url = "https://www.metaculus.com/api2"
        self.session = None

    async def init(self):
        """Initialize async HTTP session"""
        self.session = aiohttp.ClientSession()

    async def close(self):
        """Close async session"""
        if self.session:
            await self.session.close()

    async def get_questions(self, query: str = "", limit: int = 10) -> List[Dict]:
        """
        Search for Metaculus questions based on a query.
        """
        if not self.session:
            logger.debug("Metaculus client not initialized.")
            return []

        endpoint = f"{self.base_url}/questions"
        params = {
            "search": query,
            "limit": limit,
            "order_by": "-publish_time" # Order by most recent
        }

        try:
            async with self.session.get(endpoint, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("results", [])
                else:
                    logger.error(f"Failed to fetch Metaculus questions (status {resp.status}): {await resp.text()}")
                    return []
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching Metaculus questions: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching Metaculus questions: {e}", exc_info=True)
            return []

    async def get_forecast(self, question_id: int) -> Optional[Dict]:
        """
        Get the community forecast for a specific question ID.
        """
        if not self.session:
            logger.debug("Metaculus client not initialized.")
            return None

        endpoint = f"{self.base_url}/questions/{question_id}/forecast"

        try:
            async with self.session.get(endpoint, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.warning(f"Failed to fetch Metaculus forecast for question {question_id} (status {resp.status}): {await resp.text()}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching Metaculus forecast: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching Metaculus forecast: {e}", exc_info=True)
            return None
