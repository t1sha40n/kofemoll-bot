import os
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from datetime import datetime
import re
import asyncio

# ============= НАСТРОЙКИ =============
TOKEN = os.environ.get("TELEGRAM_TOKEN", "8320251593:AAG9xwKfjI3QtA5EKZHAFfKHaKNY_iDF1O8")
BARISTA_GROUP_ID = -5239112663
OWNER_ID = 5063665522
COFFEE_SHOP_NAME = "КОФЕМОЛЛ"
COFFEE_SHOP_ADDRESS = "центральная д.67"
COFFEE_SHOP_PHONE = "89175212528"
BONUS_PERCENT = 3
# =====================================

# Хранилище
user_data = {}

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def escape_markdown(text):
    if not text:
        return text
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

# Создаем Flask приложение (для health check)
flask_app = Flask(__name__)

@flask_app.route('/health')
def health():
    """Render пингует этот адрес каждые 5 минут"""
    return 'OK', 200

@flask_app.route('/')
def index():
    return 'Bot is running!'

# Создаем Telegram бота
bot_app = Application.builder().token(TOKEN).build()

# ============= ОБРАБОТЧИКИ =============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ['group', 'supergroup']:
        return
    keyboard = [[InlineKeyboardButton("🌟 ПОЛУЧИТЬ БОНУСНУЮ КАРТУ", callback_data="register")]]
    await update.message.reply_text(
        f"☕ {COFFEE_SHOP_NAME}\n📍 {COFFEE_SHOP_ADDRESS}\n\n"
        f"🎁 Бонус: {BONUS_PERCENT}% с каждой покупки\n"
        f"💰 1 бонус = 1 рубль\n"
        f"❓ Узнать баланс - спросите бариста\n\n"
        f"👇 Нажмите кнопку",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user_data[user_id] = {'step': 'phone'}
    await query.edit_message_text(
        "📝 **Введите ваш номер телефона**\nНапример: +79991234567",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_data:
        await update.message.reply_text("Нажмите /start")
        return
    
    step = user_data[user_id].get('step')
    
    if step == 'phone':
        phone = text.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if phone.startswith('8'):
            phone = '+7' + phone[1:]
        elif phone.startswith('7'):
            phone = '+' + phone
        elif not phone.startswith('+7'):
            phone = '+7' + phone[-10:] if len(phone) >= 10 else phone
        
        if not re.match(r'^\+7[0-9]{10}$', phone):
            await update.message.reply_text("❌ Неверный формат")
            return
        
        user_data[user_id]['phone'] = phone
        user_data[user_id]['step'] = 'name'
        await update.message.reply_text("✅ **Введите ваше имя:**", parse_mode='Markdown')
    
    elif step == 'name':
        name = text
        phone = user_data[user_id].get('phone', 'не указан')
        username = update.effective_user.username or 'нет'
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ ВНЕСЁН", callback_data=f"done_{user_id}"),
                InlineKeyboardButton("⏳ НЕ ВНЕСЁН", callback_data=f"pending_{user_id}")
            ]
        ])
        
        try:
            await context.bot.send_message(
                chat_id=BARISTA_GROUP_ID,
                text=f"🆕 **НОВЫЙ КЛИЕНТ**\n\n👤 {escape_markdown(name)}\n📱 {escape_markdown(phone)}\n🆔 @{escape_markdown(username)}\n📅 {now}",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка: {e}")
        
        await update.message.reply_text(
            f"✅ **ГОТОВО!**\n📍 {COFFEE_SHOP_ADDRESS}\n📞 {COFFEE_SHOP_PHONE}",
            parse_mode='Markdown'
        )
        del user_data[user_id]

async def barista_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if update.effective_chat.id != BARISTA_GROUP_ID:
        return
    
    data = query.data.split('_')
    action = data[0]
    user_id = data[1]
    barista = query.from_user.first_name
    
    if action == 'done':
        new_text = f"{query.message.text}\n\n✅ Внёс: {barista}"
        await query.edit_message_text(text=new_text, parse_mode='Markdown')
        await query.edit_message_reply_markup(reply_markup=None)
    else:
        new_text = f"{query.message.text}\n\n⏳ Отметил: {barista}"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ ВНЕСЁН", callback_data=f"done_{user_id}")]
        ])
        await query.edit_message_text(text=new_text, parse_mode='Markdown', reply_markup=keyboard)

# Добавляем обработчики
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(button_handler, pattern="^register$"))
bot_app.add_handler(CallbackQueryHandler(barista_callback, pattern="^(done|pending)_"))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ============= ЗАПУСК =============
def run_bot():
    """Запускаем бота в отдельном потоке"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_app.initialize())
    loop.run_until_complete(bot_app.start())
    loop.run_forever()

if __name__ == "__main__":
    import threading
    # Запускаем бота в фоновом потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем Flask (для health check)
    port = int(os.environ.get('PORT', 10000))
    flask_app.run(host='0.0.0.0', port=port)
