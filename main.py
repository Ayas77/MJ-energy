import subprocess
import sys

# Авто-установка необходимых библиотек
for pkg in ["aiogram==3.15.0", "aiosqlite==0.20.0", "aiohttp==3.10.11"]:
    try:
        mod_name = pkg.split("==")[0]
        __import__(mod_name)
    except ImportError:
        print(f"Установка {pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

import os
import logging
import asyncio
import urllib.parse
from datetime import datetime, timedelta
import aiosqlite
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8923920954:AAGpJQyWtwCjeO8mR2s4RW9TeSnPm-UQ12Q"
ADMIN_ID = 8735103964

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class UserState(StatesGroup):
    waiting_for_payout_req = State()

class AdminState(StatesGroup):
    waiting_for_reply = State()
    waiting_for_broadcast = State()

TEXTS = {
    'ru': {
        'welcome': "👋 Здравствуйте! Выберите язык / Select language / Dil saýlaň:",
        'lang_set': "✅ Язык установлен: Русский.\nВыберите действие в меню ниже или напишите сообщение оператору.",
        'msg_sent': "📩 Ваше сообщение отправлено оператору. Ожидайте ответа!",
        'ref_info': (
            "🔗 **Ваша реферальная ссылка:**\n`{link}`\n\n"
            "👥 **Приглашено:** {count} чел.\n"
            "🛒 **Оплачено заказов:** {paid_count}\n"
            "💰 **Заработано (40%):** {earned} TMT"
        ),
        'btn_buy': "🛒 Купить VPN",
        'btn_ref': "🔗 Реферальная ссылка",
        'btn_lang': "🌐 Язык / Language / Dil",
        'btn_help': "❓ Инструкция",
        'btn_test': "🎁 Тест на 24 часа",
        'tariffs_title': "⚡ **Выберите подходящий тариф VPN:**",
        'tariff_100_btn': "📱 100 манат ($5) — 1 устройство",
        'tariff_200_btn': "♾️ 200 манат ($10) — Безлимит устройств",
        'choose_pay_method': "💳 **Выберите способ оплаты для тарифа {tariff}:**",
        'btn_pay_phone': "📱 Оплатить по номеру",
        'btn_pay_crypto': "💎 Оплатить криптовалютой",
        'payment_phone_text': (
            "💳 **Оплата по номеру телефона:**\n\n"
            "Вы выбрали тариф: **{tariff}**\n\n"
            "📌 **Номера для оплаты:**\n"
            "`+99362565792`\n"
            "`+99361843366`\n\n"
            "💡 *Если перевод с номера на номер не проходит — оплатите через терминал.*\n\n"
            "После оплаты нажмите кнопку **«✅ Я оплатил»** ниже и отправьте чек или скриншот прямо в этот чат."
        ),
        'payment_crypto_text': (
            "💎 **Оплата криптовалютой:**\n\n"
            "Вы выбрали тариф: **{tariff}**\n\n"
            "📌 **Наши крипто-кошельки:**\n\n"
            "🔹 **USDT (TRC20):**\n`TSRfr6UQiEuV17U9XmSfmWGZQiPA3NYqAv`\n\n"
            "🔹 **BTC (Bitcoin):**\n`3GRApv73rPGn7JMtueGAaY33SbviiQdnbR`\n\n"
            "🔹 **USDT (BEP20):**\n`0xbb7d1b44a4da704ecd3ce89e92b09ea5fbf5e4b1`\n\n"
            "🔹 **ETH (BEP20):**\n`0xbb7d1b44a4da704ecd3ce89e92b09ea5fbf5e4b1`\n\n"
            "После перевода нажмите кнопку **«✅ Я оплатил»** и отправьте скриншот или хеш транзакции оператору."
        ),
        'share_text': "Привет! Пользуюсь отличным скоростным VPN. Держи ссылку:",
        'btn_share': "📲 Поделиться с друзьями",
        'btn_withdraw': "💸 Запросить вывод средств",
        'btn_i_paid': "✅ Я оплатил",
        'paid_notify_user': "⏳ Ваши данные отправлены оператору. Ожидайте подтверждения и ключи!",
        'enter_payout_info': "✍️ Введите номер карты или телефона для получения выплаты:",
        'payout_sent': "✅ Заявка на вывод отправлена оператору!",
        'test_requested': "🎁 Заявка на тестовый период отправлена оператору! Ожидайте ключ.",
        'test_already_used': "❌ Вы уже запрашивали тестовый период ранее.",
        'instructions': (
            "📖 **Инструкция по настройке VPN:**\n\n"
            "📱 **Android:**\n"
            "1. Скачайте приложение **v2rayNG** или **Happ** из Google Play.\n"
            "2. Скопируйте ключ, полученный от оператора.\n"
            "3. Откройте приложение, нажмите `+` -> `Импорт из буфера обмена`.\n"
            "4. Нажмите на подключение.\n\n"
            "🍏 **iOS (iPhone / iPad):**\n"
            "1. Установите **Streisand** или **V2Box** из App Store.\n"
            "2. Скопируйте ключ и вставьте его через плюсик `+` в приложении.\n\n"
            "💻 **Windows / macOS:**\n"
            "1. Используйте программу **v2rayN** или **Nekoray**.\n"
            "2. Вставьте ключ из буфера обмена (`Ctrl+V`) и включите системный прокси."
        )
    },
    'en': {
        'welcome': "👋 Hello! Select language / Выберите язык / Dil saýlaň:",
        'lang_set': "✅ Language set: English.\nSelect an option from the menu below or send a message to the operator.",
        'msg_sent': "📩 Your message has been sent to the operator. Please wait for a reply!",
        'ref_info': (
            "🔗 **Your referral link:**\n`{link}`\n\n"
            "👥 **Invited:** {count} users\n"
            "🛒 **Paid orders:** {paid_count}\n"
            "💰 **Earned (40%):** {earned} TMT"
        ),
        'btn_buy': "🛒 Buy VPN",
        'btn_ref': "🔗 Referral Link",
        'btn_lang': "🌐 Language / Язык / Dil",
        'btn_help': "❓ Instructions",
        'btn_test': "🎁 24h Free Trial",
        'tariffs_title': "⚡ **Select your VPN plan:**",
        'tariff_100_btn': "📱 100 TMT ($5) — 1 device",
        'tariff_200_btn': "♾️ 200 TMT ($10) — Unlimited devices",
        'choose_pay_method': "💳 **Select payment method for plan {tariff}:**",
        'btn_pay_phone': "📱 Pay by phone number",
        'btn_pay_crypto': "💎 Pay with Crypto",
        'payment_phone_text': (
            "💳 **Payment by phone number:**\n\n"
            "Selected plan: **{tariff}**\n\n"
            "📌 **Payment phone numbers:**\n"
            "`+99362565792`\n"
            "`+99361843366`\n\n"
            "💡 *If transfer from number to number fails, pay via terminal.*\n\n"
            "After payment, click the **«✅ I have paid»** button below and send the receipt or screenshot in this chat."
        ),
        'payment_crypto_text': (
            "💎 **Crypto payment:**\n\n"
            "Selected plan: **{tariff}**\n\n"
            "📌 **Our crypto wallets:**\n\n"
            "🔹 **USDT (TRC20):**\n`TSRfr6UQiEuV17U9XmSfmWGZQiPA3NYqAv`\n\n"
            "🔹 **BTC (Bitcoin):**\n`3GRApv73rPGn7JMtueGAaY33SbviiQdnbR`\n\n"
            "🔹 **USDT (BEP20):**\n`0xbb7d1b44a4da704ecd3ce89e92b09ea5fbf5e4b1`\n\n"
            "🔹 **ETH (BEP20):**\n`0xbb7d1b44a4da704ecd3ce89e92b09ea5fbf5e4b1`\n\n"
            "After transfer, click **«✅ I have paid»** and send the screenshot or tx hash in this chat."
        ),
        'share_text': "Hey! I'm using a fast VPN service. Here is the link:",
        'btn_share': "📲 Share with friends",
        'btn_withdraw': "💸 Request payout",
        'btn_i_paid': "✅ I have paid",
        'paid_notify_user': "⏳ Information sent to the operator. Please wait for verification and keys!",
        'enter_payout_info': "✍️ Enter your card or phone number for payout:",
        'payout_sent': "✅ Payout request has been sent to the operator!",
        'test_requested': "🎁 Trial request sent to the operator! Please wait for your key.",
        'test_already_used': "❌ You have already used the free trial.",
        'instructions': (
            "📖 **VPN Setup Instructions:**\n\n"
            "📱 **Android:** Download **v2rayNG** or **Happ** from Google Play. Copy your key and import from clipboard.\n"
            "🍏 **iOS:** Install **Streisand** or **V2Box** from App Store. Import your key.\n"
            "💻 **Windows / macOS:** Use **v2rayN** or **Nekoray**."
        )
    },
    'tk': {
        'welcome': "👋 Salam! Dil saýlaň / Выберите язык / Select language:",
        'lang_set': "✅ Dil saýlandy: Türkmen dili.\nAşakdaky menýudan bölümi saýlaň ýa-da оператора hat ýazyň.",
        'msg_sent': "📩 Hatyňyz оператора ugradyldy. Jogaba garaşyň!",
        'ref_info': (
            "🔗 **Siziň referal salgyňyz:**\n`{link}`\n\n"
            "👥 **Çagyrylanlar:** {count} adam\n"
            "🛒 **Tölenenen заказлар:** {paid_count}\n"
            "💰 **Заработок (40%):** {earned} TMT"
        ),
        'btn_buy': "🛒 VPN satyn almak",
        'btn_ref': "🔗 Referal salgy",
        'btn_lang': "🌐 Dil / Language / Язык",
        'btn_help': "❓ Gözükdirme",
        'btn_test': "🎁 24 sagatlyk synag",
        'tariffs_title': "⚡ **Töleg tarifini saýlaň:**",
        'tariff_100_btn': "📱 100 manat ($5) — 1 enjam",
        'tariff_200_btn': "♾️ 200 manat ($10) — Päksiz enjam",
        'choose_pay_method': "💳 **{tariff} tarifi üçin töleg usulyny saýlaň:**",
        'btn_pay_phone': "📱 Telefon belgi arkaly tölemek",
        'btn_pay_crypto': "💎 Kriptowalýuta arkaly tölemek",
        'payment_phone_text': (
            "💳 **Telefon belgi arkaly töleg:**\n\n"
            "Saýlanan tarif: **{tariff}**\n\n"
            "📌 **Töleg üçin telefon belgiler:**\n"
            "`+99362565792`\n"
            "`+99361843366`\n\n"
            "💡 *Nomerden nomere töleg geçmese — terminal arkaly töleň.*\n\n"
            "Töleg edeniňizden soň **«✅ Men töledim»** düwmesine басыň we çeki (скриншот) şu çata ugradyň."
        ),
        'payment_crypto_text': (
            "💎 **Kriptowalýuta arkaly töleg:**\n\n"
            "Saýlanan tarif: **{tariff}**\n\n"
            "📌 **Biziň kripto gapjyklarymyz:**\n\n"
            "🔹 **USDT (TRC20):**\n`TSRfr6UQiEuV17U9XmSfmWGZQiPA3NYqAv`\n\n"
            "🔹 **BTC (Bitcoin):**\n`3GRApv73rPGn7JMtueGAaY33SbviiQdnbR`\n\n"
            "🔹 **USDT (BEP20):**\n`0xbb7d1b44a4da704ecd3ce89e92b09ea5fbf5e4b1`\n\n"
            "🔹 **ETH (BEP20):**\n`0xbb7d1b44a4da704ecd3ce89e92b09ea5fbf5e4b1`\n\n"
            "Geçirim edeniňizden soň **«✅ Men töledim»** düwmesine басыň we çeki (скриншот) ugradyň."
        ),
        'share_text': "Salam! Men çalt VPN ulanýaryn. Şyltylary şu ýerden alyp bilersiňiz:",
        'btn_share': "📲 Dostlaryň bilen paýlaş",
        'btn_withdraw': "💸 Pul çykarmak haýyşy",
        'btn_i_paid': "✅ Men töledim",
        'paid_notify_user': "⏳ Maglumatlar оператора ugradyldy. Barlag we açarlar üçin garaşyň!",
        'enter_payout_info': "✍️ Pul geçirmek üçin karta ýa-da telefon belgiňizi ýazyň:",
        'payout_sent': "✅ Haýyşyňyz оператора ugradyldy!",
        'test_requested': "🎁 Synag üçin haýyş ugradyldy! Açaryňyza garaşyň.",
        'test_already_used': "❌ Siz eýýäm synag möhletini ulandyňyz.",
        'instructions': (
            "📖 **VPN sazlamak gözükdirmesi:**\n\n"
            "📱 **Android:** Google Play-den **v2rayNG** ýa-da **Happ** programmasyny ýükläň. Açary göçürip alyň we goşuň.\n"
            "🍏 **iOS:** App Store-dan **Streisand** ýa-da **V2Box** ýükläň.\n"
            "💻 **Windows / macOS:** **v2rayN** ýa-da **Nekoray** ulan nyň."
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
                language TEXT DEFAULT 'ru',
                earnings REAL DEFAULT 0.0,
                purchases_count INTEGER DEFAULT 0,
                last_selected_tariff INTEGER DEFAULT 100,
                used_test INTEGER DEFAULT 0,
                subscription_until TEXT
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
            [KeyboardButton(text=TEXTS[lang]['btn_buy']), KeyboardButton(text=TEXTS[lang]['btn_test'])],
            [KeyboardButton(text=TEXTS[lang]['btn_ref']), KeyboardButton(text=TEXTS[lang]['btn_help'])],
            [KeyboardButton(text=TEXTS[lang]['btn_lang'])]
        ],
        resize_keyboard=True
    )

def get_tariffs_keyboard(lang):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=TEXTS[lang]['tariff_100_btn'], callback_data=f"buy_100_{lang}")],
        [InlineKeyboardButton(text=TEXTS[lang]['tariff_200_btn'], callback_data=f"buy_200_{lang}")]
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

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(TEXTS[lang]['lang_set'], reply_markup=get_main_keyboard(lang))
    await callback.answer()

