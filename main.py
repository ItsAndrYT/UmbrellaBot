import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

from config import (
    BOT_TOKEN, ADMIN_ID, SUPPORT_USERNAME, PAY_STARS_USERNAME,
    UA_CARD_INFO, UA_CARD_NAME, NEWBIE_DISCOUNT_STARS,
    REQUIRED_CHANNEL, REVIEWS_URL
)
from keyboards import (
    kb_main, kb_levels, kb_countries, kb_pay, kb_after_invoice, kb_admin,
    kb_subscribe
)
from db import (
    init_db, upsert_user, get_user, create_order, get_order,
    set_order_status, add_proof, set_first_purchase_done,
    add_bonus, consume_bonus, list_user_orders
)

# ===== Цены =====
STARS_PRICE = {"basic": 25, "premium": 50}
UAH_PRICE = {"basic": 15, "premium": 30}

CATALOG = {
    "basic": {
        "title": "🔹 BASIC",
        "countries": [
            ("IN", "🇮🇳 Индия"),
            ("ID", "🇮🇩 Индонезия"),
            ("PH", "🇵🇭 Филиппины"),
            ("TH", "🇹🇭 Таиланд"),
            ("MY", "🇲🇾 Малайзия"),
            ("BD", "🇧🇩 Бангладеш"),
            ("MM", "🇲🇲 Мьянма"),
            ("NG", "🇳🇬 Нигерия"),
            ("KE", "🇰🇪 Кения"),
            ("EG", "🇪🇬 Египет"),
            ("PE", "🇵🇪 Перу"),
        ],
    },
    "premium": {
        "title": "⭐ PREMIUM",
        "countries": [
            ("US", "🇺🇸 США"),
            ("CA", "🇨🇦 Канада"),
            ("UA", "🇺🇦 Украина"),
            ("BY", "🇧🇾 Беларусь"),
        ],
    }
}

GUARANTEE_TEXT = (
    "🛡 Гарантия 48 часов\n"
    "В случае проблем с аккаунтом в течение 48 часов — замена."
)

HOW_TEXT = (
    "📘 Как происходит покупка:\n"
    "1) Выбираешь уровень и страну\n"
    "2) Выбираешь оплату (⭐ Stars / 🇺🇦 карта)\n"
    "3) Нажимаешь «Я оплатил»\n"
    "4) Отправляешь скрин/пруф\n"
    "5) Я подтверждаю — и выдаю аккаунт\n\n"
    "⭐ Stars: оплата подарком на аккаунт @QweAndrey."
)

WAITING_PROOF: dict[int, int] = {}

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ===== HELPERS =====
def channel_url(required: str) -> str:
    return f"https://t.me/{required.lstrip('@')}" if required.startswith("@") else ""

def main_menu_markup():
    return kb_main(
        SUPPORT_USERNAME,
        reviews_url=REVIEWS_URL,
        channel_url=channel_url(REQUIRED_CHANNEL)
    )

async def is_subscribed(user_id: int) -> bool:
    if not REQUIRED_CHANNEL:
        return True
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ("member", "administrator", "creator")
    except TelegramBadRequest:
        return False

def country_label(level_key: str, code: str) -> str:
    for c, label in CATALOG[level_key]["countries"]:
        if c == code:
            return label
    return code

def calc_stars_price(base_price: int, is_newbie: bool, bonus_balance: int):
    newbie_discount = NEWBIE_DISCOUNT_STARS if is_newbie else 0
    after_newbie = max(0, base_price - newbie_discount)
    bonus_used = min(bonus_balance, after_newbie)
    final_price = after_newbie - bonus_used
    return newbie_discount, bonus_used, final_price

def pay_text(method: str, stars_amount: int | None, uah_amount: int | None):
    if method == "stars":
        return (
            f"⭐ Оплата Stars подарком на аккаунт @{PAY_STARS_USERNAME}\n"
            f"Сумма: {stars_amount}⭐\n\nПосле оплаты нажми «Я оплатил» и отправь подтверждение."
        )
    name_line = f"\nПолучатель: {UA_CARD_NAME}" if UA_CARD_NAME else ""
    return (
        f"🇺🇦 Оплата картой Украины\n{UA_CARD_INFO}{name_line}\n"
        f"Сумма: {uah_amount} грн 🇺🇦\n\nПосле оплаты нажми «Я оплатил» и отправь скрин перевода."
    )

