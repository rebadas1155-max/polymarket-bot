"""
DEMO/REAL mode switcher, bankroll enforcement, trigger self-healing on risk events.
Stub for inline use in engine/main bot loop.
"""
import os
MODE = os.getenv("MODE", "demo")

class DemoBankroll:
    def __init__(self, cap=50.0):
        self.start = cap
        self.bankroll = cap
        self.pnl = 0.0
        self.trades = []

    def can_place(self, amount):
        return self.bankroll >= amount

    def register_trade(self, amount, pnl):
        self.trades.append((amount, pnl))
        self.bankroll += pnl
        self.pnl += pnl

    def is_breached(self, losslimit=0.8):
        return self.bankroll < self.start * losslimit

if MODE == "demo":
    bankroll = DemoBankroll()
else:
    # Real bankroll logic would go here
    bankroll = None
