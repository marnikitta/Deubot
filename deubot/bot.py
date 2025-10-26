import logging
from datetime import datetime, timedelta
from typing import Iterable
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import BadRequest
from deubot.agent import GermanLearningAgent, MessageOutput, ShowReviewOutput, LogOutput, TypingOutput, UserOutput

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
        self.review_state: dict = {}
        self.debug_enabled: bool = False

    def _should_reset_daily(self) -> bool:
        if self.last_reset is None:
            return True
        now = datetime.now()
        return now - self.last_reset > timedelta(days=1)

    def _clear_history(self) -> None:
        self.agent.clear_history()
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
            "/stats - Statistiken / <i>Show statistics</i>\n"
            "/review - Wiederholung starten / <i>Start review session</i>\n"
            "/debug - Debug-Logging umschalten / <i>Toggle debug logging</i>",
            parse_mode="HTML",
        )

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return

        self._clear_history()
        await update.message.reply_text("Verlauf gelöscht!\n<i>Conversation history cleared!</i>", parse_mode="HTML")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return

        phrases = self.agent.db.get_all_phrases()
        due_phrases = self.agent.db.get_due_phrases()

        stats_text = "Lernstatistiken\n<i>Learning Statistics</i>\n\n"
        stats_text += f"Gesamt: {len(phrases)} Phrasen\n<i>Total: {len(phrases)} phrases</i>\n"
        stats_text += f"Fällig: {len(due_phrases)} Phrasen\n<i>Due for review: {len(due_phrases)} phrases</i>"

        await update.message.reply_text(stats_text, parse_mode="HTML")

    async def review_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return

        try:
            outputs = self.agent.process_message("I want to start a review session")
            await self._handle_outputs(update.message, outputs)
        except Exception as e:
            await update.message.reply_text(f"Fehler / Error: {str(e)}")
            raise

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
            elif isinstance(output, ShowReviewOutput):
                await self._show_review_card(message, output)
            elif isinstance(output, LogOutput):
                if output.message:
                    await message.reply_text(f"[{output.message}]")

    async def _show_review_card(self, message, review: ShowReviewOutput) -> None:
        self.review_state = {"phrase_id": review.phrase_id, "german": review.german, "explanation": review.explanation}

        keyboard = [[InlineKeyboardButton("Zeigen / Reveal", callback_data=f"reveal_{review.phrase_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = f"<b>{review.german}</b>\n\n<i>Was bedeutet das? / What does this mean?</i>"
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
        data = query.data

        if data.startswith("reveal_"):
            phrase_id = data.split("_")[1]
            await self._handle_reveal(query, phrase_id)
        elif data.startswith("quality_"):
            parts = data.split("_")
            phrase_id = parts[1]
            quality = int(parts[2])
            await self._handle_quality(query, phrase_id, quality)

    async def _handle_reveal(self, query, phrase_id: str) -> None:
        if not self.review_state or self.review_state["phrase_id"] != phrase_id:
            return

        german = self.review_state["german"]
        explanation = self.review_state["explanation"]

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

        text = f"<b>{german}</b>\n\n{explanation}\n\n<i>Wie gut konntest du dich erinnern? / How well did you remember?</i>"
        try:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise
            logger.debug(f"Message not modified (duplicate reveal click): {e}")

    async def _handle_quality(self, query, phrase_id: str, quality: int) -> None:
        if not self.review_state or self.review_state["phrase_id"] != phrase_id:
            return

        german = self.review_state["german"]
        explanation = self.review_state["explanation"]
        quality_names = {1: "Nochmal / Again", 2: "Schwer / Hard", 3: "Gut / Good", 4: "Leicht / Easy"}
        quality_name = quality_names.get(quality, "")

        self.agent.db.update_review(phrase_id, quality)
        self.review_state = {}

        try:
            text = (
                f"<b>{german}</b>\n\n{explanation}\n\n<i>Wie gut konntest du dich erinnern? / How well did you remember?</i>\n\n✓ Bewertet als / Rated as: {quality_name}"
            )
            await query.edit_message_text(
                text,
                parse_mode="HTML",
            )
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise
            logger.debug(f"Message not modified (duplicate quality rating): {e}")

        try:
            outputs = self.agent.process_message(f"REVIEWED: {german} as {quality_name}")
            await self._handle_outputs(query.message, outputs)
        except Exception as e:
            await query.message.reply_text(f"Error: {str(e)}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text:
            return

        user_text = update.message.text
        logger.info(f"Message received ({len(user_text)} chars)")

        if self._should_reset_daily():
            self._clear_history()

        try:
            outputs = self.agent.process_message(user_text)
            await self._handle_outputs(update.message, outputs)
        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}")
            await update.message.reply_text(f"Fehler / Error: {str(e)}")
            raise

    def run(self) -> None:
        application = Application.builder().token(self.token).build()
        auth_filter = AuthFilter(self.allowed_user_id)

        application.add_handler(CommandHandler("start", self.start_command, filters=auth_filter))
        application.add_handler(CommandHandler("clear", self.clear_command, filters=auth_filter))
        application.add_handler(CommandHandler("stats", self.stats_command, filters=auth_filter))
        application.add_handler(CommandHandler("review", self.review_command, filters=auth_filter))
        application.add_handler(CommandHandler("debug", self.debug_command, filters=auth_filter))
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        application.add_handler(MessageHandler(auth_filter & filters.TEXT & ~filters.COMMAND, self.handle_message))

        application.run_polling(allowed_updates=Update.ALL_TYPES)
