import subprocess
import sys

# Автоматическая проверка и установка библиотек при старте
def install_requirements():
    required = ["aiogram==3.15.0", "aiosqlite==0.20.0", "aiohttp==3.10.11"]
    for package in required:
        try:
            mod_name = package.split("==")[0]
            __import__(mod_name)
        except ImportError:
            print(f"📦 Устанавливаем {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_requirements()

import os
import logging
import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8923920954:AAGpJQyWtwCjeO8mR2s4RW9TeSnPm-UQ12Q"
ADMIN_ID = 8735103964

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class AdminState(StatesGroup):
    waiting_for_reply = State()

# Тексты и локализация на трех языках
TEXTS = {
    'ru': {
        'welcome': "👋 Здравствуйте! Выберите язык / Select language / Dil saýlaň:",
        'lang_set': "✅ Язык установлен: Русский.\nВыберите действие в меню ниже или напишите сообщение оператору.",
        'msg_sent': "📩 Ваше сообщение отправлено оператору. Ожидайте ответа!",
        'ref_info': "🔗 **Ваша реферальная ссылка:**\n{link}\n\n👥 Приглашено: {count} чел.",
        'btn_buy': "🛒 Купить VPN",
        'btn_ref': "🔗 Реферальная ссылка",
        'btn_lang': "🌐 Язык / Language / Dil",
        'tariffs_title': "⚡ **Выберите подходящий тариф VPN:**",
        'tariff_100_btn': "📱 100 манат (1 устройство)",
        'tariff_200_btn': "♾️ 200 манат (Бесконечно устройств)",
        'payment_text': (
            "💳 **Реквизиты для оплаты:**\n\n"
            "Вы выбрали тариф: **{tariff}**\n\n"
            "📌 **Номер для перевода / пополнения:**\n`+9936XXXXXXX`\n\n"
            "После оплаты отправьте чек или скриншот прямо в этот чат. "
            "Оператор проверит перевод и выдаст вам ключи доступа!"
        )
    },
    'en': {
        'welcome': "👋 Hello! Select language / Выберите язык / Dil saýlaň:",
        'lang_set': "✅ Language set: English.\nSelect an option from the menu below or send a message to the operator.",
        'msg_sent': "📩 Your message has been sent to the operator. Please wait for a reply!",
        'ref_info': "🔗 **Your referral link:**\n{link}\n\n👥 Invited: {count} users",
        'btn_buy': "🛒 Buy VPN",
        'btn_ref': "🔗 Referral Link",
        'btn_lang': "🌐 Language / Язык / Dil",
        'tariffs_title': "⚡ **Select your VPN plan:**",
        'tariff_100_btn': "📱 100 TMT (1 device)",
        'tariff_200_btn': "♾️ 200 TMT (Unlimited devices)",
        'payment_text': (
            "💳 **Payment details:**\n\n"
            "Selected plan: **{tariff}**\n\n"
            "📌 **Phone number / Payment info:**\n`+9936XXXXXXX`\n\n"
            "After payment, please send the receipt or screenshot directly to this chat. "
            "The operator will verify the transaction and issue your access keys!"
        )
    },
    'tk': {
        'welcome': "👋 Salam! Dil saýlaň / Выберите язык / Select language:",
        'lang_set': "✅ Dil saýlandy: Türkmen dili.\nAşakdaky menýudan bölümi saýlaň ýa-da оператора hat ýazyň.",
        'msg_sent': "📩 Hatyňyz оператора ugradyldy. Jogaba garaşyň!",
        'ref_info': "🔗 **Siziň referal salgyňyz:**\n{link}\n\n👥 Çagyrylanlar: {count} adam",
        'btn_buy': "🛒 VPN satyn almak",
        'btn_ref': "🔗 Referal salgy",
        'btn_lang': "🌐 Dil / Language / Язык",
        'tariffs_title': "⚡ **Töleg tarifini saýlaň:**",
        'tariff_100_btn': "📱 100 manat (1 enjam)",
        'tariff_200_btn': "♾️ 200 manat (Päksiz enjam)",
        'payment_text': (
            "💳 **Töleg maglumatlary:**\n\n"
            "Saýlanan tarif: **{tariff}**\n\n"
            "📌 **Töleg üçin telefon belgi:**\n`+9936XXXXXXX`\n\n"
            "Tölegi geçireniňizden soň çeki (скриншот) şu çata ugradyň. "
            "Оператор tölegi barlap, сизге VPN açarlaryny ugradar!"
        )
    }
}

async def init_db():
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                referrer_id INTEGER,
                language TEXT DEFAULT 'ru'
            )
        """)
        await db.commit()

def get_lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang_ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang_en"),
            InlineKeyboardButton(text="🇹🇲 Türkmen", callback_data="setlang_tk")
        ]
    ])

def get_main_keyboard(lang):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=TEXTS[lang]['btn_buy'])],
            [KeyboardButton(text=TEXTS[lang]['btn_ref']), KeyboardButton(text=TEXTS[lang]['btn_lang'])]
        ],
        resize_keyboard=True
    )

def get_tariffs_keyboard(lang):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=TEXTS[lang]['tariff_100_btn'], callback_data="buy_100")],
        [InlineKeyboardButton(text=TEXTS[lang]['tariff_200_btn'], callback_data="buy_200")]
    ])

@dp.message(CommandStart())
async def start_cmd(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    username = message.from_user.username or "NoUsername"
    referrer_id = None

    if command.args and command.args.startswith("ref_"):
        try:
            possible_ref = int(command.args.split("_")[1])
            if possible_ref != user_id:
                referrer_id = possible_ref
        except ValueError:
            pass

    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT user_id, language FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                await db.execute(
                    "INSERT INTO users (user_id, username, referrer_id, language) VALUES (?, ?, ?, ?)",
                    (user_id, username, referrer_id, 'ru')
                )
                await db.commit()
                lang = 'ru'
            else:
                lang = user[1]

    await message.answer(TEXTS[lang]['welcome'], reply_markup=get_lang_keyboard())

@dp.callback_query(F.data.startswith("setlang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id

    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
        await db.commit()

    await callback.message.delete()
    await callback.message.answer(TEXTS[lang]['lang_set'], reply_markup=get_main_keyboard(lang))

@dp.message(F.text.in_(["🛒 Купить VPN", "🛒 Buy VPN", "🛒 VPN satyn almak"]))
async def buy_vpn_handler(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT language FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            lang = row[0] if row else 'ru'

    await message.answer(TEXTS[lang]['tariffs_title'], reply_markup=get_tariffs_keyboard(lang), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_"))
async def process_tariff_selection(callback: types.CallbackQuery):
    tariff_code = callback.data.split("_")[1]
    user_id = callback.from_user.id
    username = f"@{callback.from_user.username}" if callback.from_user.username else "Отсутствует"

    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT referrer_id, language FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user_data = await cursor.fetchone()
            referrer_id = user_data[0] if user_data else None
            lang = user_data[1] if user_data else 'ru'

    tariff_name = TEXTS[lang]['tariff_100_btn'] if tariff_code == "100" else TEXTS[lang]['tariff_200_btn']

    referrer_info = "Прямой заход (без реферала)"
    if referrer_id:
        async with aiosqlite.connect("bot_database.db") as db:
            async with db.execute("SELECT username FROM users WHERE user_id = ?", (referrer_id,)) as cursor:
                ref_user = await cursor.fetchone()
                ref_name = f"@{ref_user[0]}" if ref_user and ref_user[0] != "NoUsername" else f"ID: {referrer_id}"
                referrer_info = f"Партнер: {ref_name} (ID: `{referrer_id}`) — **40%**"

    # Уведомление администратору о намерении купить
    admin_alert = (
        f"🛍 **ЗАЯВКА НА ПОКУПКУ VPN!**\n\n"
        f"💳 **Тариф:** {tariff_name}\n"
        f"👤 **Клиент:** {username} (ID: `{user_id}`)\n"
        f"🤝 **Источник:** {referrer_info}\n"
        f"🌐 **Язык:** {lang.upper()}"
    )

    reply_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Ответить / Выдать доступ", callback_data=f"reply_{user_id}")]
    ])

    await bot.send_message(chat_id=ADMIN_ID, text=admin_alert, parse_mode="Markdown", reply_markup=reply_kb)

    # Выдача реквизитов пользователю
    await callback.message.edit_text(
        TEXTS[lang]['payment_text'].format(tariff=tariff_name),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message(F.text.in_(["🔗 Реферальная ссылка", "🔗 Referral Link", "🔗 Referal salgy"]))
async def ref_handler(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT language FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            lang = row[0] if row else 'ru'

        async with db.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,)) as cursor:
            count = (await cursor.fetchone())[0]

    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    await message.answer(TEXTS[lang]['ref_info'].format(link=ref_link, count=count), parse_mode="Markdown")

@dp.message(F.text.in_(["🌐 Язык / Language / Dil"]))
async def change_lang_handler(message: types.Message):
    await message.answer("Выберите язык / Select language / Dil saýlaň:", reply_markup=get_lang_keyboard())

# Пересылка всех сообщений (чеков, фото, вопросов) админу
@dp.message(F.chat.type == "private")
async def forward_to_admin(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == AdminState.waiting_for_reply.state:
        return

    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else "Отсутствует"

    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT referrer_id, language FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user_data = await cursor.fetchone()
            referrer_id = user_data[0] if user_data else None
            lang = user_data[1] if user_data else 'ru'

    referrer_info = "Прямой заход (без реферала)"
    if referrer_id:
        async with aiosqlite.connect("bot_database.db") as db:
            async with db.execute("SELECT username FROM users WHERE user_id = ?", (referrer_id,)) as cursor:
                ref_user = await cursor.fetchone()
                ref_name = f"@{ref_user[0]}" if ref_user and ref_user[0] != "NoUsername" else f"ID: {referrer_id}"
                referrer_info = f"Партнер: {ref_name} (ID: `{referrer_id}`) — **40%**"

    admin_caption = (
        f"📩 **Новое сообщение / Чек от клиента!**\n\n"
        f"👤 **От:** {username} (ID: `{user_id}`)\n"
        f"🤝 **Источник:** {referrer_info}\n"
        f"🌐 **Язык:** {lang.upper()}"
    )

    reply_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Ответить клиенту", callback_data=f"reply_{user_id}")]
    ])

    await bot.send_message(chat_id=ADMIN_ID, text=admin_caption, parse_mode="Markdown", reply_markup=reply_kb)
    await bot.copy_message(chat_id=ADMIN_ID, from_chat_id=message.chat.id, message_id=message.message_id)

    await message.answer(TEXTS[lang]['msg_sent'])

@dp.callback_query(F.data.startswith("reply_"), F.from_user.id == ADMIN_ID)
async def prepare_reply(callback: types.CallbackQuery, state: FSMContext):
    target_user_id = int(callback.data.split("_")[1])
    await state.update_data(target_user_id=target_user_id)
    await state.set_state(AdminState.waiting_for_reply)
    await callback.message.answer(f"✍️ Введите ответ для пользователя `[{target_user_id}]`:")
    await callback.answer()

@dp.message(AdminState.waiting_for_reply, F.from_user.id == ADMIN_ID)
async def send_reply_to_user(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target_user_id = data['target_user_id']

    try:
        await bot.send_message(chat_id=target_user_id, text="👨‍💻 **Ответ оператора:**", parse_mode="Markdown")
        await bot.copy_message(chat_id=target_user_id, from_chat_id=message.chat.id, message_id=message.message_id)
        await message.answer("✅ Ответ успешно отправлен!")
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")

    await state.clear()

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