@dp.message(F.text.in_(["🛒 Купить VPN", "🛒 Buy VPN", "🛒 VPN satyn almak"]))
async def buy_vpn_handler(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT language FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            lang = row[0] if (row and row[0]) else 'ru'

    await message.answer(TEXTS[lang]['tariffs_title'], reply_markup=get_tariffs_keyboard(lang), parse_mode="Markdown")

@dp.message(F.text.in_(["❓ Инструкция", "❓ Instructions", "❓ Gözükdirme"]))
async def instructions_handler(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT language FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            lang = row[0] if (row and row[0]) else 'ru'

    await message.answer(TEXTS[lang]['instructions'], parse_mode="Markdown")

@dp.message(F.text.in_(["🎁 Тест на 24 часа", "🎁 24h Free Trial", "🎁 24 sagatlyk synag"]))
async def test_period_handler(message: types.Message):
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else "Отсутствует"

    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT language, used_test FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            lang = row[0] if row else 'ru'
            used_test = row[1] if (row and row[1]) else 0

    if used_test == 1:
        await message.answer(TEXTS[lang]['test_already_used'])
        return

    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("UPDATE users SET used_test = 1 WHERE user_id = ?", (user_id,))
        await db.commit()

    admin_msg = (
        f"🎁 **ЗАПРОС ТЕСТОВОГО ПЕРИОДА (24 часа)!**\n\n"
        f"👤 **Пользователь:** {username} (ID: `{user_id}`)\n"
        f"🌐 **Язык:** {lang.upper()}\n"
        f"📌 Выдайте тестовый ключ!"
    )
    reply_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Выдать тестовый ключ", callback_data=f"reply_{user_id}")]
    ])

    await bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown", reply_markup=reply_kb)
    await message.answer(TEXTS[lang]['test_requested'])

