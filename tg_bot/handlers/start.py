from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["📚 Об услугах и ценах"],
        ["📝 Записаться на пробное занятие"],
        ["❓ Частые вопросы"],
    ],
    resize_keyboard=True,
)

_INFO_TEXT = """
📐 <b>Репетитор по математике (ОГЭ)</b>

Подготовка к ОГЭ онлайн: выход на 4–5 за 2–3 месяца, без зубрёжки.

<b>Форматы и цены:</b>
• Индивидуально — 2 000 ₽/час
• Мини-группа — 800 ₽/час

<b>Как проходят занятия:</b>
• Онлайн (Zoom / Google Meet)
• Разбор темы + практика
• Домашнее задание с проверкой

<b>Кому подойдёт:</b>
• Если сейчас 2–3 и нужно выйти на 4
• Если есть пробелы в знаниях
• Если боишься экзамена
"""

_FAQ_TEXT = """
❓ <b>Частые вопросы</b>

<b>Как проходит пробное занятие?</b>
60 минут: разбираем текущий уровень и составляем план подготовки. Стоимость — 2 000 ₽.

<b>Как оплачивать?</b>
Онлайн-переводом после каждого занятия или пакетом (4–8 занятий со скидкой).

<b>Как записаться?</b>
Нажмите «Записаться на пробное занятие» — свяжусь в течение нескольких часов.

<b>Есть ли группы?</b>
Да! Мини-группы по 2–3 человека: 800 ₽/час с каждого.
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! 👋 Я помогу записаться на занятия по математике для подготовки к ОГЭ.\n\n"
        "Выберите, что вас интересует:",
        reply_markup=MAIN_MENU,
    )


async def info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(_INFO_TEXT, reply_markup=MAIN_MENU)


async def faq_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(_FAQ_TEXT, reply_markup=MAIN_MENU)
