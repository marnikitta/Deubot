from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from deubot.agent import GermanLearningAgent


class DeuBot:
    def __init__(self, token: str, allowed_user_id: int, agent: GermanLearningAgent):
        self.token = token
        self.allowed_user_id = allowed_user_id
        self.agent = agent
        self.user_messages: dict[int, list[dict[str, str]]] = {}
        self.last_reset: dict[int, datetime] = {}

    def _is_authorized(self, user_id: int) -> bool:
        return user_id == self.allowed_user_id

    def _should_reset_daily(self, user_id: int) -> bool:
        if user_id not in self.last_reset:
            return True
        now = datetime.now()
        last = self.last_reset[user_id]
        return now - last > timedelta(days=1)

    def _clear_history(self, user_id: int) -> None:
        self.user_messages[user_id] = []
        self.last_reset[user_id] = datetime.now()

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_user or not update.message:
            return
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("Sorry, you are not authorized to use this bot.")
            return

        self._clear_history(update.effective_user.id)
        await update.message.reply_text(
            "Hallo! I'm your German learning assistant.\n\n"
            "Send me any German or English text and I'll translate it for you.\n"
            "I'll also save useful phrases for spaced repetition practice.\n\n"
            "Commands:\n"
            "/clear - Clear conversation history\n"
            "/stats - Show your learning statistics"
        )

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_user or not update.message:
            return
        if not self._is_authorized(update.effective_user.id):
            return

        self._clear_history(update.effective_user.id)
        await update.message.reply_text("Conversation history cleared!")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_user or not update.message:
            return
        if not self._is_authorized(update.effective_user.id):
            return

        phrases = self.agent.db.get_all_phrases()
        due_phrases = self.agent.db.get_due_phrases()

        stats_text = "Learning Statistics\n\n"
        stats_text += f"Total phrases: {len(phrases)}\n"
        stats_text += f"Due for review: {len(due_phrases)}\n"

        if phrases:
            total_reviews = sum(p["review_count"] for p in phrases)
            stats_text += f"Total reviews: {total_reviews}\n"

        await update.message.reply_text(stats_text)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_user or not update.message or not update.message.text:
            return
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("Sorry, you are not authorized to use this bot.")
            return

        user_id = update.effective_user.id
        user_text = update.message.text

        if self._should_reset_daily(user_id):
            self._clear_history(user_id)

        if user_id not in self.user_messages:
            self.user_messages[user_id] = []

        self.user_messages[user_id].append({"role": "user", "content": user_text})

        try:
            response_text, should_clear = self.agent.process_message(self.user_messages[user_id])

            if should_clear:
                self._clear_history(user_id)
                self.user_messages[user_id].append({"role": "user", "content": user_text})
                response_text, _ = self.agent.process_message(self.user_messages[user_id])

            self.user_messages[user_id].append({"role": "assistant", "content": response_text})

            await update.message.reply_text(response_text)

        except Exception as e:
            await update.message.reply_text(f"Sorry, an error occurred: {str(e)}")
            raise

    def run(self) -> None:
        application = Application.builder().token(self.token).build()

        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("clear", self.clear_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        application.run_polling(allowed_updates=Update.ALL_TYPES)
