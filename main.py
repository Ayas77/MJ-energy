import sys
import subprocess
import os

# ================= АВТО-УСТАНОВКА ЗАВИСИМОСТЕЙ =================
def install_requirements():
    required = ["aiogram==3.15.0", "aiosqlite==0.20.0", "aiohttp==3.10.11"]
    for package in required:
        pkg_name = package.split("==")[0]
        try:
            __import__(pkg_name)
        except ImportError:
            print(f"📦 Модуль {pkg_name} не найден. Устанавливаем...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_requirements()

# ================= ОСНОВНЫЕ ИМПОРТЫ =================
import logging
import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

# ================= КОНФИГУРАЦИЯ =================
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ ОШИБКА: Переменная BOT_TOKEN не найдена в Railway Variables!")

ADMIN_ID = 8735103964           # Ваш Telegram ID
ADMIN_PASSWORD = "1234"         # Пароль для входа в /admin

DB_NAME = "bot_database.db"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN.strip())
dp = Dispatcher(storage=MemoryStorage())

# ================= FSM (СОСТОЯНИЯ) =================
class AdminState(StatesGroup):
    waiting_for_password = State()
    waiting_for_reply = State()
    waiting_for_broadcast = State()

class UserState(StatesGroup):
    waiting_for_operator_msg = State()
    waiting_for_receipt = State()
    waiting_for_shop_order_info = State()

