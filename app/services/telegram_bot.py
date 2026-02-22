"""
Telegram Bot service for VoltWay.

Provides bot functionality for:
- Finding nearby stations
- Station availability notifications
- Reservation management
- Quick search
"""

import logging
import os
from typing import Optional

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.config import settings

logger = logging.getLogger(__name__)


class VoltWayBot:
    """Telegram Bot for VoltWay"""

    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self.is_configured = bool(self.token)

        if self.is_configured:
            self._setup()

    def _setup(self):
        """Setup bot handlers"""
        self.bot = Bot(token=self.token)
        self.dp = Dispatcher()

        # Register handlers
        self.dp.message(self.cmd_start)(self._handle_start)
        self.dp.message(self.cmd_help)(self._handle_help)
        self.dp.message(self.cmd_nearby)(self._handle_nearby)

        logger.info("Telegram bot configured")

    async def _handle_start(self, message: types.Message):
        """Handle /start command"""
        await message.answer(
            "👋 Добро пожаловать в VoltWay Bot!\n\n"
            "Я помогу вам найти зарядные станции для электромобилей.\n\n"
            "Команды:\n"
            "/nearby - Найти станции рядом\n"
            "/help - Помощь\n"
            "/settings - Настройки"
        )

    async def _handle_help(self, message: types.Message):
        """Handle /help command"""
        await message.answer(
            "📖 **Помощь**\n\n"
            "**Основные команды:**\n"
            "/start - Запустить бота\n"
            "/nearby - Найти станции рядом\n"
            "/help - Эта справка\n\n"
            "**Как найти станции:**\n"
            "1. Отправьте команду /nearby\n"
            "2. Бот запросит вашу геопозицию\n"
            "3. Получите список ближайших станций\n\n"
            "**Уведомления:**\n"
            "Подпишитесь на уведомления о статусе станций."
        )

    async def _handle_nearby(self, message: types.Message):
        """Handle /nearby command"""
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📍 Отправить геопозицию",
                        request_location=True,
                    )
                ]
            ]
        )

        await message.answer(
            "📍 Отправьте вашу геопозицию, чтобы найти ближайшие зарядные станции.\n\n"
            "Или нажмите кнопку ниже:",
            reply_markup=keyboard,
        )

    async def send_station_notification(
        self,
        user_id: int,
        station_title: str,
        status: str,
        address: str,
    ):
        """
        Send notification about station status change.

        Args:
            user_id: Telegram user ID
            station_title: Station name
            status: New status
            address: Station address
        """
        if not self.is_configured or not self.bot:
            return

        status_emoji = {
            "available": "✅",
            "occupied": "🔴",
            "maintenance": "🔧",
            "unknown": "❓",
        }

        emoji = status_emoji.get(status, "❓")

        text = (
            f"{emoji} **Обновление станции**\n\n"
            f"**{station_title}**\n"
            f"📍 {address}\n\n"
            f"Статус: **{status}**"
        )

        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")

    async def start(self):
        """Start bot polling"""
        if not self.is_configured:
            logger.warning("Telegram bot not configured, skipping start")
            return

        logger.info("Starting Telegram bot...")
        await self.dp.start_polling(self.bot)

    async def stop(self):
        """Stop bot"""
        if self.is_configured and self.bot:
            await self.bot.session.close()
            logger.info("Telegram bot stopped")


# Global bot instance
voltway_bot = VoltWayBot()
