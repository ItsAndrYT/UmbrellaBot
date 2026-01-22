import aiosqlite
import datetime

DATABASE_PATH = "database.db"

# ===== ИНИЦИАЛИЗАЦИЯ БАЗЫ =====
async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Таблица пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                bonus_balance INTEGER DEFAULT 0,
                first_purchase_done INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица заказов
        await db.execute('''
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
                
                status TEXT DEFAULT 'pending',  -- pending, proof_required, approved, rejected
                proof_text TEXT,
                proof_photo_id TEXT,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица бонусных операций
        await db.execute('''
            CREATE TABLE IF NOT EXISTS bonus_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                reason TEXT,
                order_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        await db.commit()
        print("✅ База данных инициализирована")

# ===== ПОЛЬЗОВАТЕЛИ =====
async def upsert_user(user_id: int, username: str = None):
    """Добавить или обновить пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            INSERT OR REPLACE INTO users (user_id, username, updated_at)
            VALUES (?, ?, ?)
        ''', (user_id, username, datetime.datetime.now().isoformat()))
        await db.commit()

async def get_user(user_id: int):
    """Получить пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT * FROM users WHERE user_id = ?", 
            (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        return None

async def set_first_purchase_done(user_id: int):
    """Отметить первую покупку как выполненную"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET first_purchase_done = 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()

# ===== ЗАКАЗЫ =====
async def create_order(
    user_id: int,
    username: str,
    level_key: str,
    level_title: str,
    country_code: str,
    country_label: str,
    pay_method: str,
    stars_base_price: int = None,
    stars_newbie_discount: int = None,
    stars_bonus_used: int = None,
    stars_final_price: int = None,
    uah_final_price: int = None
):
    """Создать новый заказ"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO orders (
                user_id, username, level_key, level_title,
                country_code, country_label, pay_method,
                stars_base_price, stars_newbie_discount,
                stars_bonus_used, stars_final_price,
                uah_final_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, username, level_key, level_title,
            country_code, country_label, pay_method,
            stars_base_price, stars_newbie_discount,
            stars_bonus_used, stars_final_price,
            uah_final_price
        ))
        await db.commit()
        return cursor.lastrowid

async def get_order(order_id: int):
    """Получить заказ по ID"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT * FROM orders WHERE id = ?", 
            (order_id,)
        )
        row = await cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        return None

async def set_order_status(order_id: int, status: str):
    """Изменить статус заказа"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.datetime.now().isoformat(), order_id)
        )
        await db.commit()

async def add_proof(order_id: int, user_id: int, text: str = None, photo_id: str = None):
    """Добавить подтверждение оплаты"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            UPDATE orders 
            SET proof_text = ?, proof_photo_id = ?, status = 'proof_required', updated_at = ?
            WHERE id = ? AND user_id = ?
        ''', (text, photo_id, datetime.datetime.now().isoformat(), order_id, user_id))
        await db.commit()

async def list_user_orders(user_id: int):
    """Получить все заказы пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        rows = await cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

# ===== БОНУСЫ =====
async def add_bonus(user_id: int, amount: int, reason: str = "admin", order_id: int = None):
    """Добавить бонусы пользователю"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Добавляем в историю
        await db.execute('''
            INSERT INTO bonus_transactions (user_id, amount, reason, order_id)
            VALUES (?, ?, ?, ?)
        ''', (user_id, amount, reason, order_id))
        
        # Обновляем баланс
        await db.execute('''
            UPDATE users 
            SET bonus_balance = bonus_balance + ?, updated_at = ?
            WHERE user_id = ?
        ''', (amount, datetime.datetime.now().isoformat(), user_id))
        
        await db.commit()

async def consume_bonus(user_id: int, amount: int):
    """Списать бонусы"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Добавляем в историю (отрицательная сумма)
        await db.execute('''
            INSERT INTO bonus_transactions (user_id, amount, reason)
            VALUES (?, ?, ?)
        ''', (user_id, -amount, "order_payment"))
        
        # Обновляем баланс
        await db.execute('''
            UPDATE users 
            SET bonus_balance = bonus_balance - ?, updated_at = ?
            WHERE user_id = ?
        ''', (amount, datetime.datetime.now().isoformat(), user_id))
        
        await db.commit()

# ===== АДМИН СТАТИСТИКА =====
async def get_all_orders(limit: int = 100):
    """Получить все заказы (для админа)"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

async def get_stats():
    """Получить статистику (для админа)"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Общее количество заказов
        cursor = await db.execute("SELECT COUNT(*) FROM orders")
        total_orders = (await cursor.fetchone())[0]
        
        # Заказы по статусам
        cursor = await db.execute("""
            SELECT status, COUNT(*) as count 
            FROM orders 
            GROUP BY status
        """)
        status_stats = {row[0]: row[1] for row in await cursor.fetchall()}
        
        # Общая выручка
        cursor = await db.execute("""
            SELECT 
                SUM(stars_final_price) as total_stars,
                SUM(uah_final_price) as total_uah
            FROM orders 
            WHERE status = 'approved'
        """)
        revenue_row = await cursor.fetchone()
        
        return {
            "total_orders": total_orders,
            "status_stats": status_stats,
            "total_stars": revenue_row[0] or 0,
            "total_uah": revenue_row[1] or 0
        }
