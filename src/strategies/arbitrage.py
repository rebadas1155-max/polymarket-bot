"""
Arbitrage Scanner - Core Strategy 1
Scans all Polymarket markets for binary complement mispricings
Identifies opportunities where YES + NO < $0.98 (after fees)
"""
import asyncio
import logging
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)

class ArbitrageOpportunity:
    def __init__(
        self,
        market_id: str,
        market_name: str,
        yes_price: float,
        no_price: float,
        total_cost: float,
        profit_per_share: float,
        profit_pct: float,
        timestamp: datetime
    ):
        self.market_id = market_id
        self.market_name = market_name
        self.yes_price = yes_price
        self.no_price = no_price
        self.total_cost = total_cost
        self.profit_per_share = profit_per_share
        self.profit_pct = profit_pct
        self.timestamp = timestamp

    def __repr__(self):
        return (f"Arb({self.market_name[:30]} | "
                f"YES=${self.yes_price:.4f} + NO=${self.no_price:.4f} = "
                f"${self.total_cost:.4f} | Profit: {self.profit_pct:.2f}%)")

class ArbitrageScanner:
    """
    Scans Polymarket for arbitrage opportunities
    - Scan interval: 2 seconds
    - Min mispricing: YES + NO < $0.98 (after 2% taker fee)
    - Identify atomic trades on both sides
    """
    
    def __init__(self, polymarket_client, config: Dict):
        self.client = polymarket_client
        self.scan_interval = config.get("scan_interval", 2)  # seconds
        self.min_mispricing = config.get("min_mispricing", 0.02)  # $0.02 gap
        self.taker_fee = config.get("taker_fee", 0.02)  # 2% on Polymarket
        self.maker_fee = config.get("maker_fee", 0.0)  # 0% maker orders
        self.use_maker_orders = config.get("use_maker_orders", True)
        
        self.last_scan_time = None
        self.opportunities_found = 0
        self.scan_count = 0

    async def scan_all_markets(self) -> List[ArbitrageOpportunity]:
        """
        Fetch all active markets and identify arbitrage opportunities
        Returns sorted by profit percentage (highest first)
        """
        opportunities = []
        self.scan_count += 1
        
        try:
            # Fetch all markets
            markets = await self.client.get_markets(limit=500)
            
            if not markets:
                logger.warning("No markets returned from API")
                return opportunities
            
            # Scan each market for mispricings
            for market in markets:
                opp = await self._check_market(market)
                if opp:
                    opportunities.append(opp)
            
            # Sort by profit percentage (highest first)
            opportunities.sort(key=lambda x: x.profit_pct, reverse=True)
            
            self.opportunities_found += len(opportunities)
            self.last_scan_time = datetime.now()
            
            logger.info(
                f"Scan #{self.scan_count}: Found {len(opportunities)} opportunities "
                f"from {len(markets)} markets"
            )
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error scanning markets: {e}")
            return opportunities

    async def _check_market(self, market: Dict) -> Optional[ArbitrageOpportunity]:
        """
        Check if a single market has an arbitrage opportunity
        Returns ArbitrageOpportunity if YES + NO < break-even threshold
        """
        try:
            market_id = market.get("id")
            market_name = market.get("question", "Unknown")
            
            # Get current prices from outcomePrices array [YES, NO]
            outcome_prices = market.get("outcomePrices", [])
            if isinstance(outcome_prices, str):
                # Handle case where it's a string representation of array
                import json
                try:
                    outcome_prices = json.loads(outcome_prices)
                except:
                    outcome_prices = []
            
            if len(outcome_prices) >= 2:
                yes_price = float(outcome_prices[0])
                no_price = float(outcome_prices[1])
            else:
                # Fallback: try bestAsk/BestBid if available
                yes_price = float(market.get("bestAsk", 0))  # YES is typically bestAsk
                no_price = float(market.get("bestBid", 0))   # NO is typically bestBid
                # Alternative: if we have bestAsk for YES, NO price is 1 - YES price
                if yes_price > 0 and no_price == 0:
                    no_price = 1.0 - yes_price
            
            if yes_price <= 0 or no_price <= 0:
                return None
            
            # Calculate total cost
            total_cost_raw = yes_price + no_price
            
            # Apply fee (if using taker orders)
            if not self.use_maker_orders:
                # Taker fee increases effective cost
                total_cost = total_cost_raw * (1 + self.taker_fee)
            else:
                # Maker orders: no fee
                total_cost = total_cost_raw
            
            # Check if arbitrage exists (total cost < $1.00)
            profit_per_share = 1.0 - total_cost
            profit_pct = (profit_per_share / total_cost) * 100 if total_cost > 0 else 0
            
            # Only flag if profit exceeds minimum threshold
            if profit_per_share >= self.min_mispricing / 100:
                return ArbitrageOpportunity(
                    market_id=market_id,
                    market_name=market_name,
                    yes_price=yes_price,
                    no_price=no_price,
                    total_cost=total_cost,
                    profit_per_share=profit_per_share,
                    profit_pct=profit_pct,
                    timestamp=datetime.now()
                )
            
            return None
            
        except Exception as e:
            logger.debug(f"Error checking market: {e}")
            return None

    async def run_continuous_scan(self, callback=None):
        """
        Run continuous market scanning loop
        Calls callback with opportunities every scan interval
        """
        logger.info(
            f"Starting continuous arbitrage scan "
            f"(interval={self.scan_interval}s, min_gap={self.min_mispricing})"
        )
        
        while True:
            try:
                opportunities = await self.scan_all_markets()
                
                if callback and opportunities:
                    await callback(opportunities)
                
                await asyncio.sleep(self.scan_interval)
                
            except Exception as e:
                logger.error(f"Error in continuous scan loop: {e}")
                await asyncio.sleep(self.scan_interval)

    def get_stats(self) -> Dict:
        """Return scanner statistics"""
        return {
            "total_scans": self.scan_count,
            "total_opportunities": self.opportunities_found,
            "avg_per_scan": (
                self.opportunities_found / self.scan_count 
                if self.scan_count > 0 else 0
            ),
            "last_scan_time": self.last_scan_time
        }
