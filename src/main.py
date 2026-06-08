"""
Main Entry Point - Polymarket Arbitrage Demo Bot
Orchestrates: Bot Engine + TUI + Telegram
Runs in MODE=DEMO with $50 fake capital
"""
import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_bot_demo():
    """Run bot in DEMO mode"""
    from src.core.bot_engine import BotEngine
    from src.tui.dashboard import ArbBotTUI

    logger.info("=" * 70)
    logger.info("POLYMARKET ARBITRAGE BOT - DEMO MODE")
    logger.info("=" * 70)
    logger.info(f"Initial Capital: $50.00 (fake money)")
    logger.info(f"Strategy: Arbitrage Scanner (YES + NO < $0.98)")
    logger.info(f"Mode: DEMO (no real orders, only paper trading)")
    logger.info("=" * 70)

    # Create bot engine
    config = {
        "mode": "DEMO",
        "initial_capital": 50.0,
        "scan_interval": 2,  # seconds
        "min_mispricing": 0.02,  # $0.02 gap
    }

    engine = BotEngine(config)

    try:
        # Initialize engine
        await engine.initialize()

        # Create TUI task (runs in background event loop)
        tui_task = asyncio.create_task(ArbBotTUI(engine=engine).run_async())

        # Start bot operations in main event loop
        await engine.start()

        # Wait for TUI to close
        await tui_task

    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await engine.cleanup()
        logger.info("Shutdown complete")

def main():
    """Main entry point"""
    mode = os.getenv("MODE", "demo").lower()

    if mode == "demo":
        logger.info("Running in DEMO mode")
        try:
            asyncio.run(run_bot_demo())
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
    else:
        logger.error(f"Unknown mode: {mode}")
        sys.exit(1)

if __name__ == "__main__":
    main()
