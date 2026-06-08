"""
Telegram Bot Controller - Full bidirectional control and notifications
Commands: /start, /pause, /resume, /summary, /open, /stop, /stats
Also sends real-time notifications to configured chat
"""
import os
import asyncio
import logging
from datetime import datetime
from typing import Optional

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

logger = logging.getLogger(__name__)

class TelegramBotController:
    def __init__(self, bot_engine=None):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.engine = bot_engine
        self.application = None

    async def initialize(self):
        """Initialize Telegram bot"""
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not set - Telegram disabled")
            return False
        
        logger.info("Initializing Telegram bot...")
        
        # Create application
        self.application = Application.builder().token(self.bot_token).build()
        
        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("pause", self.cmd_pause))
        self.application.add_handler(CommandHandler("resume", self.cmd_resume))
        self.application.add_handler(CommandHandler("summary", self.cmd_summary))
        self.application.add_handler(CommandHandler("open", self.cmd_open))
        self.application.add_handler(CommandHandler("stats", self.cmd_stats))
        self.application.add_handler(CommandHandler("stop", self.cmd_stop))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        
        logger.info("Telegram bot initialized")
        return True

    async def start_polling(self):
        """Start polling for updates"""
        if self.application:
            logger.info("Telegram bot starting to poll...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            logger.info("Telegram bot polling started")

    async def send_notification(self, message: str):
        """Send notification to configured chat"""
        if not self.application or not self.chat_id:
            return
        
        try:
            bot = self.application.bot
            await bot.send_message(chat_id=self.chat_id, text=message)
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    # ============ Command Handlers ============

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        message = (
            "🤖 Polymarket Arbitrage Demo Bot Online!\n\n"
            "Available commands:\n"
            "/pause - Pause trading\n"
            "/resume - Resume trading\n"
            "/summary - Quick summary\n"
            "/open - Show open positions\n"
            "/stats - Detailed stats\n"
            "/stop - Emergency stop\n"
            "/help - Show all commands"
        )
        await update.message.reply_text(message)

    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pause command"""
        if self.engine:
            self.engine.pause()
        await update.message.reply_text("⏸️ Bot paused")
        await self.send_notification("Bot paused via Telegram")

    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /resume command"""
        if self.engine:
            self.engine.resume()
        await update.message.reply_text("▶️ Bot resumed")
        await self.send_notification("Bot resumed via Telegram")

    async def cmd_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /summary command"""
        if not self.engine:
            await update.message.reply_text("Engine not available")
            return
        
        stats = self.engine.get_stats()
        message = (
            f"📊 SUMMARY\n\n"
            f"💰 Bankroll: ${stats['bankroll']:.2f}\n"
            f"📈 P&L: ${stats['pnl']:.2f} ({stats['pnl_pct']:.2f}%)\n"
            f"📌 Trades: {stats['trades_count']}\n"
            f"✅ Win Rate: {stats['win_rate']:.1f}%\n"
        )
        await update.message.reply_text(message)

    async def cmd_open(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /open command - show open positions"""
        if not self.engine:
            await update.message.reply_text("Engine not available")
            return
        
        stats = self.engine.get_stats()
        open_trades = stats.get("open_trades", [])
        
        if not open_trades:
            await update.message.reply_text("No open positions")
            return
        
        message = "📂 OPEN POSITIONS\n\n"
        for i, trade in enumerate(open_trades, 1):
            message += (
                f"{i}. {trade.get('market', '?')[:30]}\n"
                f"   {trade.get('asset')} @ ${trade.get('entry', 0):.4f}\n"
                f"   Size: ${trade.get('size', 0):.2f}\n\n"
            )
        
        await update.message.reply_text(message)

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command - detailed statistics"""
        if not self.engine:
            await update.message.reply_text("Engine not available")
            return
        
        stats = self.engine.get_stats()
        scanner_stats = stats.get("scanner_stats", {})
        
        message = (
            f"📋 DETAILED STATS\n\n"
            f"Balance: ${stats['bankroll']:.2f}\n"
            f"P&L: ${stats['pnl']:.2f} ({stats['pnl_pct']:.2f}%)\n"
            f"Trades: {stats['trades_count']}\n"
            f"Win Rate: {stats['win_rate']:.1f}%\n\n"
            f"Scanner Stats:\n"
            f"Total Scans: {scanner_stats.get('total_scans', 0)}\n"
            f"Opportunities Found: {scanner_stats.get('total_opportunities', 0)}\n"
            f"Avg per Scan: {scanner_stats.get('avg_per_scan', 0):.2f}\n"
        )
        await update.message.reply_text(message)

    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command - emergency stop"""
        if self.engine:
            self.engine.stop()
        
        await update.message.reply_text("🛑 EMERGENCY STOP - All trading halted!")
        await self.send_notification("EMERGENCY STOP activated via Telegram")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        message = (
            "🆘 HELP\n\n"
            "/start - Start bot & show menu\n"
            "/pause - Pause all trading\n"
            "/resume - Resume trading\n"
            "/summary - Quick P&L summary\n"
            "/open - Show all open positions\n"
            "/stats - Detailed statistics\n"
            "/stop - Emergency stop (halt everything)\n"
            "/help - Show this message\n"
        )
        await update.message.reply_text(message)

async def run_telegram_bot(bot_controller: TelegramBotController):
    """Run Telegram bot in separate task"""
    if await bot_controller.initialize():
        await bot_controller.start_polling()
