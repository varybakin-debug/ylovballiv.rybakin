import aiosqlite
from datetime import datetime, timedelta
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                subject TEXT NOT NULL,
                format TEXT NOT NULL,
                preferred_time TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                lesson_datetime TEXT,
                reminder_sent_24h INTEGER DEFAULT 0,
                reminder_sent_1h INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def add_booking(user_id, username, name, phone, subject, format_, preferred_time):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO bookings (user_id, username, name, phone, subject, format, preferred_time)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, username, name, phone, subject, format_, preferred_time),
        )
        await db.commit()
        return cursor.lastrowid


async def get_booking_by_id(booking_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
        return await cursor.fetchone()


async def get_pending_bookings():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM bookings WHERE status = 'pending' ORDER BY created_at DESC"
        )
        return await cursor.fetchall()


async def get_all_bookings():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM bookings ORDER BY created_at DESC")
        return await cursor.fetchall()


async def confirm_booking(booking_id, lesson_datetime):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE bookings SET status = 'confirmed', lesson_datetime = ? WHERE id = ?",
            (lesson_datetime, booking_id),
        )
        await db.commit()


async def cancel_booking(booking_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,)
        )
        await db.commit()


async def get_upcoming_reminders():
    now = datetime.now()
    window_24h_start = now + timedelta(hours=23, minutes=30)
    window_24h_end = now + timedelta(hours=24, minutes=30)
    window_1h_start = now + timedelta(minutes=50)
    window_1h_end = now + timedelta(hours=1, minutes=10)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """SELECT * FROM bookings
               WHERE status = 'confirmed' AND lesson_datetime IS NOT NULL
               AND reminder_sent_24h = 0
               AND lesson_datetime BETWEEN ? AND ?""",
            (window_24h_start.isoformat(), window_24h_end.isoformat()),
        )
        remind_24h = await cursor.fetchall()

        cursor = await db.execute(
            """SELECT * FROM bookings
               WHERE status = 'confirmed' AND lesson_datetime IS NOT NULL
               AND reminder_sent_1h = 0
               AND lesson_datetime BETWEEN ? AND ?""",
            (window_1h_start.isoformat(), window_1h_end.isoformat()),
        )
        remind_1h = await cursor.fetchall()

    return remind_24h, remind_1h


async def mark_reminder_sent(booking_id, reminder_type):
    field = f"reminder_sent_{reminder_type}"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE bookings SET {field} = 1 WHERE id = ?", (booking_id,))
        await db.commit()