@dp.callback_query(F.data.startswith("buy_"))
async def process_tariff_selection(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    tariff_code = int(parts[1])
    lang = parts[2] if len(parts) > 2 else 'ru'
    
    user_id = callback.from_user.id
    username = f"@{callback.from_user.username}" if callback.from_user.username else "Отсутствует"

    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("UPDATE users SET last_selected_tariff = ?, language = ? WHERE user_id = ?", (tariff_code, lang, user_id))
        await db.commit()

        async with db.execute("SELECT referrer_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user_data = await cursor.fetchone()
            referrer_id = user_data[0] if user_data else None

    tariff_name = TEXTS[lang]['tariff_100_btn'] if tariff_code == 100 else TEXTS[lang]['tariff_200_btn']

    referrer_info = "Прямой заход"
    if referrer_id:
        async with aiosqlite.connect("bot_database.db") as db:
            async with db.execute("SELECT username FROM users WHERE user_id = ?", (referrer_id,)) as cursor:
                ref_user = await cursor.fetchone()
                ref_name = f"@{ref_user[0]}" if ref_user and ref_user[0] != "NoUsername" else f"ID: {referrer_id}"
                referrer_info = f"Партнер: {ref_name} (ID: `{referrer_id}`) — **40%**"

    admin_alert = (
        f"🛍 **ВЫБОР ТАРИФА!**\n\n"
        f"💳 **Тариф:** {tariff_name}\n"
        f"👤 **Клиент:** {username} (ID: `{user_id}`)\n"
        f"🤝 **Источник:** {referrer_info}\n"
        f"🌐 **Язык клиента:** {lang.upper()}"
    )

    reply_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить оплату (Начислить 40%)", callback_data=f"confirm_{user_id}_{tariff_code}")],
        [InlineKeyboardButton(text="💬 Ответить / Выдать доступ", callback_data=f"reply_{user_id}")]
    ])

    await bot.send_message(chat_id=ADMIN_ID, text=admin_alert, parse_mode="Markdown", reply_markup=reply_kb)

    pay_method_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=TEXTS[lang]['btn_pay_phone'], callback_data=f"paymeth_phone_{tariff_code}_{lang}")],
        [InlineKeyboardButton(text=TEXTS[lang]['btn_pay_crypto'], callback_data=f"paymeth_crypto_{tariff_code}_{lang}")]
    ])

    await callback.message.edit_text(
        TEXTS[lang]['choose_pay_method'].format(tariff=tariff_name),
        parse_mode="Markdown",
        reply_markup=pay_method_kb
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("paymeth_"))
async def show_payment_details(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    method = parts[1]
    tariff_code = int(parts[2])
    lang = parts[3] if len(parts) > 3 else 'ru'

    tariff_name = TEXTS[lang]['tariff_100_btn'] if tariff_code == 100 else TEXTS[lang]['tariff_200_btn']

    pay_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=TEXTS[lang]['btn_i_paid'], callback_data=f"userpaid_{tariff_code}_{method}_{lang}")]
    ])

    if method == "phone":
        text = TEXTS[lang]['payment_phone_text'].format(tariff=tariff_name)
    else:
        text = TEXTS[lang]['payment_crypto_text'].format(tariff=tariff_name)

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=pay_kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("userpaid_"))
async def user_paid_handler(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    tariff_code = int(parts[1])
    method = parts[2]
    lang = parts[3] if len(parts) > 3 else 'ru'
    
    user_id = callback.from_user.id
    username = f"@{callback.from_user.username}" if callback.from_user.username else "Отсутствует"

    usd_amount = "$5" if tariff_code == 100 else "$10"
    method_str = "По номеру телефона" if method == "phone" else "Криптовалюта"

    admin_msg = (
        f"⚠️ **КЛИЕНТ НАЖАЛ \"Я ОПЛАТИЛ\"!**\n\n"
        f"👤 **Клиент:** {username} (ID: `{user_id}`)\n"
        f"💳 **Тариф:** {tariff_code} TMT ({usd_amount})\n"
        f"⚙️ **Метод оплаты:** {method_str}\n"
        f"🌐 **Язык:** {lang.upper()}\n"
        f"📌 Проверьте зачисление средств и вышлите ключи!"
    )

    reply_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить оплату (Начислить 40%)", callback_data=f"confirm_{user_id}_{tariff_code}")],
        [InlineKeyboardButton(text="💬 Ответить / Выдать доступ", callback_data=f"reply_{user_id}")]
    ])

    await bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown", reply_markup=reply_kb)
    await callback.answer(TEXTS[lang]['paid_notify_user'], show_alert=True)

