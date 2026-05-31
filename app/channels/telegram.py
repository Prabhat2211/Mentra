from __future__ import annotations

import asyncio

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
    workflows = db.list_workflows()
    if workflows:
        return workflows[0]["id"]
    raise RuntimeError("No workflows found. Create one via the UI first.")


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
            await update.message.reply_text(
                "Send me a message and I'll run it through the configured workflow.\n"
                "Commands:\n"
                "/workflows — list available workflows\n"
                "/use <number|name|id> — switch to a different workflow"
            )

    async def list_workflows(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        if not update.message:
            return
        wf_list = db.list_workflows()
        lines = ["Available workflows:"]
        for i, wf in enumerate(wf_list, 1):
            lines.append(f"{i}. {wf['name']} ({wf['template_key']})")
        lines.append("")
        lines.append("Use /use <number> or /use <name> to switch.")
        await update.message.reply_text("\n".join(lines))

    async def use_workflow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        nonlocal workflow_id
        if not update.message or not context.args:
            await update.message.reply_text("Usage: /use <number|name|id>")
            return
        query = context.args[0].lower()
        wf_list = db.list_workflows()

        # Match by number
        if query.isdigit():
            idx = int(query) - 1
            if 0 <= idx < len(wf_list):
                wf = wf_list[idx]
                workflow_id = wf["id"]
                await update.message.reply_text(f"Switched to: {wf['name']} ({wf['template_key']})")
                return

        # Match by name (partial, case-insensitive) or full ID
        for wf in wf_list:
            if wf["id"].startswith(query) or query in wf["name"].lower():
                workflow_id = wf["id"]
                await update.message.reply_text(f"Switched to: {wf['name']} ({wf['template_key']})")
                return

        await update.message.reply_text(f"No workflow found matching '{context.args[0]}'. Use /workflows to see available workflows.")

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        if not update.message or not update.message.text:
            return
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: run_workflow(
                workflow_id=workflow_id,
                user_input=update.message.text,
                source_channel="telegram",
                external_user_id=str(update.effective_user.id if update.effective_user else ""),
                db=db,
            )
        )
        await update.message.reply_text(result.output)

    application = Application.builder().token(settings.telegram_bot_token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("workflows", list_workflows))
    application.add_handler(CommandHandler("use", use_workflow))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()


def main() -> None:
    start_bot()


if __name__ == "__main__":
    main()
