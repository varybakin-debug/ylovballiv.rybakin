import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from database import get_upcoming_reminders, mark_reminder_sent

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()
_bot = None


async def _check_reminders():
    if _bot is None:
        return
    remind_24h, remind_1h = await get_upcoming_reminders()

    for booking in remind_24h:
        from datetime import datetime
        dt = datetime.fromisoformat(booking["lesson_datetime"])
        try:
            await _bot.send_message(
                chat_id=booking["user_id"],
                text=(
                    f"⏰ <b>Напоминание о занятии</b>\n\n"
                    f"Здравствуйте, {booking['name']}!\n"
                    f"Завтра в <b>{dt.strftime('%H:%M')}</b> у вас занятие по математике.\n\n"
                    "До встречи! 📐"
                ),
                parse_mode="HTML",
            )
            await mark_reminder_sent(booking["id"], "24h")
        except Exception as e:
            logger.warning("Failed to send 24h reminder for booking %s: %s", booking["id"], e)

    for booking in remind_1h:
        from datetime import datetime
        dt = datetime.fromisoformat(booking["lesson_datetime"])
        try:
            await _bot.send_message(
                chat_id=booking["user_id"],
                text=(
                    f"🔔 <b>Занятие через час!</b>\n\n"
                    f"Здравствуйте, {booking['name']}!\n"
                    f"Напоминаем: занятие сегодня в <b>{dt.strftime('%H:%M')}</b>.\n\n"
                    "Ссылку на встречу пришлёт репетитор. 🎓"
                ),
                parse_mode="HTML",
            )
            await mark_reminder_sent(booking["id"], "1h")
        except Exception as e:
            logger.warning("Failed to send 1h reminder for booking %s: %s", booking["id"], e)


def setup_scheduler(bot):
    global _bot
    _bot = bot
    scheduler.add_job(_check_reminders, IntervalTrigger(minutes=30), id="reminders")
    scheduler.start()
    logger.info("Scheduler started")
