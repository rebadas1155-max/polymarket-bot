#!/usr/bin/env python3
"""
Bot server with HTTP API - runs engine + aiohttp web server
TUI (or any client) connects via HTTP to monitor/control the bot
"""
import sys
import os
import asyncio
import json
import logging
from datetime import datetime, date
from aiohttp import web
from dotenv import load_dotenv
from src.telegram.controller import TelegramBotController, run_telegram_bot

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('arb_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

HOST = os.getenv("BOT_HOST", "127.0.0.1")
PORT = int(os.getenv("BOT_PORT", "8080"))

def json_serialize(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

async def handle_stats(request):
    engine = request.app['engine']
    stats = engine.get_stats()
    return web.json_response(stats, dumps=lambda o: json.dumps(o, default=json_serialize))

async def handle_pause(request):
    engine = request.app['engine']
    engine.pause()
    return web.json_response({"status": "paused"})

async def handle_resume(request):
    engine = request.app['engine']
    engine.resume()
    return web.json_response({"status": "resumed"})

async def handle_health(request):
    engine = request.app['engine']
    return web.json_response({
        "status": "ok",
        "running": engine.is_running,
        "paused": engine.is_paused
    })

async def handle_quit(request):
    engine = request.app['engine']
    engine.stop()
    asyncio.get_event_loop().stop()
    return web.json_response({"status": "stopped"})

async def start_web_server(engine):
    app = web.Application()
    app['engine'] = engine
    app.router.add_get('/stats', handle_stats)
    app.router.add_get('/health', handle_health)
    app.router.add_post('/pause', handle_pause)
    app.router.add_post('/resume', handle_resume)
    app.router.add_post('/quit', handle_quit)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    logger.info(f"HTTP API server running on http://{HOST}:{PORT}")
    return runner, site

async def main():
    logger.info("=" * 70)
    logger.info("POLYMARKET ARBITRAGE BOT - SERVER MODE")
    logger.info("=" * 70)
    logger.info(f"Initial Capital: $50.00 (fake money)")
    logger.info(f"Strategy: Arbitrage Scanner (YES + NO < $0.98)")
    logger.info(f"Mode: DEMO (no real orders, only paper trading)")
    logger.info(f"API: http://{HOST}:{PORT}/stats")
    logger.info(f"Press Ctrl+C to stop")
    logger.info("=" * 70)

    from src.core.bot_engine import BotEngine

    config = {
        "mode": "DEMO",
        "initial_capital": 50.0,
        "scan_interval": 2,
        "min_mispricing": 0.02,
    }

    engine = BotEngine(config)

    try:
        await engine.initialize()

        runner, site = await start_web_server(engine)

        tg_controller = TelegramBotController(bot_engine=engine)
        telegram_task = asyncio.create_task(run_telegram_bot(tg_controller))

        await engine.start()

        while engine.is_running:
            await asyncio.sleep(1)

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await engine.cleanup()
        try:
            await runner.cleanup()
        except Exception:
            pass
        logger.info("Server stopped")

if __name__ == "__main__":
    asyncio.run(main())
