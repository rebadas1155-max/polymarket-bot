"""
Standalone TUI Dashboard - connects to bot server via HTTP
"""
import os
import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, DataTable
from textual.containers import Vertical
from textual.reactive import reactive
from textual.binding import Binding
from datetime import datetime
import aiohttp

BOT_HOST = os.getenv("BOT_HOST", "127.0.0.1")
BOT_PORT = int(os.getenv("BOT_PORT", "8080"))
BASE_URL = f"http://{BOT_HOST}:{BOT_PORT}"

class BankrollPanel(Static):
    bankroll = reactive(50.0)
    pnl = reactive(0.0)
    pnl_pct = reactive(0.0)
    status = reactive("CONNECTING")
    trades_count = reactive(0)
    win_rate = reactive(0.0)

    def render(self) -> str:
        return f"""
\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557
\u2551                     BANKROLL & P&L STATS                     \u2551
\u2560\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2563
\u2551  Bankroll: ${self.bankroll:>10.2f}  \u2502  Total P&L: ${self.pnl:>10.2f}          \u2551
\u2551  P&L %: {self.pnl_pct:>10.2f}%     \u2502  Status: {self.status:<20s}          \u2551
\u2551  Trades: {self.trades_count:>10d}      \u2502  Win Rate: {self.win_rate:>10.2f}%          \u2551
\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d
"""

class OpportunitiesPanel(Static):
    opportunities = reactive([])

    def render(self) -> str:
        if not self.opportunities:
            return "\U0001f50d Scanning for opportunities...\n"

        lines = ["\u2554\u2550\u2550\u2550 TOP ARBITRAGE OPPORTUNITIES \u2550\u2550\u2550\u2557"]
        for i, opp in enumerate(self.opportunities[:5]):
            opp_name = opp.get("market", "?")[:25].ljust(25)
            profit = opp.get("profit_pct", 0)
            lines.append(f"\u2551 {opp_name} \u2502 +{profit:.2f}%  \u2551")
        lines.append("\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557")
        return "\n".join(lines) + "\n"

class TradeLogPanel(Static):
    logs = reactive([])

    def render(self) -> str:
        if not self.logs:
            return "\U0001f4cb Awaiting log entries...\n"

        lines = ["\u2554\u2550\u2550\u2550\u2550\u2550\u2550 RECENT LOG \u2550\u2550\u2550\u2550\u2550\u2550\u2557"]
        for entry in self.logs[-8:]:
            lines.append(f"\u2551 {str(entry)[:28].ljust(28)} \u2551")
        lines.append("\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557")
        return "\n".join(lines) + "\n"

class RemoteArbBotTUI(App):
    BINDINGS = [
        Binding("p", "pause", "Pause", show=True),
        Binding("r", "resume", "Resume", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    bankroll = reactive(50.0)
    pnl = reactive(0.0)
    pnl_pct = reactive(0.0)
    status = reactive("CONNECTING")
    opportunities = reactive([])
    open_trades = reactive([])
    logs = reactive([])
    trades_count = reactive(0)
    win_rate = reactive(0.0)

    def __init__(self):
        super().__init__()
        self.bankroll_panel = None
        self.opp_panel = None
        self.log_panel = None
        self._session = None
        self._connected = False

    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical():
            self.bankroll_panel = BankrollPanel()
            yield self.bankroll_panel

            self.opp_panel = OpportunitiesPanel()
            yield self.opp_panel

            trades_table = DataTable(id="trades")
            trades_table.add_columns("Market", "Asset", "Size", "Entry", "Status")
            yield trades_table

            self.log_panel = TradeLogPanel()
            yield self.log_panel

        yield Footer()

    async def on_mount(self) -> None:
        self._session = aiohttp.ClientSession()
        self.add_log("Connecting to bot server...")
        asyncio.create_task(self._update_loop())

    async def _fetch(self, endpoint: str):
        try:
            async with self._session.get(f"{BASE_URL}{endpoint}", timeout=2) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception:
            return None

    async def _post(self, endpoint: str):
        try:
            async with self._session.post(f"{BASE_URL}{endpoint}", timeout=2):
                pass
        except Exception:
            pass

    async def _update_loop(self):
        while True:
            try:
                data = await self._fetch("/stats")
                if data:
                    if not self._connected:
                        self._connected = True
                        self.add_log("Connected to bot server")
                        self.status = "RUNNING"

                    self.bankroll = data.get("bankroll", 50.0)
                    self.pnl = data.get("pnl", 0.0)
                    self.pnl_pct = data.get("pnl_pct", 0.0)
                    self.trades_count = data.get("trades_count", 0)
                    self.win_rate = data.get("win_rate", 0.0)
                    self.opportunities = data.get("opportunities", [])
                    self.open_trades = data.get("open_trades", [])
                    self.logs = data.get("logs", [])

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
                else:
                    self.status = "DISCONNECTED"
                    if self.bankroll_panel:
                        self.bankroll_panel.status = "DISCONNECTED"

                await asyncio.sleep(1)

            except Exception as e:
                await asyncio.sleep(1)

    def add_log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.logs = [entry] + self.logs[:20]

    async def action_pause(self) -> None:
        self.status = "PAUSED"
        self.add_log("Pause requested")
        await self._post("/pause")

    async def action_resume(self) -> None:
        self.status = "RUNNING"
        self.add_log("Resume requested")
        await self._post("/resume")

    async def action_quit(self) -> None:
        self.add_log("Shutting down...")
        await self._post("/quit")
        if self._session:
            await self._session.close()
        super().action_quit()