@dp.callback_query(F.data.startswith("confirm_"), F.from_user.id == ADMIN_ID)
async def confirm_payment_handler(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[1])
    tariff_amount = int(parts[2])

    reward = tariff_amount * 0.40
    until_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute(
            "UPDATE users SET purchases_count = purchases_count + 1, subscription_until = ? WHERE user_id = ?",
            (until_date, user_id)
        )
        await db.commit()

        async with db.execute("SELECT referrer_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            referrer_id = row[0] if row else None

        if referrer_id:
            await db.execute("UPDATE users SET earnings = earnings + ? WHERE user_id = ?", (reward, referrer_id))
            await db.commit()

            try:
                await bot.send_message(
                    chat_id=referrer_id,
                    text=f"🎉 **Вам зачислено +{int(reward)} TMT!**\nВаш реферал совершил оплату.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

    await callback.message.edit_text(
        callback.message.text + f"\n\n✅ **Оплата подтверждена!** Подписка установлена до `{until_date}`. Партнёру начислено: {int(reward)} TMT.",
        parse_mode="Markdown"
    )
    await callback.answer("Оплата подтверждена!")

# --- РЕФЕРАЛЬНАЯ СИСТЕМА И ВЫВОД ---
@dp.message(F.text.in_(["🔗 Реферальная ссылка", "🔗 Referral Link", "🔗 Referal salgy"]))
async def ref_handler(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT language, earnings FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            lang = row[0] if row else 'ru'
            earnings = row[1] if (row and row[1]) else 0.0

        async with db.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,)) as cursor:
            count = (await cursor.fetchone())[0]

        async with db.execute("SELECT SUM(purchases_count) FROM users WHERE referrer_id = ?", (user_id,)) as cursor:
            paid_row = await cursor.fetchone()
            paid_count = paid_row[0] if (paid_row and paid_row[0]) else 0

    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"

    share_msg = f"{TEXTS[lang]['share_text']}\n{ref_link}"
    share_url = f"https://t.me/share/url?url={urllib.parse.quote(share_msg)}"

    ref_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=TEXTS[lang]['btn_share'], url=share_url)],
        [InlineKeyboardButton(text=TEXTS[lang]['btn_withdraw'], callback_data="req_payout")]
    ])

    await message.answer(
        TEXTS[lang]['ref_info'].format(
            link=ref_link, 
            count=count, 
            paid_count=paid_count, 
            earned=int(earnings)
        ), 
        parse_mode="Markdown",
        reply_markup=ref_kb
    )

