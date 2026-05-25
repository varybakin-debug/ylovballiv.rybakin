import logging
from datetime import datetime
from functools import wraps

import aiosqlite
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from database import (
    get_pending_bookings,
    get_all_bookings,
    confirm_booking,
    cancel_booking,
    get_booking_by_id,
    DB_PATH,
)
from config import ADMIN_ID, TUTOR_USERNAME

logger = logging.getLogger(__name__)

SET_DATETIME = 0


def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_ID:
            if update.message:
                await update.message.reply_text("⛔ Доступ запрещён.")
            elif update.callback_query:
                await update.callback_query.answer("⛔ Доступ запрещён.", show_alert=True)
            return ConversationHandler.END
        return await func(update, context)
    return wrapper


@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bookings = await get_pending_bookings()
    if not bookings:
        await update.message.reply_text("📋 Нет новых заявок.")
        return

    await update.message.reply_html(f"📋 <b>Новые заявки ({len(bookings)}):</b>")
    for b in bookings:
        text = (
            f"<b>Заявка #{b['id']}</b>\n"
            f"👤 {b['name']}\n"
            f"📱 {b['phone']}\n"
            f"📚 {'Индивидуально' if b['format'] == 'individual' else 'Мини-группа'}\n"
            f"🕐 {b['preferred_time']}\n"
            f"📅 {b['created_at'][:16]}"
        )
        keyboard = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{b['id']}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{b['id']}"),
            ]]
        )
        await update.message.reply_html(text, reply_markup=keyboard)


@admin_only
async def all_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bookings = await get_all_bookings()
    if not bookings:
        await update.message.reply_text("📋 Заявок пока нет.")
        return

    status_emoji = {"pending": "⏳", "confirmed": "✅", "cancelled": "❌"}
    lines = ["<b>Все заявки:</b>\n"]
    for b in bookings:
        emoji = status_emoji.get(b["status"], "❓")
        fmt = "Инд." if b["format"] == "individual" else "Группа"
        lines.append(
            f"{emoji} <b>#{b['id']}</b> {b['name']} — {b['phone']} — {fmt} — {b['created_at'][:16]}"
        )

    await update.message.reply_html("\n".join(lines))


@admin_only
async def handle_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    booking_id = int(query.data.split("_")[1])
    booking = await get_booking_by_id(booking_id)
    if not booking:
        await query.answer("Заявка не найдена.", show_alert=True)
        return ConversationHandler.END

    context.user_data["confirming_booking_id"] = booking_id
    await query.message.reply_text(
        f"Введите дату и время занятия для заявки #{booking_id} ({booking['name']}).\n"
        "Формат: <b>ДД.ММ.ГГГГ ЧЧ:ММ</b>\n"
        "Например: 01.06.2025 17:00\n\n"
        "Или отправьте /skip чтобы подтвердить без конкретной даты.",
        parse_mode="HTML",
    )
    return SET_DATETIME


async def handle_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    booking_id = int(query.data.split("_")[1])
    booking = await get_booking_by_id(booking_id)
    if not booking:
        return

    await cancel_booking(booking_id)
    await query.edit_message_text(
        query.message.text + "\n\n❌ <b>Отклонено</b>",
        parse_mode="HTML",
    )

    try:
        await context.bot.send_message(
            chat_id=booking["user_id"],
            text=(
                f"Здравствуйте, {booking['name']}!\n\n"
                "К сожалению, в данный момент нет свободных мест на указанное время. "
                f"Пожалуйста, напишите напрямую для уточнения: @{TUTOR_USERNAME}"
            ),
        )
    except Exception:
        pass


async def set_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    booking_id = context.user_data.get("confirming_booking_id")
    if not booking_id:
        return ConversationHandler.END

    text = update.message.text.strip()
    try:
        lesson_dt = datetime.strptime(text, "%d.%m.%Y %H:%M")
    except ValueError:
        await update.message.reply_text(
            "Неверный формат. Введите дату: <b>ДД.ММ.ГГГГ ЧЧ:ММ</b>\n"
            "Например: 01.06.2025 17:00",
            parse_mode="HTML",
        )
        return SET_DATETIME

    booking = await get_booking_by_id(booking_id)
    await confirm_booking(booking_id, lesson_dt.isoformat())
    await update.message.reply_text(f"✅ Заявка #{booking_id} подтверждена на {text}.")

    try:
        fmt = "Индивидуально" if booking["format"] == "individual" else "Мини-группа"
        await context.bot.send_message(
            chat_id=booking["user_id"],
            text=(
                f"✅ <b>Занятие подтверждено!</b>\n\n"
                f"Здравствуйте, {booking['name']}!\n"
                f"Ваше пробное занятие запланировано на <b>{text}</b>.\n"
                f"Формат: {fmt}\n\n"
                "Вы получите напоминание за 24 часа и за 1 час до начала.\n"
                f"Если есть вопросы — @{TUTOR_USERNAME}"
            ),
            parse_mode="HTML",
        )
    except Exception:
        pass

    return ConversationHandler.END


async def skip_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    booking_id = context.user_data.get("confirming_booking_id")
    if not booking_id:
        return ConversationHandler.END

    booking = await get_booking_by_id(booking_id)
    await confirm_booking(booking_id, None)
    await update.message.reply_text(f"✅ Заявка #{booking_id} подтверждена (без даты).")

    try:
        await context.bot.send_message(
            chat_id=booking["user_id"],
            text=(
                f"✅ <b>Заявка подтверждена!</b>\n\n"
                f"Здравствуйте, {booking['name']}! Репетитор свяжется с вами для уточнения времени.\n"
                f"Если есть вопросы — @{TUTOR_USERNAME}"
            ),
            parse_mode="HTML",
        )
    except Exception:
        pass

    return ConversationHandler.END


def get_admin_conversation():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_confirm_callback, pattern="^confirm_")],
        states={
            SET_DATETIME: [
                CommandHandler("skip", skip_datetime),
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_datetime),
            ]
        },
        fallbacks=[],
        per_user=True,
        per_chat=False,
    )
