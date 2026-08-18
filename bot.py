import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import aiosqlite
from datetime import datetime

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = "8923920954:AAGpJQyWtwCjeO8mR2s4RW9TeSnPm-UQ12Q"
ADMIN_ID = 8735103964
DEFAULT_PERCENT = 40
# ===============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ---------- Переводы ----------
TEXTS = {
    "ru": {
        "choose_lang": "Выберите язык / Dil saýlaň / Choose language:",
        "welcome": "Привет, <b>{name}</b>!\n\nЭто бот для работы с VPN.\nНапиши сюда любой вопрос — я отвечу.",
        "my_stats_btn": "📊 Моя статистика",
        "my_link_btn": "🔗 Моя реферальная ссылка",
        "change_lang_btn": "🌐 Сменить язык",
        "your_link": "🔗 Твоя реферальная ссылка:\n\n<code>{link}</code>\n\nОтправляй её друзьям. Все, кто перейдёт по ней, закрепятся за тобой.",
        "stats": "📊 <b>Твоя статистика</b>\n\nПриглашено человек: <b>{count}</b>\nТвой процент: <b>{percent}%</b>\n\nКогда твои люди будут оплачивать — тебе будет начисляться {percent}%.",
        "lang_changed": "✅ Язык изменён на русский",
        "new_referral": "🆕 Новый реферал!\n\nЧеловек: <b>{name}</b> (@{username})\nID: <code>{user_id}</code>\nПригласил: <b>{ref_name}</b> (ID: <code>{ref_id}</code>)",
        "msg_header": "💬 Сообщение от клиента\n\nИмя: <b>{name}</b>\nЮзернейм: @{username}\nID: <code>{user_id}</code>\nРеферер: {referrer_info}\n─────────────────",
    },
    "tk": {
        "choose_lang": "Dil saýlaň / Выберите язык / Choose language:",
        "welcome": "Salam, <b>{name}</b>!\n\nBu VPN bilen işlemäge niýetlenen bot.\nIslendik soragyňyzy ýazyň — men jogap bererin.",
        "my_stats_btn": "📊 Mening statistikam",
        "my_link_btn": "🔗 Mening referal baglanyşygym",
        "change_lang_btn": "🌐 Dili üýtgetmek",
        "your_link": "🔗 Seniň referal baglanyşygyň:\n\n<code>{link}</code>\n\nDostlaryňa iber. Şu baglanyşyk bilen girenler saňa berkarar bolar.",
        "stats": "📊 <b>Seniň statistikasyň</b>\n\nÇagyrylan adamlar: <b>{count}</b>\nSeniň göterimiň: <b>{percent}%</b>\n\nAdamlar töleg edeninde saňa {percent}% hasaplanar.",
        "lang_changed": "✅ Dil türkmen diline üýtgedildi",
        "new_referral": "🆕 Täze referal!\n\nAdam: <b>{name}</b> (@{username})\nID: <code>{user_id}</code>\nÇagyran: <b>{ref_name}</b> (ID: <code>{ref_id}</code>)",
        "msg_header": "💬 Müşderiden hat\n\nAdy: <b>{name}</b>\nUlanyjy ady: @{username}\nID: <code>{user_id}</code>\nReferal: {referrer_info}\n─────────────────",
    },
    "en": {
        "choose_lang": "Choose language / Dil saýlaň / Выберите язык:",
        "welcome": "Hello, <b>{name}</b>!\n\nThis is a VPN service bot.\nWrite any question — I will reply.",
        "my_stats_btn": "📊 My statistics",
        "my_link_btn": "🔗 My referral link",
        "change_lang_btn": "🌐 Change language",
        "your_link": "🔗 Your referral link:\n\n<code>{link}</code>\n\nShare it with friends. Everyone who joins via this link will be assigned to you.",
        "stats": "📊 <b>Your statistics</b>\n\nInvited people: <b>{count}</b>\nYour percent: <b>{percent}%</b>\n\nWhen your people pay, you will receive {percent}%.",
        "lang_changed": "✅ Language changed to English",
        "new_referral": "🆕 New referral!\n\nUser: <b>{name}</b> (@{username})\nID: <code>{user_id}</code>\nInvited by: <b>{ref_name}</b> (ID: <code>{ref_id}</code>)",
        "msg_header": "💬 Message from client\n\nName: <b>{name}</b>\nUsername: @{username}\nID: <code>{user_id}</code>\nReferrer: {referrer_info}\n─────────────────",
    }
}

def t(lang: str, key: str, **kwargs):
    lang = lang if lang in TEXTS else "ru"
    text = TEXTS[lang].get(key, TEXTS["ru"].get(key, key))
    return text.format(**kwargs) if kwargs else text

