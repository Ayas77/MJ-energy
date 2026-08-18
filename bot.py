import os
import logging
import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)

# Твои данные жестко прописаны в коде
BOT_TOKEN = "8923920954:AAGpJQyWtwCjeO8mR2s4RW9TeSnPm-UQ12Q"
ADMIN_ID = 8735103964

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class AdminState(StatesGroup):
    waiting_for_reply = State()

TEXTS = {
    'ru': {
        'welcome': "👋 Здравствуйте! Выберите язык / Select language / Dil saýlaň:",
        'lang_set': "✅ Язык установлен: Русский.\nНапишите ваше сообщение, и оператор ответит вам в ближайшее время.",
        'msg_sent': "📩 Ваше сообщение отправлено оператору. Ожидайте ответа!",
        'ref_info': "🔗 **Ваша реферальная ссылка:**\n{link}\n\n👥 Приглашено: {count} чел.",
        'btn_ref': "🔗 Реферальная ссылка",
        'btn_lang': "🌐 Язык / Language / Dil"
    },
    'en': {
        'welcome': "👋 Hello! Select language / Выберите язык / Dil saýlaň:",
        'lang_set': "✅ Language set: English.\nSend your message here, and an operator will respond shortly.",
        'msg_sent': "📩 Your message has been sent to the operator. Please wait for a reply!",
        'ref_info': "🔗 **Your referral link:**\n{link}\n\n👥 Invited: {count} users",
        'btn_ref': "🔗 Referral Link",
        'btn_lang': "🌐 Language / Язык / Dil"
    },
    'tk': {
        'welcome': "👋 Salam! Dil saýlaň / Выберите язык / Select language:",
        'lang_set': "✅ Dil saýlandy: Türkmen dili.\nHatyňyzy ýazyň, оператор сизге tiz арада jogap берер.",
        'msg_sent': "📩 Hatyňyz оператора ugradyldy. Jogaba garaşyň!",
        'ref_info': "🔗 **Siziň referal salgyňyz:**\n{link}\n\n👥 Çagyrylanlar: {count} adam",
        'btn_ref': "🔗 Referal salgy",
        'btn_lang': "🌐 Dil / Language / Язык"
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
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text=TEXTS[lang]['btn_ref']), types.KeyboardButton(text=TEXTS[lang]['btn_lang'])]
        ],
        resize_keyboard=True
    )

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

@dp.message(F.chat.type == "private", F.from_user.id != ADMIN_ID)
async def forward_to_admin(message: types.Message):
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
        f"📩 **Новое обращение!**\n\n"
        f"👤 **От:** {username} (ID: `{user_id}`)\n"
        f"🤝 **Источник:** {referrer_info}\n"
        f"🌐 **Язык:** {lang.upper()}\n\n"
        f"💬 **Текст:** {message.text}"
    )

    reply_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Ответить клиенту", callback_data=f"reply_{user_id}")]
    ])

    await bot.send_message(chat_id=ADMIN_ID, text=admin_caption, parse_mode="Markdown", reply_markup=reply_kb)
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
        await bot.send_message(chat_id=target_user_id, text=f"👨‍💻 **Ответ оператора:**\n\n{message.text}", parse_mode="Markdown")
        await message.answer("✅ Ответ успешно отправлен клиенту!")
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")

    await state.clear()

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