@dp.callback_query(F.data == "req_payout")
async def start_payout_request(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT language, earnings FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            lang = row[0] if row else 'ru'
            earnings = row[1] if (row and row[1]) else 0.0

    if earnings <= 0:
        await callback.answer("❌ У вас пока нет доступных средств для вывода!", show_alert=True)
        return

    await state.set_state(UserState.waiting_for_payout_req)
    await callback.message.answer(TEXTS[lang]['enter_payout_info'])
    await callback.answer()

@dp.message(UserState.waiting_for_payout_req)
async def process_payout_info(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else "Отсутствует"
    payout_details = message.text

    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT language, earnings FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            lang = row[0] if row else 'ru'
            earnings = row[1] if (row and row[1]) else 0.0

    admin_msg = (
        f"💸 **ЗАЯВКА НА ВЫВОД СРЕДСТВ!**\n\n"
        f"👤 **Партнер:** {username} (ID: `{user_id}`)\n"
        f"💰 **Сумма:** {int(earnings)} TMT\n"
        f"📌 **Реквизиты:** `{payout_details}`"
    )

    reply_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Выплачено (Обнулить баланс)", callback_data=f"payoutdone_{user_id}_{int(earnings)}")]
    ])

    await bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown", reply_markup=reply_kb)
    await message.answer(TEXTS[lang]['payout_sent'])
    await state.clear()

