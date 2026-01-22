import aiosqlite
from datetime import datetime

DB_PATH = "database.db"


# ================= INIT =================

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_purchase_done INTEGER DEFAULT 0,
            bonus_balance INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            level_key TEXT,
            level_title TEXT,
            country_code TEXT,
            country_label TEXT,
            pay_method TEXT,
            stars_base_price INTEGER,
            stars_newbie_discount INTEGER,
            stars_bonus_used INTEGER,
            stars_final_price INTEGER,
            uah_final_price INTEGER,
            status TEXT DEFAULT 'created',
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS proofs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            user_id INTEGER,
            text_proof TEXT,
            photo_file_id TEXT,
            created_at TEXT
        );
        """)
        await db.commit()


# ================= USERS =================

async def upsert_user(user_id: int, username: str | None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO users (user_id, username)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET username=excluded.username
        """, (user_id, username))
        await db.commit()


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        if not row:
            return {
                "user_id": user_id,
                "first_purchase_done": 0,
                "bonus_balance": 0
            }
        return {
            "user_id": row[0],
            "username": row[1],
            "first_purchase_done": row[2],
            "bonus_balance": row[3]
        }


async def set_first_purchase_done(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET first_purchase_done=1 WHERE user_id=?",
            (user_id,)
        )
        await db.commit()


async def add_bonus(user_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET bonus_balance = bonus_balance + ? WHERE user_id=?",
            (amount, user_id)
        )
        await db.commit()


async def consume_bonus(user_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET bonus_balance = bonus_balance - ? WHERE user_id=?",
            (amount, user_id)
        )
        await db.commit()


# ================= ORDERS =================

async def create_order(
    user_id: int,
    username: str | None,
    level_key: str,
    level_title: str,
    country_code: str,
    country_label: str,
    pay_method: str,
    stars_base_price: int | None = None,
    stars_newbie_discount: int | None = None,
    stars_bonus_used: int | None = None,
    stars_final_price: int | None = None,
    uah_final_price: int | None = None
):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
        INSERT INTO orders (
            user_id, username, level_key, level_title,
            country_code, country_label, pay_method,
            stars_base_price, stars_newbie_discount,
            stars_bonus_used, stars_final_price,
            uah_final_price, status, created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            user_id, username, level_key, level_title,
            country_code, country_label, pay_method,
            stars_base_price, stars_newbie_discount,
            stars_bonus_used, stars_final_price,
            uah_final_price,
            "created",
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ))
        await db.commit()
        return cur.lastrowid


async def get_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
        SELECT id, user_id, username, level_key, level_title,
               country_code, country_label, pay_method,
               stars_base_price, stars_newbie_discount,
               stars_bonus_used, stars_final_price,
               uah_final_price, status, created_at, updated_at
        FROM orders WHERE id=?
        """, (order_id,))
        row = await cur.fetchone()
        if not row:
            return None

        keys = [
            "id","user_id","username","level_key","level_title",
            "country_code","country_label","pay_method",
            "stars_base_price","stars_newbie_discount",
            "stars_bonus_used","stars_final_price",
            "uah_final_price","status","created_at","updated_at"
        ]
        return dict(zip(keys, row))


async def set_order_status(order_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET status=?, updated_at=? WHERE id=?",
            (status, datetime.utcnow().isoformat(), order_id)
        )
        await db.commit()


async def list_user_orders(user_id: int, limit: int = 15, status: str = "approved"):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
        SELECT id, level_title, country_label, pay_method,
               COALESCE(stars_final_price, 0),
               COALESCE(uah_final_price, 0),
               created_at
        FROM orders
        WHERE user_id=? AND status=?
        ORDER BY id DESC
        LIMIT ?
        """, (user_id, status, limit))
        return await cur.fetchall()


# ================= PROOFS =================

async def add_proof(
    order_id: int,
    user_id: int,
    text_proof: str | None,
    photo_file_id: str | None
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO proofs (
            order_id, user_id, text_proof, photo_file_id, created_at
        ) VALUES (?,?,?,?,?)
        """, (
            order_id, user_id,
            text_proof, photo_file_id,
            datetime.utcnow().isoformat()
        ))
        await db.commit()
