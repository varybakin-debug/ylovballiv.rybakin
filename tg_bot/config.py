import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ALL_ID = int(os.getenv("ADMIN_ALL_ID", "1064422766"))    # математика + физика
ADMIN_PHYSICS_ID = int(os.getenv("ADMIN_PHYSICS_ID", "743587196"))  # только физика
DB_PATH = os.getenv("DB_PATH", "bot.db")
TUTOR_USERNAME = "ylovballov"

PRICE_INDIVIDUAL = 3490
PRICE_GROUP = 990

ADMINS_BY_SUBJECT = {
    "math": [ADMIN_ALL_ID],
    "physics": [ADMIN_ALL_ID, ADMIN_PHYSICS_ID],
}
