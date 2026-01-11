import logging
import os
from datetime import datetime, timedelta
from typing import Iterable
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import BadRequest
from deubot.agent import (
    GermanLearningAgent,
    MessageOutput,
    ShowReviewBatchOutput,
    LogOutput,
    TypingOutput,
    UserOutput,
    escape_html,
)
from deubot.bot_helpers import format_level, get_quality_name, parse_callback_data
from deubot.review_session import ReviewSession, ReviewCard
from deubot.translations import ReviewDirection
from deubot.systemd import notify_systemd

logger = logging.getLogger(__name__)


class AuthFilter(filters.MessageFilter):
    def __init__(self, allowed_user_id: int):
        super().__init__()
        self.allowed_user_id = allowed_user_id

    def filter(self, message: Message) -> bool:
        if message.from_user is None:
            return False

        if message.from_user.id == self.allowed_user_id:
            return True
        else:
            logger.warning(f"Unauthorized access attempt from user {message.from_user.id}")
            return False


class DeuBot:
    def __init__(self, token: str, allowed_user_id: int, agent: GermanLearningAgent):
        self.token = token
        self.allowed_user_id = allowed_user_id
        self.agent = agent
        self.last_reset: datetime | None = None
        self.review_session = ReviewSession(agent.db)
        self.debug_enabled: bool = False

    def _should_reset_daily(self) -> bool:
        if self.last_reset is None:
            return True
        now = datetime.now()
        return now - self.last_reset > timedelta(days=1)

    def _clear_history(self) -> None:
        self.agent.clear_history()
        self.review_session.interrupt()
        self.last_reset = datetime.now()

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return

        self._clear_history()
        await update.message.reply_text(
            "Hallo! Ich bin dein Deutschlernassistent.\n"
            "<i>Hello! I'm your German learning assistant.</i>\n\n"
            "Schicke mir deutschen oder englischen Text und ich übersetze ihn für dich.\n"
            "<i>Send me German or English text and I'll translate it for you.</i>\n\n"
            "Befehle / <i>Commands:</i>\n"
            "/clear - Verlauf löschen / <i>Clear history</i>\n"
            "/debug - Debug-Logging umschalten / <i>Toggle debug logging</i>",
            parse_mode="HTML",
        )

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return

        self._clear_history()
        await update.message.reply_text("Verlauf gelöscht!\n<i>Conversation history cleared!</i>", parse_mode="HTML")

    async def debug_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return

        self.debug_enabled = not self.debug_enabled
        self.agent.enable_logs = self.debug_enabled

        status = "aktiviert / enabled" if self.debug_enabled else "deaktiviert / disabled"
        await update.message.reply_text(f"Debug-Logging {status}", parse_mode="HTML")

    async def _handle_outputs(self, message, outputs: Iterable[UserOutput]) -> None:
        for output in outputs:
            if isinstance(output, TypingOutput):
                await message.chat.send_action(action="typing")
            elif isinstance(output, MessageOutput):
                if output.message:
                    await message.reply_text(output.message, parse_mode="HTML")
            elif isinstance(output, ShowReviewBatchOutput):
                await self._handle_review_batch(message, output)
            elif isinstance(output, LogOutput):
                if output.message:
                    await message.reply_text(f"[{output.message}]")

    async def _handle_review_batch(self, message, batch: ShowReviewBatchOutput) -> None:
        """Start batch session and show first card."""
        first_card = self.review_session.start_batch(batch)
        if first_card:
            await self._show_review_card(message, first_card)

    async def _show_review_card(self, message, card: ReviewCard) -> None:
        keyboard = [[InlineKeyboardButton("Zeigen / Reveal", callback_data=f"reveal_{card.phrase_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if card.direction == ReviewDirection.GERMAN_TO_ENGLISH:
            front = card.german
            prompt = "Was bedeutet das? / What does this mean?"
        else:  # english_to_german
            front = card.english
            prompt = "Wie sagt man das auf Deutsch? / How do you say this in German?"
        text = f"<b>{escape_html(front)}</b>\n\n<i>{prompt}</i>"
        await message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query or not query.data or not query.from_user:
            return

        if query.from_user.id != self.allowed_user_id:
            logger.warning(f"Unauthorized callback from user {query.from_user.id}")
            await query.answer("Not authorized")
            return

        await query.answer()

        callback = parse_callback_data(query.data)
        if not callback:
            return

        if callback.action == "reveal":
            await self._handle_reveal(query, callback.phrase_id)
        elif callback.action == "quality" and callback.quality is not None:
            await self._handle_quality(query, callback.phrase_id, callback.quality)

    async def _handle_reveal(self, query, phrase_id: str) -> None:
        card = self.review_session.current_card
        if not card or card.phrase_id != phrase_id:
            return

        keyboard = [
            [
                InlineKeyboardButton("Leicht / Easy (4)", callback_data=f"quality_{phrase_id}_4"),
                InlineKeyboardButton("Schwer / Hard (2)", callback_data=f"quality_{phrase_id}_2"),
            ],
            [
                InlineKeyboardButton("Gut / Good (3)", callback_data=f"quality_{phrase_id}_3"),
                InlineKeyboardButton("Nochmal / Again (1)", callback_data=f"quality_{phrase_id}_1"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        level = format_level(card.repetition)
        text = f"<b>{escape_html(card.german)}</b>\n\n{card.explanation}\n\nLevel: {level}\n\n<i>Wie gut konntest du dich erinnern? / How well did you remember?</i>"
        try:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise
            logger.debug(f"Message not modified (duplicate reveal click): {e}")

    async def _handle_quality(self, query, phrase_id: str, quality: int) -> None:
        card = self.review_session.current_card
        if not card or card.phrase_id != phrase_id:
            return

        quality_name = get_quality_name(quality)

        self.review_session.record_quality(phrase_id, quality)

        try:
            level = format_level(card.repetition)
            text = f"<b>{escape_html(card.german)}</b>\n\n{card.explanation}\n\nLevel: {level}\n\n<i>Wie gut konntest du dich erinnern? / How well did you remember?</i>\n\n✓ Bewertet als / Rated as: {quality_name}"
            await query.edit_message_text(
                text,
                parse_mode="HTML",
            )
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise
            logger.debug(f"Message not modified (duplicate quality rating): {e}")

        try:
            next_card = self.review_session.advance()
            if next_card:
                await self._show_review_card(query.message, next_card)
            else:
                # Let agent handle the post-review conversation
                outputs = self.agent.process_message("I just finished reviewing all the cards.")
                await self._handle_outputs(query.message, outputs)
        except Exception as e:
            await query.message.reply_text(f"Error: {str(e)}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text:
            return

        user_text = update.message.text
        logger.info(f"Message received ({len(user_text)} chars)")

        if self.review_session.is_active:
            logger.info("User interrupted review session, clearing review session")
            self.review_session.interrupt()

        if self._should_reset_daily():
            self._clear_history()

        try:
            outputs = self.agent.process_message(user_text)
            await self._handle_outputs(update.message, outputs)
        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}")
            await update.message.reply_text(f"Fehler / Error: {str(e)}")
            raise

    async def post_init(self, _: Application) -> None:
        logger.info("Bot initialized successfully")
        notify_socket = os.getenv("NOTIFY_SOCKET")
        if notify_socket:
            notify_systemd(notify_socket)

    def run(self) -> None:
        application = Application.builder().token(self.token).post_init(self.post_init).build()
        auth_filter = AuthFilter(self.allowed_user_id)

        application.add_handler(CommandHandler("start", self.start_command, filters=auth_filter))
        application.add_handler(CommandHandler("clear", self.clear_command, filters=auth_filter))
        application.add_handler(CommandHandler("debug", self.debug_command, filters=auth_filter))
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        application.add_handler(MessageHandler(auth_filter & filters.TEXT & ~filters.COMMAND, self.handle_message))

        application.run_polling(allowed_updates=Update.ALL_TYPES)
