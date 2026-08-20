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
# Берём токен из безопасных переменных окружения Railway
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

# ================= ТЕКСТЫ И ЯЗЫКИ =================
TEXTS = {
    'ru': {
        'welcome': "👋 Здравствуйте! Выберите действие в меню ниже или напишите сообщение оператору.",
        'buy_vpn': "🛒 Купить VPN",
        'test_24': "🎁 Тест на 24 часа",
        'ref_system': "🔗 Реферальная ссылка",
        'instruction': "❓ Инструкция",
        'operator': "🧑‍💻 Написать оператору",
        'lang': "🌐 Язык / Language / Dil",
        'choose_plan': "💳 Выберите тарифный план:",
        'plan_1': "📱 100 манат ($5) — 1 устройство",
        'plan_2': "💻 200 манат ($10) — до 3 устройств",
        'choose_payment': "💳 Выберите способ оплаты:",
        'pay_phone': "📱 Оплатить по номеру",
        'pay_crypto': "💎 Оплатить криптовалютой",
        'send_receipt_msg': "📸 Пожалуйста, отправьте чек или скриншот оплаты сюда в чат.",
        'receipt_received': "⏳ Чек получен и отправлен администратору на проверку. Ожидайте выдачи доступа!",
        'test_requested': "⏳ Запрос на тест 24 часа отправлен администратору. Ожидайте!",
        'op_prompt': "✍️ Напишите ваше сообщение для оператора:",
        'op_sent': "📨 Ваше сообщение отправлено оператору. Ожидайте ответа!"
    },
    'en': {
        'welcome': "👋 Hello! Choose an action from the menu below or write a message to the operator.",
        'buy_vpn': "🛒 Buy VPN",
        'test_24': "🎁 24-hour Test",
        'ref_system': "🔗 Referral link",
        'instruction': "❓ Instructions",
        'operator': "🧑‍💻 Contact Operator",
        'lang': "🌐 Язык / Language / Dil",
        'choose_plan': "💳 Choose a subscription plan:",
        'plan_1': "📱 100 TMT ($5) — 1 device",
        'plan_2': "💻 200 TMT ($10) — up to 3 devices",
        'choose_payment': "💳 Choose a payment method:",
        'pay_phone': "📱 Pay via Phone Number",
        'pay_crypto': "💎 Pay via Cryptocurrency",
        'send_receipt_msg': "📸 Please send the payment receipt/screenshot here in the chat.",
        'receipt_received': "⏳ Receipt received and sent to administrator for verification. Please wait!",
        'test_requested': "⏳ 24-hour test request sent to administrator. Please wait!",
        'op_prompt': "✍️ Write your message to the operator:",
        'op_sent': "📨 Your message has been sent to the operator. Please wait for a reply!"
    },
    'tm': {
        'welcome': "👋 Salam! Aşakdaky menýudan hereketi saýlaň ýa-da operatora hat ýazyň.",
        'buy_vpn': "🛒 VPN satyn almak",
        'test_24': "🎁 24 sagatlyk synag",
        'ref_system': "🔗 Salgylanma çykgydy",
        'instruction': "❓ Gözükdirme",
        'operator': "🧑‍💻 Operatora ýazmak",
        'lang': "🌐 Язык / Language / Dil",
        'choose_plan': "💳 Tarif meýilnamasyny saýlaň:",
        'plan_1': "📱 100 TMT ($5) — 1 enjam",
        'plan_2': "💻 200 TMT ($10) — 3 enjama çenli",
        'choose_payment': "💳 Töleg usulyny saýlaň:",
        'pay_phone': "📱 Nomer boýunça tölemek",
        'pay_crypto': "💎 Kriptowalyuta bilen tölemek",
        'send_receipt_msg': "📸 Haýyş edýäris, töleg çegini ýa-da skrinşotyny şu ýere uwradyň.",
        'receipt_received': "⏳ Çek alyndy we barlamak üçin meňzedijä ugradyldy. Garaşyň!",
        'test_requested': "⏳ 24 sagatlyk synag haýyşy meňzedijä ugradyldy. Garaşyň!",
        'op_prompt': "✍️ Operatora hatyňyzy ýazyň:",
        'op_sent': "📨 Siziň hatyňyz operatora ugradyldy. Hata garaşyň!"
    }
}

# ================= КЛАВИАТУРЫ =================
def get_main_keyboard(lang='ru'):
    t = TEXTS.get(lang, TEXTS['ru'])
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t['buy_vpn']), KeyboardButton(text=t['test_24'])],
            [KeyboardButton(text=t['ref_system']), KeyboardButton(text=t['instruction'])],
            [KeyboardButton(text=t['operator']), KeyboardButton(text=t['lang'])]
        ],
        resize_keyboard=True
    )

def get_lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en")],
        [InlineKeyboardButton(text="🇹🇲 Türkmen", callback_data="set_lang_tm")]
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
    plan_name = "100 манат ($5) — 1 устройство" if plan_type == "100" else "200 манат ($10) — до 3 устройств"
    
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
    
    if method == "phone":
        pay_info = "📱 **Реквизиты для оплаты по номеру:**\n\n`+9936XXXXXXX`\n(После перевода нажмите кнопку ниже)"
    else:
        pay_info = (
            "💎 **Реквизиты для оплаты криптовалютой:**\n\n"
            "• **USDT (TRC20):** `TYourTrc20AddressHere...`\n"
            "• **USDT (TON):** `EQYourTonAddressHere...`\n"
            "• **BTC:** `1YourBtcAddressHere...`\n"
            "• **LTC:** `LYourLtcAddressHere...`"
        )

    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил(а)", callback_data="user_pressed_paid")]
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

# ================= ИНСТРУКЦИЯ =================
@dp.message(F.text.in_(["❓ Инструкция", "❓ Instructions", "❓ Gözükdirme"]))
async def instruction_menu(message: types.Message):
    text = "📖 **Инструкция по подключению VPN:**\n\n1. Скачайте приложение Happ / V2rayN / Streisand.\n2. Скопируйте полученный ключ.\n3. Импортируйте ключ в приложение и нажмите Подключить."
    await message.answer(text, parse_mode="Markdown")

# ================= ЗАПУСК БОТА =================
async def main():
    await init_db()
    print("🚀 Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
