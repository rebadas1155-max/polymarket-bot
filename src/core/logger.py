"""
Logger utility: can push logs to TUI, Telegram, and file if needed.
"""
import os
from datetime import datetime

LOGF = os.getenv("LOGF", "arb_bot.log")

def log(msg):
    timestr = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestr}] {msg}"
    print(entry)
    try:
        with open(LOGF, "a") as f:
            f.write(entry+"\n")
    except Exception:
        pass
    return entry
