import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from datetime import datetime
import re

# ============= НАСТРОЙКИ =============
TOKEN = os.environ.get("TELEGRAM_TOKEN", "8320251593:AAG9xwKfjI3QtA5EKZHAFfKHaKNY_iDF1O8")
BARISTA_GROUP_ID = -5239112663
OWNER_ID = 5063665522
COFFEE_SHOP_NAME = "КОФЕМОЛЛ"
COFFEE_SHOP_ADDRESS = "центральная д.67"
COFFEE_SHOP_PHONE = "89175212528"
BONUS_PERCENT = 3
# =====================================

user_data = {}
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def escape_markdown(text):
    if not text: return text
    for ch in ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
        text = text.replace(ch, f'\\{ch}')
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ['group', 'supergroup']: return
    keyboard = [[InlineKeyboardButton("🌟 ПОЛУЧИТЬ БОНУСНУЮ КАРТУ", callback_data="register")]]
    await update.message.reply_text(
        f"☕ {COFFEE_SHOP_NAME}\n📍 {COFFEE_SHOP_ADDRESS}\n\n"
        f"🎁 Бонус: {BONUS_PERCENT}% с каждой покупки\n"
        f"💰 1 бонус = 1 рубль\n"
        f"❓ Узнать баланс - спросите бариста\n\n"
        f"👇 Нажмите кнопку",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user_data[user_id] = {'step': 'phone'}
    await query.edit_message_text("📝 Введите ваш номер телефона\nНапример: +79991234567")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if user_id not in user_data:
        await update.message.reply_text("Нажмите /start")
        return
    step = user_data[user_id].get('step')

    if step == 'phone':
        phone = re.sub(r'[^\d]', '', text)
        if phone.startswith('8'): phone = '7' + phone[1:]
        elif phone.startswith('7'): phone = '7' + phone[1:]
        else: phone = '7' + phone[-10:] if len(phone) >= 10 else phone
        phone = '+' + phone

        if not re.match(r'^\+7[0-9]{10}$', phone):
            await update.message.reply_text("❌ Неверный формат")
            return
        user_data[user_id]['phone'] = phone
        user_data[user_id]['step'] = 'name'
        await update.message.reply_text("✅ Введите ваше имя:")

    elif step == 'name':
        name = text
        phone = user_data[user_id].get('phone')
        username = update.effective_user.username or 'нет'
        now = datetime.now().strftime("%d.%m.%Y %H:%M")

        try:
            await context.bot.send_message(
                chat_id=BARISTA_GROUP_ID,
                text=f"🆕 **НОВЫЙ КЛИЕНТ**\n\n👤 {name}\n📱 {phone}\n🆔 @{username}\n📅 {now}"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки бариста: {e}")

        await update.message.reply_text(
            f"✅ **ГОТОВО!**\n📍 {COFFEE_SHOP_ADDRESS}\n📞 {COFFEE_SHOP_PHONE}"
        )
        del user_data[user_id]

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^register$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Бот запущен и слушает сообщения...")
    app.run_polling()

if __name__ == "__main__":
    main()
