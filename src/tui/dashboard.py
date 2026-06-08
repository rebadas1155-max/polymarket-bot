"""
Live TUI Dashboard - Shows real-time engine data
Displays: Bankroll, PnL, Open Trades, Opportunities, Logs
Keys: P=Pause, R=Resume, Q=Quit, Space=Clear
"""
from textual.app import ComposeResult, App
from textual.widgets import Header, Footer, Static, DataTable, TextArea
from textual.containers import Container, Vertical, Horizontal
from textual.reactive import reactive
from textual.binding import Binding
from datetime import datetime
import asyncio

class BankrollPanel(Static):
    """Shows bankroll, PnL, and key metrics"""
    bankroll = reactive(50.0)
    pnl = reactive(0.0)
    pnl_pct = reactive(0.0)
    status = reactive("LOADING")
    trades_count = reactive(0)
    win_rate = reactive(0.0)

    def render(self) -> str:
        return f"""
╔══════════════════════════════════════════════════════════════╗
║                     BANKROLL & P&L STATS                     ║
╠══════════════════════════════════════════════════════════════╣
║  Bankroll: ${self.bankroll:>10.2f}  │  Total P&L: ${self.pnl:>10.2f}          ║
║  P&L %: {self.pnl_pct:>10.2f}%     │  Status: {self.status:<20s}          ║
║  Trades: {self.trades_count:>10d}      │  Win Rate: {self.win_rate:>10.2f}%          ║
╚══════════════════════════════════════════════════════════════╝
"""

class OpportunitiesPanel(Static):
    """Shows top arbitrage opportunities"""
    opportunities = reactive([])

    def render(self) -> str:
        if not self.opportunities:
            return "\n🔍 Scanning for opportunities...\n"
        
        header = "╔════ TOP ARBITRAGE OPPORTUNITIES ════╗\n"
        lines = ["║                                    ║"]
        
        for i, opp in enumerate(self.opportunities[:5]):  # Top 5
            market_name = opp.market_name[:25].ljust(25)
            line = f"║ {market_name} │ +{opp.profit_pct:.2f}%  ║"
            lines.append(line)
        
        lines.append("╚════════════════════════════════════╝")
        
        return header + "\n".join(lines) + "\n"

class TradeLogPanel(Static):
    """Shows recent trade log"""
    logs = reactive([])

    def render(self) -> str:
        if not self.logs:
            return "📋 Awaiting log entries...\n"
        
        lines = ["╔════════ RECENT LOG ════════╗"]
        for log_entry in self.logs[-8:]:  # Last 8 lines
            lines.append(f"║ {log_entry[:28].ljust(28)} ║")
        lines.append("╚════════════════════════════╝")
        
        return "\n".join(lines) + "\n"

class ArbBotTUI(App):
    """Main TUI Application"""
    
    BINDINGS = [
        Binding("p", "pause", "Pause", show=True),
        Binding("r", "resume", "Resume", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]
    
    # Reactive state
    bankroll = reactive(50.0)
    pnl = reactive(0.0)
    pnl_pct = reactive(0.0)
    status = reactive("INITIALIZING")
    opportunities = reactive([])
    open_trades = reactive([])
    logs = reactive([])
    trades_count = reactive(0)
    win_rate = reactive(0.0)

    def __init__(self, engine=None):
        super().__init__()
        self.engine = engine
        self.bankroll_panel = None
        self.opp_panel = None
        self.log_panel = None

    def compose(self) -> ComposeResult:
        yield Header()
        
        with Vertical():
            # Top section: Bankroll stats
            self.bankroll_panel = BankrollPanel()
            yield self.bankroll_panel
            
            # Middle section: Opportunities
            self.opp_panel = OpportunitiesPanel()
            yield self.opp_panel
            
            # Open trades table
            trades_table = DataTable(id="trades")
            trades_table.add_columns("Market", "Asset", "Size", "Entry", "Status")
            yield trades_table
            
            # Bottom section: Log
            self.log_panel = TradeLogPanel()
            yield self.log_panel
        
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize and start update loop"""
        self.status = "RUNNING"
        self.add_log("TUI initialized")
        
        # Start background update loop
        if self.engine:
            asyncio.create_task(self._update_loop())

    async def _update_loop(self):
        """Update displays with engine data"""
        while True:
            try:
                if self.engine:
                    # Get stats from engine
                    stats = self.engine.get_stats()
                    
                    self.bankroll = stats.get("bankroll", 50.0)
                    self.pnl = stats.get("pnl", 0.0)
                    self.pnl_pct = stats.get("pnl_pct", 0.0)
                    self.trades_count = stats.get("trades_count", 0)
                    self.win_rate = stats.get("win_rate", 0.0)
                    self.opportunities = stats.get("opportunities", [])
                    self.open_trades = stats.get("open_trades", [])
                    self.logs = stats.get("logs", [])
                    
                    # Update panels
                    if self.bankroll_panel:
                        self.bankroll_panel.bankroll = self.bankroll
                        self.bankroll_panel.pnl = self.pnl
                        self.bankroll_panel.pnl_pct = self.pnl_pct
                        self.bankroll_panel.status = self.status
                        self.bankroll_panel.trades_count = self.trades_count
                        self.bankroll_panel.win_rate = self.win_rate
                    
                    if self.opp_panel:
                        self.opp_panel.opportunities = self.opportunities
                    
                    if self.log_panel:
                        self.log_panel.logs = self.logs
                
                # Update trades table
                trades_table = self.query_one("#trades", DataTable)
                trades_table.clear()
                for trade in self.open_trades[:10]:
                    trades_table.add_row(
                        trade.get("market", "?")[:20],
                        trade.get("asset", "?"),
                        f"${trade.get('size', 0):.2f}",
                        f"${trade.get('entry', 0):.4f}",
                        trade.get("status", "?")
                    )
                
                await asyncio.sleep(1)  # Update every second
                
            except Exception as e:
                self.add_log(f"Error: {str(e)[:40]}")
                await asyncio.sleep(1)

    def add_log(self, message: str):
        """Add log entry with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.logs = [entry] + self.logs[:20]  # Keep last 20

    def action_pause(self) -> None:
        """Pause bot"""
        self.status = "PAUSED"
        self.add_log("⏸  Bot paused")
        if self.engine:
            self.engine.pause()

    def action_resume(self) -> None:
        """Resume bot"""
        self.status = "RUNNING"
        self.add_log("▶  Bot resumed")
        if self.engine:
            self.engine.resume()

    def action_quit(self) -> None:
        """Exit cleanly"""
        self.add_log("🛑 Shutting down...")
        if self.engine:
            self.engine.stop()
        super().action_quit()