async def show_sub_gate(target: Message | CallbackQuery):
    text = "☂️ Чтобы пользоваться ботом, подпишись на наш канал 👇\n\nПосле подписки нажми «Проверить подписку»."
    if isinstance(target, Message):
        await target.answer(text, reply_markup=kb_subscribe(channel_url(REQUIRED_CHANNEL)))
    else:
        await target.message.edit_text(text, reply_markup=kb_subscribe(channel_url(REQUIRED_CHANNEL)))

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def mention(msg: Message):
    return f"<a href='tg://user?id={msg.from_user.id}'>{msg.from_user.full_name}</a>"

# ===== START =====
@dp.message(CommandStart())
async def start(msg: Message):
    await upsert_user(msg.from_user.id, msg.from_user.username)
    if not await is_subscribed(msg.from_user.id):
        await show_sub_gate(msg)
        return
    await msg.answer(
        "☂️ UmbrellaTeam\n\n"
        f"🎁 Новым клиентам: –{NEWBIE_DISCOUNT_STARS}⭐ на первый Stars-заказ\n\n"
        "Выбирай действие 👇",
        reply_markup=main_menu_markup()
    )

# ===== CALLBACKS =====
@dp.callback_query(F.data == "m:home")
async def cb_home(cb: CallbackQuery):
    if not await is_subscribed(cb.from_user.id):
        await show_sub_gate(cb)
        await cb.answer()
        return
    await cb.message.edit_text("Выберите действие:", reply_markup=main_menu_markup())
    await cb.answer()

@dp.callback_query(F.data == "m:buy")
async def cb_buy(cb: CallbackQuery):
    if not await is_subscribed(cb.from_user.id):
        await show_sub_gate(cb)
        await cb.answer()
        return
    await cb.message.edit_text("Выберите уровень:", reply_markup=kb_levels())
    await cb.answer()

@dp.callback_query(F.data.startswith("lvl:"))
async def cb_level(cb: CallbackQuery):
    if not await is_subscribed(cb.from_user.id):
        await show_sub_gate(cb)
        await cb.answer()
        return
    level_key = cb.data.split(":")[1]
    stars = STARS_PRICE[level_key]
    uah = UAH_PRICE[level_key]
    await cb.message.edit_text(
        f"{CATALOG[level_key]['title']}\n⭐ Stars: {stars}⭐\n🇺🇦 Карта: {uah} грн\n\nВыберите страну:",
        reply_markup=kb_countries(level_key, CATALOG[level_key]["countries"])
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("cty:"))
async def cb_country(cb: CallbackQuery):
    if not await is_subscribed(cb.from_user.id):
        await show_sub_gate(cb)
        await cb.answer()
        return
    _, level_key, code = cb.data.split(":")
    has_card = bool(UA_CARD_INFO.strip())
    await cb.message.edit_text(
        f"{CATALOG[level_key]['title']}\nСтрана: {country_label(level_key, code)}\n\nВыберите оплату:",
        reply_markup=kb_pay(level_key, code, has_card)
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("pay:"))
async def cb_pay(cb: CallbackQuery):
    if not await is_subscribed(cb.from_user.id):
        await show_sub_gate(cb)
        await cb.answer()
        return
    _, level_key, code, method = cb.data.split(":")
    await upsert_user(cb.from_user.id, cb.from_user.username)
    user = await get_user(cb.from_user.id)

    lvl_title = CATALOG[level_key]["title"]
    c_label = country_label(level_key, code)

    if method == "stars":
        base = STARS_PRICE[level_key]
        is_newbie = (user["first_purchase_done"] == 0)
        bonus_balance = int(user["bonus_balance"])
        newbie_discount, bonus_used, final_price = calc_stars_price(base, is_newbie, bonus_balance)

        order_id = await create_order(
            user_id=cb.from_user.id,
            username=cb.from_user.username,
            level_key=level_key,
            level_title=lvl_title,
            country_code=code,
            country_label=c_label,
            pay_method="stars",
            stars_base_price=base,
            stars_newbie_discount=newbie_discount,
            stars_bonus_used=bonus_used,
            stars_final_price=final_price
        )

        text = (
            f"🧾 Заказ #{order_id}\nУровень: {lvl_title}\nСтрана: {c_label}\n"
            f"Цена: {base}⭐\n"
        )
        if newbie_discount: text += f"🎁 Скидка новичка: –{newbie_discount}⭐\n"
        if bonus_used: text += f"🎁 Списано бонусов: –{bonus_used}⭐\n"
        text += f"К оплате: {final_price}⭐\n\n" + pay_text("stars", final_price, None)
        await cb.message.edit_text(text, reply_markup=kb_after_invoice(order_id))
        await cb.answer()
        return

    # card
    uah = UAH_PRICE[level_key]
    order_id = await create_order(
        user_id=cb.from_user.id,
        username=cb.from_user.username,
        level_key=level_key,
        level_title=lvl_title,
        country_code=code,
        country_label=c_label,
        pay_method="card",
        uah_final_price=uah
    )
    text = f"🧾 Заказ #{order_id}\nУровень: {lvl_title}\nСтрана: {c_label}\nК оплате: {uah} грн 🇺🇦\n\n" + pay_text("card", None, uah)
    await cb.message.edit_text(text, reply_markup=kb_after_invoice(order_id))
    await cb.answer()

