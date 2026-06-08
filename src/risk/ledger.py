"""
Demo Ledger - Tracks all demo trades and bankroll
In-memory tracking of fake trades + P&L
Simple transition to real mode just changes this layer
"""
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import logging
import json

logger = logging.getLogger(__name__)

class Trade:
    def __init__(
        self,
        trade_id: str,
        market_id: str,
        market_name: str,
        side: str,  # BUY or SELL
        asset: str,  # YES or NO
        size: float,
        entry_price: float,
        entry_time: datetime,
        exit_price: Optional[float] = None,
        exit_time: Optional[datetime] = None,
        status: str = "OPEN"  # OPEN, CLOSED, PARTIAL
    ):
        self.trade_id = trade_id
        self.market_id = market_id
        self.market_name = market_name
        self.side = side
        self.asset = asset
        self.size = size
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.status = status

    @property
    def entry_cost(self) -> float:
        return self.entry_price * self.size

    @property
    def current_value(self) -> float:
        if self.exit_price:
            return self.exit_price * self.size
        return self.entry_cost

    @property
    def pnl(self) -> float:
        if self.exit_price:
            return (self.exit_price - self.entry_price) * self.size
        return 0

    @property
    def pnl_pct(self) -> float:
        if self.entry_price > 0:
            return (self.pnl / self.entry_cost) * 100
        return 0

    def __repr__(self):
        return (f"Trade({self.market_name[:20]} {self.asset} "
                f"@ ${self.entry_price:.4f} x{self.size} | "
                f"PnL: ${self.pnl:.4f} ({self.pnl_pct:.2f}%) [{self.status}])")

class DemoBankroll:
    """
    Tracks demo bankroll and all trades
    Enforces limits, rejects over-sized trades
    """
    
    def __init__(self, initial_capital: float = 50.0):
        self.initial_capital = initial_capital
        self.current_balance = initial_capital
        self.trades: List[Trade] = []
        self.trade_counter = 0
        self.created_at = datetime.now()
        
        # Risk limits
        self.max_loss_per_trade_pct = 0.05  # 5% per trade
        self.max_position_size = 2.5  # $2.50 max per trade
        self.max_monthly_loss_pct = 0.20  # 20% monthly
        self.max_drawdown_pct = 0.20  # 20% total drawdown

    def can_place_trade(self, size: float, entry_price: float) -> bool:
        """Check if trade meets risk requirements"""
        cost = size * entry_price
        
        # Check: is capital available?
        if cost > self.current_balance:
            logger.warning(
                f"Insufficient balance: need ${cost:.2f}, have ${self.current_balance:.2f}"
            )
            return False
        
        # Check: max position size
        if size > self.max_position_size:
            logger.warning(
                f"Position too large: {size} > {self.max_position_size}"
            )
            return False
        
        # Check: max loss per trade
        max_loss_allowed = self.current_balance * self.max_loss_per_trade_pct
        if cost > max_loss_allowed:
            logger.warning(
                f"Position risk too high: ${cost:.2f} > ${max_loss_allowed:.2f}"
            )
            return False
        
        return True

    def place_trade(
        self,
        market_id: str,
        market_name: str,
        side: str,
        asset: str,
        size: float,
        entry_price: float
    ) -> Optional[Trade]:
        """Execute a demo trade (paper trading)"""
        
        if not self.can_place_trade(size, entry_price):
            return None
        
        self.trade_counter += 1
        trade = Trade(
            trade_id=f"DEMO_{self.trade_counter}",
            market_id=market_id,
            market_name=market_name,
            side=side,
            asset=asset,
            size=size,
            entry_price=entry_price,
            entry_time=datetime.now()
        )
        
        # Deduct cost from balance
        cost = trade.entry_cost
        self.current_balance -= cost
        
        self.trades.append(trade)
        
        logger.info(
            f"Trade executed: {trade.trade_id} "
            f"{market_name[:30]} {asset} "
            f"@ ${entry_price:.4f} x {size} | "
            f"Balance: ${self.current_balance:.2f}"
        )
        
        return trade

    def close_trade(
        self,
        trade_id: str,
        exit_price: float
    ) -> Optional[Trade]:
        """Close a trade at exit price"""
        
        for trade in self.trades:
            if trade.trade_id == trade_id:
                trade.exit_price = exit_price
                trade.exit_time = datetime.now()
                trade.status = "CLOSED"
                
                # Return proceeds to balance
                proceeds = trade.current_value
                self.current_balance += proceeds
                
                logger.info(
                    f"Trade closed: {trade_id} "
                    f"@ ${exit_price:.4f} | "
                    f"PnL: ${trade.pnl:.4f} ({trade.pnl_pct:.2f}%) | "
                    f"Balance: ${self.current_balance:.2f}"
                )
                
                return trade
        
        logger.warning(f"Trade {trade_id} not found")
        return None

    def get_open_trades(self) -> List[Trade]:
        """Return all open trades"""
        return [t for t in self.trades if t.status == "OPEN"]

    def get_closed_trades(self) -> List[Trade]:
        """Return all closed trades"""
        return [t for t in self.trades if t.status == "CLOSED"]

    @property
    def total_pnl(self) -> float:
        """Sum of all trade P&Ls"""
        return sum(t.pnl for t in self.trades)

    @property
    def total_pnl_pct(self) -> float:
        """Total P&L as percentage of initial capital"""
        if self.initial_capital > 0:
            return (self.total_pnl / self.initial_capital) * 100
        return 0

    @property
    def win_rate(self) -> float:
        """Percentage of closed trades that were profitable"""
        closed = self.get_closed_trades()
        if not closed:
            return 0
        wins = sum(1 for t in closed if t.pnl > 0)
        return (wins / len(closed)) * 100

    @property
    def drawdown_pct(self) -> float:
        """Current drawdown from peak"""
        if self.initial_capital > 0:
            return ((self.initial_capital - self.current_balance) / self.initial_capital) * 100
        return 0

    def get_stats(self) -> Dict:
        """Return comprehensive stats"""
        return {
            "initial_capital": self.initial_capital,
            "current_balance": round(self.current_balance, 2),
            "total_pnl": round(self.total_pnl, 2),
            "total_pnl_pct": round(self.total_pnl_pct, 2),
            "trades_total": len(self.trades),
            "trades_open": len(self.get_open_trades()),
            "trades_closed": len(self.get_closed_trades()),
            "win_rate": round(self.win_rate, 2),
            "drawdown_pct": round(self.drawdown_pct, 2),
            "created_at": self.created_at.isoformat(),
            "uptime_hours": (datetime.now() - self.created_at).total_seconds() / 3600
        }

    def export_trades_json(self) -> str:
        """Export all trades as JSON"""
        trades_list = []
        for t in self.trades:
            trades_list.append({
                "id": t.trade_id,
                "market": t.market_name,
                "asset": t.asset,
                "size": t.size,
                "entry_price": round(t.entry_price, 4),
                "exit_price": round(t.exit_price, 4) if t.exit_price else None,
                "entry_time": t.entry_time.isoformat(),
                "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                "pnl": round(t.pnl, 4),
                "pnl_pct": round(t.pnl_pct, 2),
                "status": t.status
            })
        return json.dumps(trades_list, indent=2)