@dp.callback_query(F.data.startswith("payoutdone_"), F.from_user.id == ADMIN_ID)
async def complete_payout_handler(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[1])
    amount = int(parts[2])

    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("UPDATE users SET earnings = 0 WHERE user_id = ?", (user_id,))
        await db.commit()

    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"✅ **Ваша выплата {amount} TMT успешно произведена!**\nСпасибо за сотрудничество!",
            parse_mode="Markdown"
        )
    except Exception:
        pass

    await callback.message.edit_text(
        callback.message.text + f"\n\n✅ **Выплата подтверждена, баланс пользователя обнулен!**",
        parse_mode="Markdown"
    )
    await callback.answer("Баланс обнулен!")

# --- АДМИН ПАНЕЛЬ (/admin) & РАССЫЛКА ---
@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel_cmd(message: types.Message):
    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            total_users = (await cursor.fetchone())[0]
        async with db.execute("SELECT SUM(purchases_count) FROM users") as cursor:
            total_sales = (await cursor.fetchone())[0] or 0

    stats_text = (
        f"🛠 **ПАНЕЛЬ АДМИНИСТРАТОРА**\n\n"
        f"👥 всего пользователей: **{total_users}**\n"
        f"🛒 Всего проданных подписок: **{total_sales}**\n"
    )

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Сделать рассылку всем", callback_data="start_broadcast")]
    ])

    await message.answer(stats_text, parse_mode="Markdown", reply_markup=admin_kb)

