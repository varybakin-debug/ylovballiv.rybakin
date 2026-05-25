import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from config import BOT_TOKEN
from database import init_db
from handlers.start import start, info_handler, faq_handler
from handlers.booking import get_booking_conversation
from handlers.admin import admin_panel, all_bookings_handler, handle_reject_callback, get_admin_conversation
from scheduler import setup_scheduler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def _post_init(application):
    await init_db()
    setup_scheduler(application.bot)
    logger.info("Bot started")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан. Скопируйте .env.example в .env и заполните.")

    app = Application.builder().token(BOT_TOKEN).post_init(_post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("bookings", all_bookings_handler))

    # ConversationHandler для записи клиента
    app.add_handler(get_booking_conversation())

    # ConversationHandler для подтверждения заявки (admin)
    app.add_handler(get_admin_conversation())

    # Callback для отклонения заявки (не требует диалога)
    app.add_handler(CallbackQueryHandler(handle_reject_callback, pattern="^reject_"))

    # Статичные кнопки главного меню
    app.add_handler(MessageHandler(filters.Regex("^📚 Об услугах и ценах$"), info_handler))
    app.add_handler(MessageHandler(filters.Regex("^❓ Частые вопросы$"), faq_handler))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
