from __future__ import annotations

from app.config import settings
from app.db import Database
from app.runtime.graph import run_workflow
from app.templates.registry import seed_default_workflows


def resolve_default_workflow_id(db: Database) -> str:
    if settings.default_telegram_workflow_id:
        return settings.default_telegram_workflow_id
    for workflow in db.list_workflows():
        if workflow["template_key"] == "financial_assistant":
            return workflow["id"]
    raise RuntimeError("No Financial Assistant workflow found. Run app.main first.")


def start_bot() -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required.")

    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
    except ImportError as exc:
        raise RuntimeError("Install python-telegram-bot to enable Telegram integration.") from exc

    db = Database()
    db.init()
    seed_default_workflows(db)
    workflow_id = resolve_default_workflow_id(db)

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        if update.message:
            await update.message.reply_text("Send me a stock question like: What is Apple's stock price?")

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        if not update.message or not update.message.text:
            return
        result = run_workflow(
            workflow_id=workflow_id,
            user_input=update.message.text,
            source_channel="telegram",
            external_user_id=str(update.effective_user.id if update.effective_user else ""),
            db=db,
        )
        await update.message.reply_text(result.output)

    application = Application.builder().token(settings.telegram_bot_token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()


def main() -> None:
    start_bot()


if __name__ == "__main__":
    main()
