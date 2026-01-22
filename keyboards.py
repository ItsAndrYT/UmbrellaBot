from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# ===== ГЛАВНОЕ МЕНЮ =====
def kb_main(support_username: str, reviews_url: str = "", channel_url: str = ""):
    """Главное меню бота"""
    buttons = [
        [
            InlineKeyboardButton(text="🛒 Купить", callback_data="m:buy"),
            InlineKeyboardButton(text="📦 Мои покупки", callback_data="m:purchases")
        ],
        [
            InlineKeyboardButton(text="❓ Как купить", callback_data="m:how"),
            InlineKeyboardButton(text="🛡 Гарантия", callback_data="m:guarantee")
        ],
        [
            InlineKeyboardButton(text="⭐ Отзывы", callback_data="m:reviews"),
            InlineKeyboardButton(text="💬 Поддержка", url=f"https://t.me/{support_username}")
        ]
    ]
    
    # Добавляем кнопку канала если есть
    if channel_url:
        buttons.append([
            InlineKeyboardButton(text="📢 Наш канал", url=channel_url)
        ])
    
    # Добавляем кнопку отзывов если есть URL
    if reviews_url:
        # Обновляем кнопку отзывов на URL
        buttons[2][0] = InlineKeyboardButton(text="⭐ Отзывы", url=reviews_url)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ===== ВЫБОР УРОВНЯ =====
def kb_levels():
    """Клавиатура выбора уровня"""
    buttons = [
        [
            InlineKeyboardButton(text="🔹 BASIC - 25⭐ / 15 грн", callback_data="lvl:basic")
        ],
        [
            InlineKeyboardButton(text="⭐ PREMIUM - 50⭐ / 30 грн", callback_data="lvl:premium")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="m:home")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ===== ВЫБОР СТРАНЫ =====
def kb_countries(level_key: str, countries_list: list):
    """Клавиатура выбора страны"""
    buttons = []
    
    # Добавляем страны в 2 колонки
    for i in range(0, len(countries_list), 2):
        row = []
        # Первая кнопка в ряду
        code1, name1 = countries_list[i]
        row.append(InlineKeyboardButton(text=name1, callback_data=f"cty:{level_key}:{code1}"))
        
        # Вторая кнопка в ряду (если есть)
        if i + 1 < len(countries_list):
            code2, name2 = countries_list[i + 1]
            row.append(InlineKeyboardButton(text=name2, callback_data=f"cty:{level_key}:{code2}"))
        
        buttons.append(row)
    
    # Кнопки назад
    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"lvl:{level_key}")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ===== ВЫБОР СПОСОБА ОПЛАТЫ =====
def kb_pay(level_key: str, country_code: str, has_card: bool = True):
    """Клавиатура выбора способа оплаты"""
    buttons = []
    
    # Кнопка оплаты Stars
    buttons.append([
        InlineKeyboardButton(text="⭐ Оплата Stars", callback_data=f"pay:{level_key}:{country_code}:stars")
    ])
    
    # Кнопка оплаты картой (только если есть реквизиты)
    if has_card:
        buttons.append([
            InlineKeyboardButton(text="🇺🇦 Оплата картой", callback_data=f"pay:{level_key}:{country_code}:card")
        ])
    
    # Кнопки навигации
    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cty:{level_key}:{country_code}")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ===== ПОСЛЕ ВЫСТАВЛЕНИЯ СЧЕТА =====
def kb_after_invoice(order_id: int):
    """Клавиатура после выставления счета"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid:{order_id}")
        ],
        [
            InlineKeyboardButton(text="❌ Отменить", callback_data="m:home"),
            InlineKeyboardButton(text="🔄 Выбрать другой", callback_data="m:buy")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ===== АДМИН ПАНЕЛЬ =====
def kb_admin(order_id: int):
    """Админ клавиатура для подтверждения оплат"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"adm:ok:{order_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm:no:{order_id}")
        ],
        [
            InlineKeyboardButton(text="🎁 +5⭐ Бонус", callback_data=f"adm:bonus:{order_id}:5"),
            InlineKeyboardButton(text="🎁 +10⭐ Бонус", callback_data=f"adm:bonus:{order_id}:10")
        ],
        [
            InlineKeyboardButton(text="📊 Статус: Ожидает", callback_data=f"adm:status:{order_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ===== ПОДПИСКА НА КАНАЛ =====
def kb_subscribe(channel_url: str = ""):
    """Клавиатура для подписки на канал"""
    buttons = []
    
    if channel_url:
        buttons.append([
            InlineKeyboardButton(text="📢 Подписаться на канал", url=channel_url)
        ])
    
    buttons.append([
        InlineKeyboardButton(text="🔁 Проверить подписку", callback_data="check_sub"),
        InlineKeyboardButton(text="🏠 На главную", callback_data="m:home")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ===== ПРОВЕРКА ПОДПИСКИ =====
def kb_check_subscription():
    """Клавиатура для проверки подписки"""
    buttons = [
        [
            InlineKeyboardButton(text="🔁 Проверить подписку", callback_data="check_sub"),
            InlineKeyboardButton(text="🏠 На главную", callback_data="m:home")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ===== ПОДДЕРЖКА =====
def kb_support(support_username: str):
    """Клавиатура поддержки"""
    buttons = [
        [
            InlineKeyboardButton(text="💬 Написать в поддержку", url=f"https://t.me/{support_username}")
        ],
        [
            InlineKeyboardButton(text="📦 Мои заказы", callback_data="m:purchases"),
            InlineKeyboardButton(text="🏠 На главную", callback_data="m:home")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ===== ОТМЕНА =====
def kb_cancel():
    """Простая кнопка отмены"""
    buttons = [
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="m:home")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ===== ИСТОРИЯ ЗАКАЗОВ =====
def kb_order_history(orders: list, page: int = 0, per_page: int = 5):
    """Клавиатура истории заказов с пагинацией"""
    buttons = []
    
    start_idx = page * per_page
    end_idx = start_idx + per_page
    
    for order in orders[start_idx:end_idx]:
        status_icon = "✅" if order.get("status") == "approved" else "⏳"
        btn_text = f"{status_icon} Заказ #{order.get('id', 'N/A')} - {order.get('level_title', 'N/A')}"
        
        buttons.append([
            InlineKeyboardButton(
                text=btn_text, 
                callback_data=f"order_detail:{order.get('id')}"
            )
        ])
    
    # Кнопки пагинации
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"orders_page:{page-1}")
        )
    
    nav_buttons.append(
        InlineKeyboardButton(text="🏠 Главная", callback_data="m:home")
    )
    
    if end_idx < len(orders):
        nav_buttons.append(
            InlineKeyboardButton(text="Далее ➡️", callback_data=f"orders_page:{page+1}")
        )
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ===== ДЕТАЛИ ЗАКАЗА =====
def kb_order_detail(order_id: int):
    """Клавиатура деталей заказа"""
    buttons = [
        [
            InlineKeyboardButton(text="🔄 Обновить статус", callback_data=f"order_refresh:{order_id}"),
            InlineKeyboardButton(text="💬 Поддержка", callback_data=f"order_support:{order_id}")
        ],
        [
            InlineKeyboardButton(text="📦 Все заказы", callback_data="m:purchases"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="m:home")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ===== БЫСТРЫЕ ОТВЕТЫ =====
def kb_quick_replies():
    """Клавиатура быстрых ответов"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data="quick:yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="quick:no")
        ],
        [
            InlineKeyboardButton(text="💰 Цены", callback_data="m:buy"),
            InlineKeyboardButton(text="❓ Помощь", callback_data="m:how")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