@dp.callback_query(F.data.startswith("paid:"))
async def cb_paid(cb: CallbackQuery):
    order_id = int(cb.data.split(":")[1])
    order = await get_order(order_id)
    if not order or int(order["user_id"]) != cb.from_user.id:
        await cb.answer("Заказ не найден.", show_alert=True)
        return
    await set_order_status(order_id, "proof_required")
    WAITING_PROOF[cb.from_user.id] = order_id
    await cb.message.edit_text(
        f"✅ Заказ #{order_id} отмечен как оплаченный.\nТеперь отправь подтверждение (скрин/текст)."
    )
    await cb.answer()

# ===== ПРУФЫ =====
@dp.message(F.photo)
async def proof_photo(msg: Message):
    if msg.from_user.id not in WAITING_PROOF:
        return
    order_id = WAITING_PROOF.pop(msg.from_user.id)
    file_id = msg.photo[-1].file_id
    await add_proof(order_id, msg.from_user.id, msg.caption, file_id)
    order = await get_order(order_id)
    method = order["pay_method"]
    price_line = f"{order['stars_final_price']}⭐" if method=="stars" else f"{order['uah_final_price']} грн 🇺🇦"
    caption = (
        f"🔔 Пруф оплаты (фото)\nЗаказ #{order_id}\nПользователь: {mention(msg)}\n"
        f"{order['level_title']} | {order['country_label']}\nК оплате: {price_line}\nМетод: {method}"
    )
    await bot.send_photo(ADMIN_ID, file_id, caption=caption, reply_markup=kb_admin(order_id))
    await msg.answer("Принял ✅ Проверяю, скоро отвечу в личке.")

@dp.message(F.text)
async def proof_text(msg: Message):
    if msg.from_user.id not in WAITING_PROOF:
        return
    order_id = WAITING_PROOF.pop(msg.from_user.id)
    await add_proof(order_id, msg.from_user.id, msg.text, None)
    order = await get_order(order_id)
    method = order["pay_method"]
    price_line = f"{order['stars_final_price']}⭐" if method=="stars" else f"{order['uah_final_price']} грн 🇺🇦"
    text = (
        f"🔔 Пруф оплаты (текст)\nЗаказ #{order_id}\nПользователь: {mention(msg)}\n"
        f"{order['level_title']} | {order['country_label']}\nК оплате: {price_line}\nМетод: {method}\n\n"
        f"Текст:\n{msg.text}"
    )
    await bot.send_message(ADMIN_ID, text, reply_markup=kb_admin(order_id))
    await msg.answer("Принял ✅ Проверяю, скоро отвечу в личке.")

# ===== ADMIN =====
@dp.callback_query(F.data.startswith("adm:"))
async def admin_actions(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("Нет доступа.", show_alert=True)
        return
    _, action, order_id_s, *rest = cb.data.split(":")
    order_id = int(order_id_s)
    order = await get_order(order_id)
    if not order:
        await cb.answer("Заказ не найден.", show_alert=True)
        return
    user_id = int(order["user_id"])
    if action == "ok":
        if order["pay_method"]=="stars":
            bonus_used = int(order["stars_bonus_used"] or 0)
            if bonus_used>0: await consume_bonus(user_id, bonus_used)
            await set_first_purchase_done(user_id)
        await set_order_status(order_id, "approved")
        await bot.send_message(user_id, f"✅ Оплата подтверждена.\nЗаказ #{order_id}\nНапиши в поддержку: https://t.me/{SUPPORT_USERNAME}")
        await cb.answer("Подтверждено ✅")
    elif action=="no":
        await set_order_status(order_id, "rejected")
        await bot.send_message(user_id, f"❌ Оплата не подтверждена.\nЗаказ #{order_id}\nЕсли ошибка — отправь снова или напиши в поддержку: https://t.me/{SUPPORT_USERNAME}")
        await cb.answer("Отклонено ❌")
    elif action=="bonus":
        amount = int(rest[0]) if rest else 5
        await add_bonus(user_id, amount)
        await bot.send_message(user_id, f"🎁 Начислен бонус: +{amount}⭐")
        await cb.answer(f"Бонус +{amount} ✅")

# ===== MAIN =====
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