@dp.callback_query(F.data == "start_broadcast", F.from_user.id == ADMIN_ID)
async def start_broadcast_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.waiting_for_broadcast)
    await callback.message.answer("✍️ Пришлите текст или медиа (фото/видео), которое нужно разослать всем пользователям:")
    await callback.answer()

@dp.message(AdminState.waiting_for_broadcast, F.from_user.id == ADMIN_ID)
async def process_broadcast_msg(message: types.Message, state: FSMContext):
    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            users = await cursor.fetchall()

    success_count = 0
    fail_count = 0

    await message.answer("🚀 Рассылка начата...")

    for user in users:
        u_id = user[0]
        try:
            await bot.copy_message(chat_id=u_id, from_chat_id=message.chat.id, message_id=message.message_id)
            success_count += 1
            await asyncio.sleep(0.05) # Защита от спам-фильтра Telegram
        except Exception:
            fail_count += 1

    await message.answer(f"📊 **Рассылка завершена!**\n\n✅ Успешно: {success_count}\n❌ Не доставлено (заблокировали бота): {fail_count}")
    await state.clear()

@dp.message(F.text.in_([
    "🌐 Язык / Language / Dil",
    "🌐 Language / Язык / Dil",
    "🌐 Dil / Language / Язык"
]))
async def change_lang_handler(message: types.Message):
    await message.answer("Выберите язык / Select language / Dil saýlaň:", reply_markup=get_lang_keyboard())

@dp.message(F.chat.type == "private")
async def forward_to_admin(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state in [AdminState.waiting_for_reply.state, UserState.waiting_for_payout_req.state, AdminState.waiting_for_broadcast.state]:
        return

    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else "Отсутствует"

    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT referrer_id, language, last_selected_tariff FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user_data = await cursor.fetchone()
            referrer_id = user_data[0] if user_data else None
            lang = user_data[1] if user_data else 'ru'
            last_tariff = user_data[2] if (user_data and user_data[2]) else 100

    referrer_info = "Прямой заход"
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
        [InlineKeyboardButton(text="✅ Подтвердить оплату (Начислить 40%)", callback_data=f"confirm_{user_id}_{last_tariff}")],
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
