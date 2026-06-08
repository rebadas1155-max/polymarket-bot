"""
Polymarket CLOB API Client - Real-time market data fetching
Wraps py-clob-client and adds custom query methods for arbitrage scanning
"""
import aiohttp
import asyncio
from typing import List, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)

class PolymarketClient:
    def __init__(self, base_url: str = "https://clob.polymarket.com"):
        self.base_url = base_url
        self.gamma_api = "https://gamma-api.polymarket.com"
        self.session = None

    async def init(self):
        """Initialize async HTTP session"""
        self.session = aiohttp.ClientSession()

    async def close(self):
        """Close async session"""
        if self.session:
            await self.session.close()

    async def get_markets(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Fetch all active markets from Polymarket Gamma API
        Returns list of markets with prices and order books
        """
        try:
            url = f"{self.gamma_api}/markets"
            params = {
                "limit": limit,
                "offset": offset,
                "active": "true"
            }
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data if isinstance(data, list) else []
                else:
                    logger.error(f"Failed to fetch markets: {resp.status}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return []

    async def get_market_prices(self, token_id: str) -> Optional[Dict]:
        """
        Fetch current order book and best bid/ask for a token
        """
        try:
            url = f"{self.gamma_api}/markets/{token_id}"
            async with self.session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", {})
                else:
                    return None
        except Exception as e:
            logger.error(f"Error fetching market {token_id}: {e}")
            return None

    async def get_order_book(self, token_id: str) -> Optional[Dict]:
        """
        Fetch full order book for a token (bids and asks)
        """
        try:
            url = f"{self.gamma_api}/order-book/{token_id}"
            async with self.session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", {})
                else:
                    return None
        except Exception as e:
            logger.error(f"Error fetching order book {token_id}: {e}")
            return None

    async def get_leaderboard(self, limit: int = 10, period: str = "WEEK") -> List[Dict]:
        """
        Fetch top traders/wallets from leaderboard
        Useful for wallet tracking and strategy mimicry
        """
        try:
            url = f"{self.gamma_api}/leaderboard"
            params = {
                "limit": limit,
                "period": period
            }
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", [])
                else:
                    return []
        except Exception as e:
            logger.error(f"Error fetching leaderboard: {e}")
            return []

    async def get_user_positions(self, address: str) -> List[Dict]:
        """
        Fetch all open positions for a wallet address
        """
        try:
            url = f"{self.gamma_api}/user/{address}/positions"
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", [])
                else:
                    return []
        except Exception as e:
            logger.error(f"Error fetching positions for {address}: {e}")
            return []

    async def get_user_trades(self, address: str, limit: int = 20) -> List[Dict]:
        """
        Fetch recent trades for a wallet address
        """
        try:
            url = f"{self.gamma_api}/user/{address}/trades"
            params = {"limit": limit}
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", [])
                else:
                    return []
        except Exception as e:
            logger.error(f"Error fetching trades for {address}: {e}")
            return []

    async def get_price(self, market_id: str, outcome: str = "YES") -> Optional[float]:
        """
        Fetch best ask price for a specific outcome (YES/NO)
        """
        try:
            market = await self.get_market_prices(market_id)
            if market:
                if outcome == "YES":
                    return float(market.get("yes_price", 0))
                else:
                    return float(market.get("no_price", 0))
            return None
        except Exception as e:
            logger.error(f"Error fetching price for {market_id}: {e}")
            return None

if __name__ == "__main__":
    # Test connectivity
    async def test():
        client = PolymarketClient()
        await client.init()
        
        # Fetch markets
        markets = await client.get_markets(limit=5)
        print(f"Fetched {len(markets)} markets")
        if markets:
            print(f"Sample market: {markets[0]}")
        
        await client.close()
    
    asyncio.run(test())
