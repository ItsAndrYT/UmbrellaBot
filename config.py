import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0").strip() or "0")

SUPPORT_USERNAME = (os.getenv("SUPPORT_USERNAME") or "TakeTGOwner").lstrip("@")
PAY_STARS_USERNAME = (os.getenv("PAY_STARS_USERNAME") or "QweAndrey").lstrip("@")

REQUIRED_CHANNEL = (os.getenv("REQUIRED_CHANNEL") or "").strip()
REVIEWS_URL = (os.getenv("REVIEWS_URL") or "").strip()

UA_CARD_INFO = (os.getenv("UA_CARD_INFO") or "").strip()
UA_CARD_NAME = (os.getenv("UA_CARD_NAME") or "").strip()

NEWBIE_DISCOUNT_STARS = int(os.getenv("NEWBIE_DISCOUNT_STARS", "5"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в .env")
if ADMIN_ID == 0:
    raise RuntimeError("ADMIN_ID не задан в .env")