# ---------- База данных ----------
async def init_db():
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                referrer_id INTEGER,
                percent REAL DEFAULT 40,
                lang TEXT DEFAULT 'ru',
                created_at TEXT
            )
        """)
        await db.commit()

async def add_user(user_id: int, username: str, full_name: str, referrer_id: int = None):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name, referrer_id, percent, lang, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, username, full_name, referrer_id, DEFAULT_PERCENT, "ru", datetime.now().isoformat())
        )
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("SELECT user_id, username, full_name, referrer_id, percent, lang FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def set_lang(user_id: int, lang: str):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
        await db.commit()

async def get_referrals_count(user_id: int):
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def set_percent(user_id: int, percent: float):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("UPDATE users SET percent = ? WHERE user_id = ?", (percent, user_id))
        await db.commit()

async def get_all_referrers():
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("""
            SELECT u.user_id, u.username, u.full_name, u.percent, COUNT(r.user_id) as refs
            FROM users u
            LEFT JOIN users r ON r.referrer_id = u.user_id
            GROUP BY u.user_id
            HAVING refs > 0
            ORDER BY refs DESC
        """) as cursor:
            return await cursor.fetchall()

# ---------- Клавиатуры ----------
def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton(text="🇹🇲 Türkmen", callback_data="lang_tk"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
        ]
    ])

def main_kb(lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "my_stats_btn"), callback_data="my_stats")],
        [InlineKeyboardButton(text=t(lang, "my_link_btn"), callback_data="my_link")],
        [InlineKeyboardButton(text=t(lang, "change_lang_btn"), callback_data="change_lang")],
    ])

# ---------- Хендлеры ----------
@dp.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    user = message.from_user
    referrer_id = None

    if command.args and command.args.startswith("ref_"):
        try:
            referrer_id = int(command.args.split("_")[1])
            if referrer_id == user.id:
                referrer_id = None
        except:
            referrer_id = None

    await add_user(user.id, user.username, user.full_name, referrer_id)

    # Уведомление админу о новом реферале
    if referrer_id:
        try:
            ref_user = await get_user(referrer_id)
            ref_name = ref_user[2] if ref_user else str(referrer_id)
            await bot.send_message(
                ADMIN_ID,
                t("ru", "new_referral",
                  name=user.full_name,
                  username=user.username or "нет",
                  user_id=user.id,
                  ref_name=ref_name,
                  ref_id=referrer_id)
            )
        except:
            pass

    # Проверяем, выбран ли уже язык
    db_user = await get_user(user.id)
    if db_user and db_user[5] and db_user[5] != "ru":  # если язык уже не дефолтный
        lang = db_user[5]
        await message.answer(t(lang, "welcome", name=user.full_name), reply_markup=main_kb(lang))
    else:
        await message.answer(t("ru", "choose_lang"), reply_markup=lang_kb())

@dp.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    await set_lang(callback.from_user.id, lang)
    await callback.message.edit_text(t(lang, "lang_changed"))
    await callback.message.answer(
        t(lang, "welcome", name=callback.from_user.full_name),
        reply_markup=main_kb(lang)
    )
    await callback.answer()

@dp.callback_query(F.data == "change_lang")
async def change_lang(callback: CallbackQuery):
    await callback.message.answer(t("ru", "choose_lang"), reply_markup=lang_kb())
    await callback.answer()

@dp.message(Command("lang"))
async def cmd_lang(message: Message):
    await message.answer(t("ru", "choose_lang"), reply_markup=lang_kb())

@dp.callback_query(F.data == "my_link")
async def my_link(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    lang = user[5] if user else "ru"
    link = f"https://t.me/mjenergy_bot?start=ref_{callback.from_user.id}"
    await callback.message.answer(t(lang, "your_link", link=link))
    await callback.answer()

@dp.callback_query(F.data == "my_stats")
async def my_stats(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    lang = user[5] if user else "ru"
    count = await get_referrals_count(callback.from_user.id)
    percent = user[4] if user else DEFAULT_PERCENT

    await callback.message.answer(t(lang, "stats", count=count, percent=percent))
    await callback.answer()

# ---------- Все сообщения → админу ----------
@dp.message(F.chat.type == "private")
async def forward_to_admin(message: Message):
    if message.from_user.id == ADMIN_ID:
        return

    user = await get_user(message.from_user.id)
    referrer_info = "Без реферера"

    if user and user[3]:
        ref = await get_user(user[3])
        if ref:
            referrer_info = f"{ref[2]} (@{ref[1] or 'нет'}) | ID: <code>{ref[0]}</code> | {ref[4]}%"

    header = t("ru", "msg_header",
               name=message.from_user.full_name,
               username=message.from_user.username or "нет",
               user_id=message.from_user.id,
               referrer_info=referrer_info)

    try:
        await bot.send_message(ADMIN_ID, header)
        await message.forward(ADMIN_ID)
    except Exception as e:
        logging.error(f"Ошибка пересылки: {e}")

# ---------- Админ ----------
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Рефереры", callback_data="admin_refs")],
        [InlineKeyboardButton(text="📈 Статистика", callback_data="admin_stats")],
    ])
    await message.answer("Админ-панель:", reply_markup=kb)

@dp.callback_query(F.data == "admin_refs")
async def admin_refs(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    refs = await get_all_referrers()
    if not refs:
        await callback.message.answer("Пока нет рефереров с людьми.")
        await callback.answer()
        return

    text = "👥 <b>Рефереры:</b>\n\n"
    for r in refs:
        text += f"• {r[2]} (@{r[1] or 'нет'})\n  ID: <code>{r[0]}</code> | Людей: <b>{r[4]}</b> | Процент: <b>{r[3]}%</b>\n\n"
    text += "\nИзменить процент:\n<code>/setpercent ID процент</code>"
    await callback.message.answer(text)
    await callback.answer()

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            total = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE referrer_id IS NOT NULL") as c:
            with_ref = (await c.fetchone())[0]

    await callback.message.answer(
        f"📈 <b>Общая статистика</b>\n\n"
        f"Всего пользователей: <b>{total}</b>\n"
        f"Пришли по рефке: <b>{with_ref}</b>"
    )
    await callback.answer()

@dp.message(Command("setpercent"))
async def cmd_setpercent(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        percent = float(parts[2])
        await set_percent(user_id, percent)
        await message.answer(f"✅ Процент для <code>{user_id}</code> установлен: <b>{percent}%</b>")
    except:
        await message.answer("Формат: <code>/setpercent ID процент</code>\nПример: /setpercent 123456789 35")

# ---------- Запуск ----------
async def main():
    await init_db()
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
