"""
Live TUI for Polymarket Arbitrage Demo
Shows: Bankroll, PnL, Open Trades, Log; Keys for Pause/Resume
"""
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, DataTable
from textual.reactive import reactive
from textual import events

class ArbBotTUI(App):
    CSS_PATH = None
    bankroll = reactive(50.0)
    pnl = reactive(0.0)
    status = reactive("RUNNING")
    logs = reactive([])
    open_trades = reactive([])

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(lambda: f"Bankroll: ${self.bankroll:.2f} | PnL: ${self.pnl:.2f} | Status: {self.status}", id="banner")
        yield DataTable(id="trades")
        yield Static(lambda: "\n".join(self.logs[-10:]), id="logbox")
        yield Footer()

    async def on_mount(self) -> None:
        table = self.query_one("#trades", DataTable)
        table.add_columns("Market", "YES Price", "NO Price", "Profit%", "Size", "Status")
        # Demo trades
        table.add_row("Trump 2028", "0.40", "0.58", "2.0", "10", "Open")

    async def key_p(self):  # Pause
        self.status = "PAUSED"
        self.logs.append("[KEY] Paused bot")

    async def key_r(self):  # Resume
        self.status = "RUNNING"
        self.logs.append("[KEY] Resumed bot")

if __name__ == "__main__":
    app = ArbBotTUI()
    app.run()
