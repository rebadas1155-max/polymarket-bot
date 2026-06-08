"""
Main Bot Engine - Orchestrates all components
Runs: Polymarket API polling + Arbitrage scanner + TUI + Telegram
Manages demo bankroll and enforces risk limits
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
import os

from src.core.polymarket_client import PolymarketClient
from src.strategies.arbitrage import ArbitrageScanner
from src.risk.ledger import DemoBankroll, Trade
from src.core.logger import log

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('arb_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotEngine:
    """
    Main bot engine
    - Polls Polymarket API continuously
    - Detects arbitrage opportunities
    - Executes demo trades
    - Tracks P&L via ledger
    - Sends updates to TUI/Telegram
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.mode = config.get("mode", "DEMO")  # DEMO or REAL
        self.bankroll = DemoBankroll(config.get("initial_capital", 50.0))
        self.polymarket_client = PolymarketClient()
        
        # Arbitrage scanner config
        scanner_config = {
            "scan_interval": config.get("scan_interval", 2),
            "min_mispricing": config.get("min_mispricing", 0.02),
            "taker_fee": 0.02,
            "maker_fee": 0.0,
            "use_maker_orders": True
        }
        self.scanner = ArbitrageScanner(self.polymarket_client, scanner_config)
        
        # State
        self.is_running = False
        self.is_paused = False
        self.opportunities_log: List[Dict] = []
        self.execution_log: List[str] = []
        self.last_execution_time = None
        
        # Wallet tracking (for strategy 2 & 3)
        self.top_wallets = []
        self.wallet_update_interval = 3600  # 1 hour
        self.last_wallet_update = None

    async def initialize(self):
        """Initialize async components"""
        logger.info(f"Initializing bot engine (mode={self.mode})")
        await self.polymarket_client.init()
        logger.info("Polymarket client initialized")

    async def start(self):
        """Start bot operations"""
        if self.is_running:
            logger.warning("Bot is already running")
            return
        
        self.is_running = True
        logger.info(f"Starting bot (DEMO mode, capital=${self.bankroll.initial_capital})")
        
        # Start main async tasks
        await asyncio.gather(
            self._scan_loop(),
            self._wallet_tracking_loop(),
            self._stats_reporter_loop()
        )

    def pause(self):
        """Pause trading"""
        self.is_paused = True
        self._log("🛑 Trading paused")

    def resume(self):
        """Resume trading"""
        self.is_paused = False
        self._log("▶️ Trading resumed")

    def stop(self):
        """Stop bot"""
        self.is_running = False
        self._log("Bot stopped")

    async def _scan_loop(self):
        """Continuous market scanning"""
        logger.info(f"Starting scan loop (interval={self.scanner.scan_interval}s)")
        
        while self.is_running:
            try:
                if not self.is_paused:
                    # Scan for arbitrage opportunities
                    opportunities = await self.scanner.scan_all_markets()
                    
                    if opportunities:
                        # Log opportunities
                        for opp in opportunities:
                            self.opportunities_log.append({
                                "timestamp": datetime.now().isoformat(),
                                "market": opp.market_name,
                                "yes_price": round(opp.yes_price, 4),
                                "no_price": round(opp.no_price, 4),
                                "total_cost": round(opp.total_cost, 4),
                                "profit_pct": round(opp.profit_pct, 2)
                            })
                        
                        # Execute top opportunity if profitable enough
                        if opportunities[0].profit_pct >= 1.0:  # At least 1% profit
                            await self._execute_arbitrage(opportunities[0])
                        
                        # Keep only last 100 opportunities
                        self.opportunities_log = self.opportunities_log[-100:]
                
                await asyncio.sleep(self.scanner.scan_interval)
                
            except Exception as e:
                logger.error(f"Error in scan loop: {e}")
                await asyncio.sleep(self.scanner.scan_interval)

    async def _execute_arbitrage(self, opp):
        """Execute an arbitrage opportunity (demo mode)"""
        try:
            # Check bankroll first
            size = 1.0  # Default: 1 share per side
            if not self.bankroll.can_place_trade(size, opp.total_cost):
                return
            
            # Place YES side (demo)
            yes_trade = self.bankroll.place_trade(
                market_id=opp.market_id,
                market_name=opp.market_name,
                side="BUY",
                asset="YES",
                size=size,
                entry_price=opp.yes_price
            )
            
            # Place NO side (demo)
            no_trade = self.bankroll.place_trade(
                market_id=opp.market_id,
                market_name=opp.market_name,
                side="BUY",
                asset="NO",
                size=size,
                entry_price=opp.no_price
            )
            
            if yes_trade and no_trade:
                self._log(
                    f"✅ ARB EXEC: {opp.market_name[:30]} | "
                    f"YES+NO=${opp.total_cost:.4f} | "
                    f"+{opp.profit_pct:.2f}% profit"
                )
                self.last_execution_time = datetime.now()
        
        except Exception as e:
            logger.error(f"Error executing arbitrage: {e}")

    async def _wallet_tracking_loop(self):
        """Periodically track top wallets (for strategy 2 & 3)"""
        while self.is_running:
            try:
                elapsed = (
                    (datetime.now() - self.last_wallet_update).total_seconds()
                    if self.last_wallet_update else self.wallet_update_interval
                )
                
                if elapsed >= self.wallet_update_interval:
                    wallets = await self.polymarket_client.get_leaderboard(limit=10)
                    self.top_wallets = wallets
                    self.last_wallet_update = datetime.now()
                    
                    if wallets:
                        self._log(f"Updated top {len(wallets)} wallets")
                
                await asyncio.sleep(60)  # Check every minute
            
            except Exception as e:
                logger.error(f"Error updating wallets: {e}")
                await asyncio.sleep(60)

    async def _stats_reporter_loop(self):
        """Periodically report stats"""
        while self.is_running:
            try:
                stats = self.bankroll.get_stats()
                
                # Log every 5 minutes
                logger.info(
                    f"STATS | Balance: ${stats['current_balance']:.2f} | "
                    f"PnL: ${stats['total_pnl']:.2f} ({stats['total_pnl_pct']:.2f}%) | "
                    f"Trades: {stats['trades_total']} | "
                    f"Win Rate: {stats['win_rate']:.1f}%"
                )
                
                await asyncio.sleep(300)  # Every 5 minutes
            
            except Exception as e:
                logger.error(f"Error reporting stats: {e}")
                await asyncio.sleep(300)

    def _log(self, message: str):
        """Add to execution log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.execution_log.append(entry)
        logger.info(entry)
        
        # Keep last 100 entries
        self.execution_log = self.execution_log[-100:]

    def get_stats(self) -> Dict:
        """Get current bot statistics (for TUI)"""
        bankroll_stats = self.bankroll.get_stats()
        scanner_stats = self.scanner.get_stats()
        
        return {
            "bankroll": bankroll_stats["current_balance"],
            "pnl": bankroll_stats["total_pnl"],
            "pnl_pct": bankroll_stats["total_pnl_pct"],
            "trades_count": bankroll_stats["trades_total"],
            "win_rate": bankroll_stats["win_rate"],
            "opportunities": [
                {
                    "market": o.get("market", "?"),
                    "profit_pct": o.get("profit_pct", 0),
                    "yes_price": o.get("yes_price", 0),
                    "no_price": o.get("no_price", 0)
                }
                for o in self.opportunities_log[-10:]
            ],
            "open_trades": [
                {
                    "market": t.market_name,
                    "asset": t.asset,
                    "size": t.size,
                    "entry": t.entry_price,
                    "status": t.status
                }
                for t in self.bankroll.get_open_trades()[:10]
            ],
            "logs": self.execution_log[-20:],
            "scanner_stats": scanner_stats
        }

    async def cleanup(self):
        """Cleanup on shutdown"""
        logger.info("Cleaning up...")
        await self.polymarket_client.close()
