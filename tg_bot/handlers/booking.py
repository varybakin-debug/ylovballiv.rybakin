import re
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from database import add_booking
from config import ADMINS_BY_SUBJECT, TUTOR_USERNAME, PRICE_INDIVIDUAL, PRICE_GROUP

ASK_SUBJECT, ASK_NAME, ASK_PHONE, ASK_FORMAT, ASK_TIME = range(5)

_SUBJECT_KEYBOARD = ReplyKeyboardMarkup(
    [["📐 Математика (ОГЭ)", "⚗️ Физика (ОГЭ)"]],
    resize_keyboard=True,
    one_time_keyboard=True,
)

_FORMAT_KEYBOARD = ReplyKeyboardMarkup(
    [[
        f"👤 Индивидуально ({PRICE_INDIVIDUAL:,} ₽/час)".replace(",", " "),
        f"👥 Мини-группа ({PRICE_GROUP:,} ₽/час)".replace(",", " "),
    ]],
    resize_keyboard=True,
    one_time_keyboard=True,
)

_CANCEL_KEYBOARD = ReplyKeyboardMarkup(
    [["❌ Отменить"]],
    resize_keyboard=True,
    one_time_keyboard=True,
)

SUBJECT_LABELS = {
    "math": "📐 Математика (ОГЭ)",
    "physics": "⚗️ Физика (ОГЭ)",
}


async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "📝 <b>Запись на пробное занятие</b>\n\n"
        "Выберите предмет:",
        reply_markup=_SUBJECT_KEYBOARD,
    )
    return ASK_SUBJECT


async def _ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отменить":
        return await cancel(update, context)

    text = update.message.text
    if "Математика" in text:
        context.user_data["subject"] = "math"
    elif "Физика" in text:
        context.user_data["subject"] = "physics"
    else:
        await update.message.reply_text(
            "Выберите предмет из предложенных вариантов.", reply_markup=_SUBJECT_KEYBOARD
        )
        return ASK_SUBJECT

    await update.message.reply_html(
        f"Отлично, <b>{SUBJECT_LABELS[context.user_data['subject']]}</b>!\n\n"
        "Как вас зовут?\n"
        "<i>(Имя ребёнка или ваше, если записываете себя)</i>",
        reply_markup=_CANCEL_KEYBOARD,
    )
    return ASK_NAME


async def _ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отменить":
        return await cancel(update, context)

    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("Пожалуйста, введите имя (минимум 2 символа).")
        return ASK_NAME

    context.user_data["name"] = name
    await update.message.reply_text(
        f"Приятно познакомиться, {name}! 😊\n\nУкажите ваш номер телефона:",
        reply_markup=_CANCEL_KEYBOARD,
    )
    return ASK_PHONE


async def _ask_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отменить":
        return await cancel(update, context)

    phone = update.message.text.strip()
    if len(re.sub(r"\D", "", phone)) < 10:
        await update.message.reply_text(
            "Пожалуйста, введите корректный номер телефона (минимум 10 цифр)."
        )
        return ASK_PHONE

    context.user_data["phone"] = phone
    await update.message.reply_text(
        "Какой формат занятий вас интересует?",
        reply_markup=_FORMAT_KEYBOARD,
    )
    return ASK_FORMAT


async def _ask_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отменить":
        return await cancel(update, context)

    text = update.message.text
    if "Индивидуально" in text:
        context.user_data["format"] = "individual"
        context.user_data["format_name"] = f"Индивидуально ({PRICE_INDIVIDUAL:,} ₽/час)".replace(",", " ")
    elif "Мини-группа" in text:
        context.user_data["format"] = "group"
        context.user_data["format_name"] = f"Мини-группа ({PRICE_GROUP:,} ₽/час)".replace(",", " ")
    else:
        await update.message.reply_text(
            "Выберите формат из предложенных вариантов.", reply_markup=_FORMAT_KEYBOARD
        )
        return ASK_FORMAT

    await update.message.reply_html(
        "Когда вам удобно заниматься?\n\n"
        "Напишите удобные дни и примерное время.\n"
        "<i>Например: будние дни после 17:00, или суббота утром</i>",
        reply_markup=_CANCEL_KEYBOARD,
    )
    return ASK_TIME


async def _finish_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отменить":
        return await cancel(update, context)

    preferred_time = update.message.text.strip()
    if len(preferred_time) < 3:
        await update.message.reply_text("Пожалуйста, опишите удобное время подробнее.")
        return ASK_TIME

    user = update.effective_user
    subject = context.user_data["subject"]

    booking_id = await add_booking(
        user_id=user.id,
        username=user.username,
        name=context.user_data["name"],
        phone=context.user_data["phone"],
        subject=subject,
        format_=context.user_data["format"],
        preferred_time=preferred_time,
    )

    subject_label = SUBJECT_LABELS[subject]
    admin_text = (
        f"🔔 <b>Новая заявка #{booking_id}</b>\n\n"
        f"📖 Предмет: {subject_label}\n"
        f"👤 Имя: {context.user_data['name']}\n"
        f"📱 Телефон: {context.user_data['phone']}\n"
        f"📚 Формат: {context.user_data['format_name']}\n"
        f"🕐 Удобное время: {preferred_time}\n\n"
        f"Telegram: {'@' + user.username if user.username else str(user.id)}"
    )
    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{booking_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{booking_id}"),
        ]]
    )

    for admin_id in ADMINS_BY_SUBJECT[subject]:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        except Exception:
            pass

    from handlers.start import MAIN_MENU
    await update.message.reply_html(
        f"✅ <b>Заявка принята!</b>\n\n"
        f"Спасибо, {context.user_data['name']}! Я получил вашу заявку и свяжусь с вами "
        f"по номеру {context.user_data['phone']} в ближайшее время.\n\n"
        f"Если есть вопросы — напишите напрямую: @{TUTOR_USERNAME}",
        reply_markup=MAIN_MENU,
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.start import MAIN_MENU
    context.user_data.clear()
    await update.message.reply_text(
        "Запись отменена. Если передумаете — я всегда здесь! 😊",
        reply_markup=MAIN_MENU,
    )
    return ConversationHandler.END


def get_booking_conversation():
    return ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex("^📝 Записаться на пробное занятие$"), start_booking
            )
        ],
        states={
            ASK_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_name)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_phone)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_format)],
            ASK_FORMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_time)],
            ASK_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, _finish_booking)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=600,
    )