# ================= ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ =================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                language TEXT DEFAULT 'ru',
                ref_by INTEGER DEFAULT NULL,
                balance REAL DEFAULT 0.0,
                ref_percent REAL DEFAULT 0.40,
                purchases_count INTEGER DEFAULT 0
            )
        """)
        await db.commit()

# ================= КАТАЛОГ ЦИФРОВЫХ ТОВАРОВ И УСЛУГ =================
SHOP_PRODUCTS = {
    # Telegram Premium
    "tgp3": {"title": "Telegram Premium (3 месяца)", "price": "320 TMT / 12.5 USDT", "note": "⚠️ Без входа в аккаунт"},
    "tgp6": {"title": "Telegram Premium (6 месяцев)", "price": "420 TMT / 16.6 USDT", "note": "⚠️ Без входа в аккаунт"},
    "tgp12": {"title": "Telegram Premium (12 месяцев)", "price": "720 TMT / 30.25 USDT", "note": "⚠️ Без входа в аккаунт"},
    
    # Telegram Stars
    "s100": {"title": "Telegram Stars (100 ⭐️)", "price": "60 TMT", "note": "Пополнение через ID или юзернейм"},
    "s150": {"title": "Telegram Stars (150 ⭐️)", "price": "75 TMT", "note": "Пополнение через ID или юзернейм"},
    "s250": {"title": "Telegram Stars (250 ⭐️)", "price": "120 TMT", "note": "Пополнение через ID или юзернейм"},
    "s350": {"title": "Telegram Stars (350 ⭐️)", "price": "170 TMT", "note": "Пополнение через ID или юзернейм"},
    "s500": {"title": "Telegram Stars (500 ⭐️)", "price": "230 TMT", "note": "Пополнение через ID или юзернейм"},
    "s750": {"title": "Telegram Stars (750 ⭐️)", "price": "330 TMT", "note": "Пополнение через ID или юзернейм"},
    "s1000": {"title": "Telegram Stars (1000 ⭐️)", "price": "440 TMT", "note": "Пополнение через ID или юзернейм"},

    # PUBG Mobile UC
    "uc325": {"title": "PUBG Mobile (325 UC)", "price": "130 TMT", "note": "Пополнение по Player ID"},
    "uc660": {"title": "PUBG Mobile (660 UC)", "price": "230 TMT", "note": "Пополнение по Player ID"},
    "uc1800": {"title": "PUBG Mobile (1800 UC)", "price": "550 TMT", "note": "Пополнение по Player ID"},
    "uc3850": {"title": "PUBG Mobile (3850 UC)", "price": "1070 TMT", "note": "Пополнение по Player ID"},

    # TikTok Coins
    "tt500": {"title": "TikTok 500 Монет 🌕", "price": "166 TMT", "note": "📡 С входом в аккаунт"},
    "tt1000": {"title": "TikTok 1000 Монет 🌕", "price": "3200 TMT", "note": "📡 С входом в аккаунт"},

    # Belet
    "bel_std": {"title": "Belet Standart (1 месяц)", "price": "40 TMT", "note": "Пополнение по номеру телефона / аккаунту"},
    "bel_prm": {"title": "Belet Premium (1 месяц)", "price": "75 TMT", "note": "Пополнение по номеру телефона / аккаунту"},
    "bel_msc": {"title": "Belet Music (1 месяц)", "price": "25 TMT", "note": "Пополнение по номеру телефона / аккаунту"},

    # Exchange & Top-ups
    "ex_usdt": {"title": "Продажа USDT 💸", "price": "25 TMT / 1 USDT", "note": "Укажите нужную сумму и кошелек"},
    "ex_rub": {"title": "Пополнение RUBL 🇷🇺", "price": "Курс 3.4", "note": "Укажите реквизиты карты / кошелька"},
    "ex_usd": {"title": "USD (Visa 📱 / PayPal 📱)", "price": "32 TMT", "note": "Укажите счет или реквизиты"},
    "ex_tgsms": {"title": "Tg SMS толег", "price": "60 TMT", "note": "Укажите номер телефона"},
    "ex_tmt": {"title": "Оплата услуг TMT (-20%)", "price": "Скидка -20%", "note": "Телефон, WiFi, Belet и др."}
}

# ================= ТЕКСТЫ И ЯЗЫКИ =================
TEXTS = {
    'ru': {
        'welcome': "👋 Здравствуйте! Выберите действие в меню ниже или напишите сообщение оператору.",
        'buy_vpn': "🛒 Купить VPN",
        'shop': "🛍 Товары / Донаты",
        'test_24': "🎁 Тест на 24 часа",
        'ref_system': "🔗 Реферальная ссылка",
        'instruction': "❓ Инструкция",
        'operator': "🧑‍💻 Написать оператору",
        'lang': "🌐 Язык / Language / Dil",
        'choose_plan': "💳 Выберите тарифный план:",
        'plan_1': "📱 100 манат ($5) — 1 устройство",
        'plan_2': "💻 200 манат ($10) — Безлимит",
        'choose_payment': "💳 Выберите способ оплаты:",
        'pay_phone': "📱 Оплатить по номеру",
        'pay_crypto': "💎 Оплатить криптовалютой",
        'btn_paid': "✅ Я оплатил(а)",
        'btn_cancel': "❌ Отмена",
        'order_cancelled': "❌ Заказ отменен.",
        'send_receipt_msg': "📸 Пожалуйста, отправьте чек или скриншот оплаты сюда в чат.",
        'receipt_received': "⏳ Чек получен и отправлен администратору на проверку. Ожидайте выдачи доступа!",
        'test_requested': "⏳ Запрос на тест 24 часа отправлен администратору. Ожидайте!",
        'op_prompt': "✍️ Напишите ваше сообщение для оператора:",
        'op_sent': "📨 Ваше сообщение отправлено оператору. Ожидайте ответа!",
        'shop_prompt': "✍️ Отправьте данные для выполнения заказа (ID аккаунта, логин, номер телефона или удобный способ связи):",
        'shop_order_sent': "⏳ Ваш заказ оформлен и отправлен оператору! Ожидайте ответа или подтверждения."
    },
    'en': {
        'welcome': "👋 Hello! Choose an action from the menu below or write a message to the operator.",
        'buy_vpn': "🛒 Buy VPN",
        'shop': "🛍 Digital Goods / Top-up",
        'test_24': "🎁 24-hour Test",
        'ref_system': "🔗 Referral link",
        'instruction': "❓ Instructions",
        'operator': "🧑‍💻 Contact Operator",
        'lang': "🌐 Язык / Language / Dil",
        'choose_plan': "💳 Choose a subscription plan:",
        'plan_1': "📱 100 TMT ($5) — 1 device",
        'plan_2': "💻 200 TMT ($10) — Unlimited",
        'choose_payment': "💳 Choose a payment method:",
        'pay_phone': "📱 Pay via Phone Number",
        'pay_crypto': "💎 Pay via Cryptocurrency",
        'btn_paid': "✅ I have paid",
        'btn_cancel': "❌ Cancel",
        'order_cancelled': "❌ Order cancelled.",
        'send_receipt_msg': "📸 Please send the payment receipt/screenshot here in the chat.",
        'receipt_received': "⏳ Receipt received and sent to administrator for verification. Please wait!",
        'test_requested': "⏳ 24-hour test request sent to administrator. Please wait!",
        'op_prompt': "✍️ Write your message to the operator:",
        'op_sent': "📨 Your message has been sent to the operator. Please wait for a reply!",
        'shop_prompt': "✍️ Please send account ID, username, phone number, or details required for the order:",
        'shop_order_sent': "⏳ Your order has been placed and sent to the operator! Please wait for a response."
    },
    'tm': {
        'welcome': "👋 Salam! Aşakdaky menýudan hereketi saýlaň ýa-da operatora hat ýazyň.",
        'buy_vpn': "🛒 VPN satyn almak",
        'shop': "🛍 Harytlar / Donatlar",
        'test_24': "🎁 24 sagatlyk synag",
        'ref_system': "🔗 Salgylanma çykgydy",
        'instruction': "❓ Gözükdirme",
        'operator': "🧑‍💻 Operatora ýazmak",
        'lang': "🌐 Язык / Language / Dil",
        'choose_plan': "💳 Tarif meýilnamasyny saýlaň:",
        'plan_1': "📱 100 TMT ($5) — 1 enjam",
        'plan_2': "💻 200 TMT ($10) — Çäklendirilmedik",
        'choose_payment': "💳 Töleg usulyny saýlaň:",
        'pay_phone': "📱 Nomer boýunça tölemek",
        'pay_crypto': "💎 Kriptowalyuta bilen tölemek",
        'btn_paid': "✅ Men töledim",
        'btn_cancel': "❌ Ýatyrmak",
        'order_cancelled': "❌ Sargyt ýatyryldy.",
        'send_receipt_msg': "📸 Haýyş edýäris, töleg çegini ýa-da skrinşotyny şu ýere uwradyň.",
        'receipt_received': "⏳ Çek alyndy we barlamak üçin meňzedijä ugradyldy. Garaşyň!",
        'test_requested': "⏳ 24 sagatlyk synag haýyşy meňzedijä ugradyldy. Garaşyň!",
        'op_prompt': "✍️ Operatora hatyňyzy ýazyň:",
        'op_sent': "📨 Siziň hatyňyz operatora ugradyldy. Hata garaşyň!",
        'shop_prompt': "✍️ Sargydy ýerine ýetirmek üçin maglumatlary (ID, telefon nomer ýa-da login) ugradyň:",
        'shop_order_sent': "⏳ Siziň sargydyňyz kabul edildi we operatora ugradyldy! Garaşyň."
    }
}

# ================= КЛАВИАТУРЫ =================
def get_main_keyboard(lang='ru'):
    t = TEXTS.get(lang, TEXTS['ru'])
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t['buy_vpn']), KeyboardButton(text=t['shop'])],
            [KeyboardButton(text=t['test_24']), KeyboardButton(text=t['ref_system'])],
            [KeyboardButton(text=t['instruction']), KeyboardButton(text=t['operator'])],
            [KeyboardButton(text=t['lang'])]
        ],
        resize_keyboard=True
    )

def get_lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en")],
        [InlineKeyboardButton(text="🇹🇲 Türkmen", callback_data="set_lang_tm")]
    ])

def get_shop_categories_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐️ Telegram (Premium & Stars)", callback_data="shop_cat_tg")],
        [InlineKeyboardButton(text="❤️ PUBG Mobile UC", callback_data="shop_cat_pubg")],
        [InlineKeyboardButton(text="🌕 TikTok Монеты", callback_data="shop_cat_tiktok")],
        [InlineKeyboardButton(text="🔵 Подписки Belet", callback_data="shop_cat_belet")],
        [InlineKeyboardButton(text="🪙 Обмен валют / Оплата услуг", callback_data="shop_cat_exchange")]
    ])

# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =================
async def get_user_lang(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT language FROM users WHERE user_id = ?", (user_id,)) as cursor:
            res = await cursor.fetchone()
            return res[0] if res else 'ru'

# ================= ОБРАБОТКА /START И РЕФЕРАЛОВ =================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()
    ref_by = None

    if len(args) > 1 and args[1].isdigit():
        possible_ref = int(args[1])
        if possible_ref != user_id:
            ref_by = possible_ref

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            exists = await cursor.fetchone()
        
        if not exists:
            await db.execute(
                "INSERT INTO users (user_id, language, ref_by) VALUES (?, 'ru', ?)",
                (user_id, ref_by)
            )
            await db.commit()

    lang = await get_user_lang(user_id)
    await message.answer(TEXTS[lang]['welcome'], reply_markup=get_main_keyboard(lang))

# ================= ПАНЕЛЬ АДМИНИСТРАТОРА =================
@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel_cmd(message: types.Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_password)
    await message.answer("🔒 **Доступ ограничен.** Введите пароль администратора:", parse_mode="Markdown")

@dp.message(AdminState.waiting_for_password, F.from_user.id == ADMIN_ID)
async def check_admin_password(message: types.Message, state: FSMContext):
    if message.text == ADMIN_PASSWORD:
        await state.clear()
        
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                total_users = (await cursor.fetchone())[0]
            async with db.execute("SELECT SUM(purchases_count) FROM users") as cursor:
                total_sales = (await cursor.fetchone())[0] or 0

        stats_text = (
            f"🛠 **ПАНЕЛЬ АДМИНИСТРАТОРА**\n\n"
            f"👥 Всего пользователей: **{total_users}**\n"
            f"🛒 Всего проданных подписок: **{total_sales}**\n\n"
            f"⚙️ **Установить личный процент:**\n`/setref USER_ID PERCENT` (Например: `/setref 1234567 0.50`)"
        )

        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Сделать рассылку всем", callback_data="start_broadcast")]
        ])

        await message.answer(stats_text, parse_mode="Markdown", reply_markup=admin_kb)
    else:
        await message.answer("❌ **Неверный пароль!** Доступ отклонен.", parse_mode="Markdown")
        await state.clear()

# ================= УСТАНОВКА ПРОЦЕНТА РЕФЕРАЛА (/setref) =================
@dp.message(Command("setref"), F.from_user.id == ADMIN_ID)
async def cmd_setref(message: types.Message):
    args = message.text.split()
    if len(args) != 3:
        await message.answer("⚠️ Использование: `/setref USER_ID PERCENT`\nПример: `/setref 8735103964 0.50` (50%)", parse_mode="Markdown")
        return

    try:
        target_id = int(args[1])
        percent = float(args[2])
    except ValueError:
        await message.answer("❌ Ошибка в формате чисел.")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET ref_percent = ? WHERE user_id = ?", (percent, target_id))
        await db.commit()

    await message.answer(f"✅ Для пользователя `{target_id}` установлен реферальный процент: **{int(percent * 100)}%**", parse_mode="Markdown")

# ================= ВЫБОР ЯЗЫКА =================
@dp.message(F.text.in_(["🌐 Язык / Language / Dil"]))
async def select_language_menu(message: types.Message):
    await message.answer("Выберите язык / Choose language / Dil saýlaň:", reply_markup=get_lang_keyboard())

@dp.callback_query(F.data.startswith("set_lang_"))
async def set_user_language(callback: types.CallbackQuery):
    lang_code = callback.data.split("_")[-1]
    user_id = callback.from_user.id

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang_code, user_id))
        await db.commit()

    await callback.message.delete()
    confirm_msg = {
        'ru': "✅ Язык установлен: Русский",
        'en': "✅ Language set: English",
        'tm': "✅ Dil saýlandy: Türkmen"
    }
    await callback.message.answer(confirm_msg.get(lang_code, "✅"), reply_markup=get_main_keyboard(lang_code))
    await callback.answer()

# ================= ПОКУПКА VPN И ОПЛАТА =================
@dp.message(F.text.in_(["🛒 Купить VPN", "🛒 Buy VPN", "🛒 VPN satyn almak"]))
async def buy_vpn_menu(message: types.Message):
    lang = await get_user_lang(message.from_user.id)
    t = TEXTS[lang]
    
    plans_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t['plan_1'], callback_data="plan_100")],
        [InlineKeyboardButton(text=t['plan_2'], callback_data="plan_200")]
    ])
    await message.answer(t['choose_plan'], reply_markup=plans_kb)

@dp.callback_query(F.data.startswith("plan_"))
async def plan_selected(callback: types.CallbackQuery, state: FSMContext):
    plan_type = callback.data.split("_")[1]
    plan_name = "100 манат ($5) — 1 устройство" if plan_type == "100" else "200 манат ($10) — Безлимит"
    
    await state.update_data(chosen_plan=plan_name, plan_price=100 if plan_type == "100" else 200)
    lang = await get_user_lang(callback.from_user.id)
    t = TEXTS[lang]

    pay_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t['pay_phone'], callback_data="pay_method_phone")],
        [InlineKeyboardButton(text=t['pay_crypto'], callback_data="pay_method_crypto")]
    ])

    await callback.message.edit_text(f"💳 **Тариф:** {plan_name}\n\n{t['choose_payment']}", reply_markup=pay_kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_method_"))
async def payment_method_selected(callback: types.CallbackQuery, state: FSMContext):
    method = callback.data.split("_")[-1]
    method_name = "По номеру телефона" if method == "phone" else "Криптовалютой"
    await state.update_data(payment_method=method_name)

    lang = await get_user_lang(callback.from_user.id)
    t = TEXTS[lang]

    if method == "phone":
        pay_info = (
            "📱 **Реквизиты для оплаты по номеру:**\n\n"
            "📞 `+99362565792`\n"
            "📞 `+99361843366`\n\n"
            "⚠️ *(Если возникают проблемы с переводом между номерами, используйте терминал)*\n\n"
            "*(После перевода нажмите кнопку ниже)*"
        )
    else:
        pay_info = (
            "💎 **Реквизиты для оплаты криптовалютой:**\n\n"
            "• **USDT (TRC20):**\n`TSRfr6UQiEuV17U9XmSfmWGZQiPA3NYqAv`\n\n"
            "• **BTC:**\n`3GRApv73rPGn7JMtueGAaY33SbviiQdnbR`\n\n"
            "• **USDT / ETH (BEP20):**\n`0xbb7d1b44a4da704ecd3ce89e92b09ea5fbf5e4b1`\n\n"
            "*(После перевода нажмите кнопку ниже)*"
        )

    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t['btn_paid'], callback_data="user_pressed_paid")],
        [InlineKeyboardButton(text=t['btn_cancel'], callback_data="user_pressed_cancel")]
    ])

    await callback.message.edit_text(pay_info, reply_markup=confirm_kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "user_pressed_paid")
async def process_user_paid_button(callback: types.CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    t = TEXTS[lang]
    
    await state.set_state(UserState.waiting_for_receipt)
    await callback.message.answer(t['send_receipt_msg'])
    await callback.answer()

@dp.callback_query(F.data == "user_pressed_cancel")
async def process_user_cancel_button(callback: types.CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    t = TEXTS[lang]
    await state.clear()
    await callback.message.edit_text(t['order_cancelled'])
    await callback.answer()

# ================= ПОЛУЧЕНИЕ ЧЕКА И ОТПРАВКА АДМИНУ =================
@dp.message(UserState.waiting_for_receipt)
async def process_receipt_sent(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    chosen_plan = user_data.get("chosen_plan", "Не указан")
    payment_method = user_data.get("payment_method", "Не указан")
    plan_price = user_data.get("plan_price", 100)

    user = message.from_user
    username = f"@{user.username}" if user.username else "Нет username"
    lang = await get_user_lang(user.id)

    admin_card = (
        f"🛍 **ВЫБОР ТАРИФА И ОПЛАТА!**\n\n"
        f"💳 **Тариф:** {chosen_plan}\n"
        f"💰 **Способ:** {payment_method}\n"
        f"👤 **Клиент:** {username} (ID: `{user.id}`)\n"
        f"🌐 **Язык клиента:** {lang.upper()}"
    )

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"approve_pay_{user.id}_{plan_price}")],
        [InlineKeyboardButton(text="💬 Ответить / Выдать доступ", callback_data=f"reply_user_{user.id}")]
    ])

    if message.photo:
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=admin_card, reply_markup=admin_kb, parse_mode="Markdown")
    else:
        await bot.send_message(ADMIN_ID, f"{admin_card}\n\n📝 Сообщение от пользователя: {message.text}", reply_markup=admin_kb, parse_mode="Markdown")

    await message.answer(TEXTS[lang]['receipt_received'])
    await state.clear()

# ================= ПОДТВЕРЖДЕНИЕ ОПЛАТЫ АДМИНОМ =================
@dp.callback_query(F.data.startswith("approve_pay_"))
async def admin_approve_payment(callback: types.CallbackQuery):
    _, _, user_id, price = callback.data.split("_")
    user_id = int(user_id)
    price = float(price)

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET purchases_count = purchases_count + 1 WHERE user_id = ?", (user_id,))
        
        async with db.execute("SELECT ref_by FROM users WHERE user_id = ?", (user_id,)) as cursor:
            res = await cursor.fetchone()
            ref_by = res[0] if res else None

        if ref_by:
            async with db.execute("SELECT ref_percent FROM users WHERE user_id = ?", (ref_by,)) as cursor:
                ref_res = await cursor.fetchone()
                percent = ref_res[0] if ref_res else 0.40

            reward = price * percent
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (reward, ref_by))
            
            try:
                await bot.send_message(ref_by, f"🎉 Вам начислено **{reward:.2f} TMT** за покупку реферала!", parse_mode="Markdown")
            except Exception:
                pass

        await db.commit()

    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ **ОПЛАТА ПОДТВЕРЖДЕНА!**", parse_mode="Markdown")
    try:
        await bot.send_message(user_id, "🎉 Ваш платёж успешно подтверждён! Ожидайте выдачи ключа от оператора.")
    except Exception:
        pass
    await callback.answer()

# ================= МАГАЗИН ЦИФРОВЫХ ТОВАРОВ И УСЛУГ =================
@dp.message(F.text.in_(["🛍 Товары / Донаты", "🛍 Digital Goods / Top-up", "🛍 Harytlar / Donatlar"]))
async def shop_main_menu(message: types.Message):
    await message.answer("🛒 **Каталог цифровых товаров и услуг:**\nВыберите нужную категорию:", reply_markup=get_shop_categories_kb(), parse_mode="Markdown")

@dp.callback_query(F.data == "shop_main_menu")
async def shop_back_to_main_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("🛒 **Каталог цифровых товаров и услуг:**\nВыберите нужную категорию:", reply_markup=get_shop_categories_kb(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("shop_cat_"))
async def shop_show_category_items(callback: types.CallbackQuery):
    cat = callback.data.split("_")[-1]

    if cat == "tg":
        text = "⭐️ **Telegram Premium & Stars:**"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Premium 3 мес (320 TMT / 12.5 USDT)", callback_data="shop_item_tgp3")],
            [InlineKeyboardButton(text="🎁 Premium 6 мес (420 TMT / 16.6 USDT)", callback_data="shop_item_tgp6")],
            [InlineKeyboardButton(text="🎁 Premium 12 мес (720 TMT / 30.25 USDT)", callback_data="shop_item_tgp12")],
            [InlineKeyboardButton(text="⭐️ 100 Stars (60 TMT)", callback_data="shop_item_s100"), InlineKeyboardButton(text="⭐️ 150 Stars (75 TMT)", callback_data="shop_item_s150")],
            [InlineKeyboardButton(text="⭐️ 250 Stars (120 TMT)", callback_data="shop_item_s250"), InlineKeyboardButton(text="⭐️ 350 Stars (170 TMT)", callback_data="shop_item_s350")],
            [InlineKeyboardButton(text="⭐️ 500 Stars (230 TMT)", callback_data="shop_item_s500"), InlineKeyboardButton(text="⭐️ 750 Stars (330 TMT)", callback_data="shop_item_s750")],
            [InlineKeyboardButton(text="⭐️ 1000 Stars (440 TMT)", callback_data="shop_item_s1000")],
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="shop_main_menu")]
        ])
    elif cat == "pubg":
        text = "❤️ **PUBG Mobile UC:**"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="325 UC — 130 TMT", callback_data="shop_item_uc325")],
            [InlineKeyboardButton(text="660 UC — 230 TMT", callback_data="shop_item_uc660")],
            [InlineKeyboardButton(text="1800 UC — 550 TMT", callback_data="shop_item_uc1800")],
            [InlineKeyboardButton(text="3850 UC — 1070 TMT", callback_data="shop_item_uc3850")],
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="shop_main_menu")]
        ])
    elif cat == "tiktok":
        text = "🌕 **TikTok Монеты / Jeton:**"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="500 🌕 — 166 TMT", callback_data="shop_item_tt500")],
            [InlineKeyboardButton(text="1000 🌕 — 3200 TMT", callback_data="shop_item_tt1000")],
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="shop_main_menu")]
        ])
    elif cat == "belet":
        text = "🔵 **Подписки Belet:**"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Standart (1 мес) — 40 TMT", callback_data="shop_item_bel_std")],
            [InlineKeyboardButton(text="Premium (1 мес) — 75 TMT", callback_data="shop_item_bel_prm")],
            [InlineKeyboardButton(text="Music (1 мес) — 25 TMT", callback_data="shop_item_bel_msc")],
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="shop_main_menu")]
        ])
    else:  # exchange
        text = "🪙 **Обмен валют / Оплата услуг:**"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💸 USDT ➡️ 25 TMT", callback_data="shop_item_ex_usdt")],
            [InlineKeyboardButton(text="🇷🇺 RUBL ➡️ курс 3.4", callback_data="shop_item_ex_rub")],
            [InlineKeyboardButton(text="💵 USD (Visa/PayPal) ➡️ 32 TMT", callback_data="shop_item_ex_usd")],
            [InlineKeyboardButton(text="📱 Tg SMS toleg ➡️ 60 TMT", callback_data="shop_item_ex_tgsms")],
            [InlineKeyboardButton(text="🇹🇲 TMT (-20% Телефон, WiFi, Belet)", callback_data="shop_item_ex_tmt")],
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="shop_main_menu")]
        ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("shop_item_"))
async def shop_item_detail(callback: types.CallbackQuery):
    item_code = callback.data.replace("shop_item_", "")
    product = SHOP_PRODUCTS.get(item_code)

    if not product:
        await callback.answer("⚠️ Товар не найден!", show_alert=True)
        return

    card_text = (
        f"📦 **Товар / Услуга:** {product['title']}\n"
        f"💰 **Цена:** {product['price']}\n"
        f"📌 **Примечание:** {product['note']}\n\n"
        "💳 **Реквизиты для оплаты:**\n"
        "📱 `+99362565792` / `+99361843366`\n"
        "💎 `TSRfr6UQiEuV17U9XmSfmWGZQiPA3NYqAv` (USDT)\n\n"
        f"👇 *Нажмите кнопку ниже, чтобы оформить заказ через оператора:*"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Оформить заказ", callback_data=f"order_prod_{item_code}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="shop_main_menu")]
    ])

    await callback.message.edit_text(card_text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("order_prod_"))
async def start_product_order(callback: types.CallbackQuery, state: FSMContext):
    item_code = callback.data.replace("order_prod_", "")
    product = SHOP_PRODUCTS.get(item_code)

    if not product:
        await callback.answer("⚠️ Ошибка вызова товара!", show_alert=True)
        return

    await state.update_data(item_title=product['title'], item_price=product['price'], item_note=product['note'])
    
    payment_info = (
        f"📦 **Товар:** {product['title']}\n"
        f"💰 **Цена:** {product['price']}\n\n"
        "💳 **Реквизиты для оплаты:**\n\n"
        "📱 **По номеру телефона:**\n`+99362565792` / `+99361843366`\n\n"
        "💎 **Криптовалюта (USDT TRC20):**\n`TSRfr6UQiEuV17U9XmSfmWGZQiPA3NYqAv`\n\n"
        "⚠️ *(Если возникают проблемы с переводом между номерами, используйте терминал)*\n\n"
        "*(После перевода нажмите кнопку ниже)*"
    )

    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил(а)", callback_data="shop_user_paid")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="shop_user_cancel")]
    ])

    await callback.message.edit_text(payment_info, reply_markup=confirm_kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "shop_user_paid")
async def shop_user_paid(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserState.waiting_for_shop_order_info)
    lang = await get_user_lang(callback.from_user.id)
    await callback.message.answer(TEXTS[lang]['shop_prompt'])
    await callback.answer()

@dp.callback_query(F.data == "shop_user_cancel")
async def shop_user_cancel(callback: types.CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    await state.clear()
    await callback.message.edit_text(TEXTS[lang]['order_cancelled'])
    await callback.answer()

@dp.message(UserState.waiting_for_shop_order_info)
async def process_shop_order_data(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    item_title = user_data.get("item_title", "Товар")
    item_price = user_data.get("item_price", "Не указана")
    item_note = user_data.get("item_note", "")

    user = message.from_user
    username = f"@{user.username}" if user.username else "Нет username"
    lang = await get_user_lang(user.id)

    admin_card = (
        f"🛍 **НОВЫЙ ЗАКАЗ ИЗ МАГАДИНА!**\n\n"
        f"📦 **Товар:** {item_title}\n"
        f"💰 **Цена:** {item_price}\n"
        f"📌 **Инфо:** {item_note}\n"
        f"👤 **Клиент:** {username} (ID: `{user.id}`)\n"
        f"🌐 **Язык клиента:** {lang.upper()}\n\n"
        f"📝 **Данные от клиента:**\n{message.text}"
    )

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Ответить / Выдать заказ", callback_data=f"reply_user_{user.id}")]
    ])

    await bot.send_message(ADMIN_ID, admin_card, reply_markup=admin_kb, parse_mode="Markdown")
    await message.answer(TEXTS[lang]['shop_order_sent'])
    await state.clear()

# ================= ТЕСТ 24 ЧАСА =================
@dp.message(F.text.in_(["🎁 Тест на 24 часа", "🎁 24-hour Test", "🎁 24 sagatlyk synag"]))
async def request_test_menu(message: types.Message):
    user = message.from_user
    username = f"@{user.username}" if user.username else "Нет username"
    lang = await get_user_lang(user.id)

    admin_card = (
        f"🎁 **ЗАПРОС ТЕСТА НА 24 ЧАСА!**\n\n"
        f"👤 **Клиент:** {username} (ID: `{user.id}`)\n"
        f"🌐 **Язык клиента:** {lang.upper()}"
    )

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Ответить / Выдать доступ", callback_data=f"reply_user_{user.id}")]
    ])

    await bot.send_message(ADMIN_ID, admin_card, reply_markup=admin_kb, parse_mode="Markdown")
    await message.answer(TEXTS[lang]['test_requested'])

# ================= РЕФЕРАЛЬНАЯ СИСТЕМА =================
@dp.message(F.text.in_(["🔗 Реферальная ссылка", "🔗 Referral link", "🔗 Salgylanma çykgydy"]))
async def ref_system_menu(message: types.Message):
    user_id = message.from_user.id
    bot_info = await bot.get_me()

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT balance, ref_percent FROM users WHERE user_id = ?", (user_id,)) as cursor:
            res = await cursor.fetchone()
            balance = res[0] if res else 0.0
            percent = res[1] if res else 0.40

        async with db.execute("SELECT COUNT(*) FROM users WHERE ref_by = ?", (user_id,)) as cursor:
            ref_count = (await cursor.fetchone())[0]

    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    percent_num = int(percent * 100)

    text = (
        f"💰 **Партнерская программа**\n\n"
        f"👥 Приглашено друзей: **{ref_count}**\n"
        f"💵 Ваш баланс: **{balance:.2f} TMT**\n"
        f"📊 Ваш реферальный процент: **{percent_num}%**\n\n"
        f"🔗 Ваша ссылка для приглашения:\n`{ref_link}`"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Запросить вывод средств", callback_data="request_withdraw")]
    ])

    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "request_withdraw")
async def withdraw_request(callback: types.CallbackQuery):
    user = callback.from_user
    username = f"@{user.username}" if user.username else "Нет username"

    await bot.send_message(ADMIN_ID, f"💸 **ЗАПРОС НА ВЫВОД РЕФЕРАЛЬНЫХ!**\n\n👤 Пользователь: {username} (ID: `{user.id}`)", parse_mode="Markdown")
    await callback.answer("⏳ Запрос отправлен администратору!", show_alert=True)

# ================= СВЯЗЬ С ОПЕРАТОРОМ =================
@dp.message(F.text.in_(["🧑‍💻 Написать оператору", "🧑‍💻 Contact Operator", "🧑‍💻 Operatora ýazmak"]))
async def contact_operator_menu(message: types.Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    await state.set_state(UserState.waiting_for_operator_msg)
    await message.answer(TEXTS[lang]['op_prompt'])

@dp.message(UserState.waiting_for_operator_msg)
async def process_operator_msg(message: types.Message, state: FSMContext):
    user = message.from_user
    username = f"@{user.username}" if user.username else "Нет username"

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply_user_{user.id}")]
    ])

    await bot.send_message(
        ADMIN_ID,
        f"📩 **СООБЩЕНИЕ ОПЕРАТОРУ** от {username} (ID: `{user.id}`):\n\n{message.text}",
        reply_markup=admin_kb,
        parse_mode="Markdown"
    )

    lang = await get_user_lang(user.id)
    await message.answer(TEXTS[lang]['op_sent'])
    await state.clear()

# ================= ОТВЕТ АДМИНИСТРАТОРА КЛИЕНТУ =================
@dp.callback_query(F.data.startswith("reply_user_"))
async def admin_start_reply(callback: types.CallbackQuery, state: FSMContext):
    target_user_id = callback.data.split("_")[-1]
    await state.update_data(target_user_id=target_user_id)
    await state.set_state(AdminState.waiting_for_reply)

    await callback.message.answer(f"✍️ Введите ответ/ключ для пользователя `{target_user_id}`:", parse_mode="Markdown")
    await callback.answer()

@dp.message(AdminState.waiting_for_reply, F.from_user.id == ADMIN_ID)
async def process_admin_reply_send(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target_user_id = data.get("target_user_id")

    try:
        await bot.copy_message(chat_id=target_user_id, from_chat_id=message.chat.id, message_id=message.message_id)
        await message.answer("✅ Ответ успешно доставлен клиенту!")
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")

    await state.clear()

# ================= РАССЫЛКА СООБЩЕНИЙ =================
@dp.callback_query(F.data == "start_broadcast", F.from_user.id == ADMIN_ID)
async def start_broadcast_prompt(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.waiting_for_broadcast)
    await callback.message.answer("📣 Пришлите сообщение (текст, фото или видео) для рассылки всем пользователям:")
    await callback.answer()

@dp.message(AdminState.waiting_for_broadcast, F.from_user.id == ADMIN_ID)
async def process_broadcast_msg(message: types.Message, state: FSMContext):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            users = await cursor.fetchall()

    if not users:
        await message.answer("⚠️ В базе данных пока нет пользователей!")
        await state.clear()
        return

    success_count = 0
    blocked_count = 0
    fail_count = 0

    await message.answer(f"🚀 Рассылка начата для {len(users)} пользователей...")

    for user in users:
        u_id = user[0]
        try:
            await bot.copy_message(chat_id=u_id, from_chat_id=message.chat.id, message_id=message.message_id)
            success_count += 1
            await asyncio.sleep(0.05)
        except TelegramForbiddenError:
            blocked_count += 1
        except Exception:
            fail_count += 1

    stats_report = (
        f"📊 **Рассылка завершена!**\n\n"
        f"✅ **Успешно:** {success_count}\n"
        f"🚫 **Заблокировали бота:** {blocked_count}\n"
        f"❌ **Ошибки:** {fail_count}"
    )

    await message.answer(stats_report, parse_mode="Markdown")
    await state.clear()

# ================= ИНСТРУКЦИЯ (ПОДРОБНАЯ) =================
@dp.message(F.text.in_(["❓ Инструкция", "❓ Instructions", "❓ Gözükdirme"]))
async def instruction_menu(message: types.Message):
    lang = await get_user_lang(message.from_user.id)
    
    if lang == 'ru':
        text = (
            "📖 **Инструкция по подключению M.J. E.VPN:**\n\n"
            "📱 **Для Android:**\n"
            "1. Установите приложение **v2rayNG** или **Happ**.\n"
            "2. Скопируйте полученный ключ.\n"
            "3. Откройте приложение и импортируйте ключ через буфер обмена.\n\n"
            "🍏 **Для iPhone / iPad (iOS):**\n"
            "1. Установите приложение **Streisand**, **V2Box** или **FoXray**.\n"
            "2. Скопируйте полученный ключ.\n"
            "3. Добавьте ключ в приложение через кнопку добавления (+).\n\n"
            "💻 **Для Windows:**\n"
            "1. Рекомендуется использовать **v2rayN** или **Nekoray**.\n"
            "2. Вставьте скопированный ключ.\n"
            "3. Активируйте системный прокси.\n\n"
            "🍏 **Для macOS (MacBook):**\n"
            "1. Используйте **V2Box**, **v2rayN**, **Nekoray** или **FoXray**.\n"
            "2. Импортируйте настройки из буфер обмена.\n"
            "3. Подключитесь и активируйте прокси."
        )
    elif lang == 'en':
        text = (
            "📖 **M.J. E.VPN Connection Instructions:**\n\n"
            "📱 **For Android:**\n"
            "1. Install **v2rayNG** or **Happ**.\n"
            "2. Copy your key.\n"
            "3. Import it from the clipboard in the app.\n\n"
            "🍏 **For iOS (iPhone/iPad):**\n"
            "1. Install **Streisand**, **V2Box**, or **FoXray**.\n"
            "2. Copy your key.\n"
            "3. Add the key using the add (+) button.\n\n"
            "💻 **For Windows:**\n"
            "1. We recommend **v2rayN** or **Nekoray**.\n"
            "2. Paste the copied key.\n"
            "3. Enable the system proxy.\n\n"
            "🍏 **For macOS (MacBook):**\n"
            "1. Use **V2Box**, **v2rayN**, **Nekoray** or **FoXray**.\n"
            "2. Import settings from the clipboard.\n"
            "3. Connect and activate the proxy."
        )
    else: # tm
        text = (
            "📖 **M.J. E.VPN birikdirmek üçin gözükdirme:**\n\n"
            "📱 **Android üçin:**\n"
            "1. **v2rayNG** ýa-da **Happ** programmasyny gurnaň.\n"
            "2. Açaryňyzy göçürip alyň.\n"
            "3. Programmada buferden import ediň.\n\n"
            "🍏 **iPhone / iPad (iOS) üçin:**\n"
            "1. **Streisand**, **V2Box** ýa-da **FoXray** gurnaň.\n"
            "2. Açaryňyzy göçürip alyň.\n"
            "3. (+) düwmesi arkaly açary goşuň.\n\n"
            "💻 **Windows üçin:**\n"
            "1. **v2rayN** ýa-da **Nekoray** ulanmak maslahat berilýär.\n"
            "2. Göçürilen açary goýuň.\n"
            "3. Ulgam proksisini (system proxy) işlediň.\n\n"
            "🍏 **macOS (MacBook) üçin:**\n"
            "1. **V2Box**, **v2rayN**, **Nekoray** ýa-da **FoXray** ulanyň.\n"
            "2. Sazlamalary buferden import ediň.\n"
            "3. Birikdiriň we proksini işlediň."
        )

    await message.answer(text, parse_mode="Markdown")

# ================= ЗАПУСК БОТА =================
async def main():
    await init_db()
    print("🚀 Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
