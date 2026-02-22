import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from datetime import datetime
import re

# Настройки
TOKEN = "8320251593:AAG9xwKfjI3QtA5EKZHAFfKHaKNY_iDF1O8"
BARISTA_GROUP_ID = -5239112663
OWNER_ID = 5063665522

# Данные кофейни
COFFEE_SHOP_NAME = "КОФЕМОЛЛ"
COFFEE_SHOP_ADDRESS = "центральная д.67"
COFFEE_SHOP_PHONE = "89175212528"
BONUS_PERCENT = 3

# Хранилище данных пользователей
user_data = {}

def escape_markdown(text):
    """Экранирует специальные символы для Markdown"""
    if not text:
        return text
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт - только кнопка получить карту"""
    if update.effective_chat.type in ['group', 'supergroup']:
        return
    
    keyboard = [[InlineKeyboardButton("🌟 ПОЛУЧИТЬ БОНУСНУЮ КАРТУ", callback_data="register")]]
    
    await update.message.reply_text(
        f"☕ {COFFEE_SHOP_NAME}\n📍 {COFFEE_SHOP_ADDRESS}\n\n"
        f"🎁 Бонус: {BONUS_PERCENT}% с каждой покупки\n"
        f"💰 1 бонус = 1 рубль\n"
        f"❓ Узнать баланс - спросите бариста\n\n"
        f"👇 Нажмите кнопку для получения карты",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопки регистрации"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Запоминаем что пользователь начал регистрацию
    user_data[user_id] = {'step': 'phone'}
    
    await query.edit_message_text(
        "📝 **Введите ваш номер телефона**\n"
        "Например: +79991234567",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений (телефон и имя)"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Если пользователь не начинал регистрацию
    if user_id not in user_data:
        await update.message.reply_text(
            "Нажмите /start чтобы начать регистрацию"
        )
        return
    
    step = user_data[user_id].get('step')
    
    # Шаг 1 - ввод телефона
    if step == 'phone':
        # Очистка номера
        phone = text.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if phone.startswith('8'):
            phone = '+7' + phone[1:]
        elif phone.startswith('7'):
            phone = '+' + phone
        elif not phone.startswith('+7'):
            phone = '+7' + phone[-10:] if len(phone) >= 10 else phone
        
        # Простая проверка
        if not re.match(r'^\+7[0-9]{10}$', phone):
            await update.message.reply_text(
                "❌ **Неверный формат**\n"
                "Введите как +79991234567",
                parse_mode='Markdown'
            )
            return
        
        # Сохраняем телефон
        user_data[user_id]['phone'] = phone
        user_data[user_id]['step'] = 'name'
        
        # Просим имя
        await update.message.reply_text(
            "✅ **Номер принят!**\n\n"
            "📝 **Введите ваше имя:**",
            parse_mode='Markdown'
        )
    
    # Шаг 2 - ввод имени
    elif step == 'name':
        name = text
        phone = user_data[user_id].get('phone', 'не указан')
        username = update.effective_user.username or 'нет'
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        # Экранируем специальные символы для Markdown
        safe_name = escape_markdown(name)
        safe_phone = escape_markdown(phone)
        safe_username = escape_markdown(username)
        
        # Кнопки для бариста
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ ВНЕСЁН В БАЗУ", callback_data=f"done_{user_id}"),
                InlineKeyboardButton("⏳ ЕЩЁ НЕ ВНЕСЁН", callback_data=f"pending_{user_id}")
            ]
        ])
        
        # Отправляем в группу бариста
        group_sent = False
        try:
            # Пробуем отправить с Markdown
            await context.bot.send_message(
                chat_id=BARISTA_GROUP_ID,
                text=f"🆕 **НОВЫЙ КЛИЕНТ {COFFEE_SHOP_NAME}**\n\n"
                     f"👤 **Имя:** {safe_name}\n"
                     f"📱 **Телефон:** `{safe_phone}`\n"
                     f"🆔 **Telegram:** @{safe_username}\n"
                     f"📅 **Время:** {now}\n\n"
                     f"⬇️ **Отметить статус:**",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            group_sent = True
        except Exception as e:
            logger.error(f"Ошибка отправки с Markdown: {e}")
            try:
                # Если не получилось - отправляем без Markdown
                await context.bot.send_message(
                    chat_id=BARISTA_GROUP_ID,
                    text=f"🆕 НОВЫЙ КЛИЕНТ {COFFEE_SHOP_NAME}\n\n"
                         f"👤 Имя: {name}\n"
                         f"📱 Телефон: {phone}\n"
                         f"🆔 Telegram: @{username}\n"
                         f"📅 Время: {now}\n\n"
                         f"⬇️ Отметить статус:",
                    reply_markup=keyboard
                )
                group_sent = True
            except Exception as e2:
                logger.error(f"Ошибка отправки без Markdown: {e2}")
        
        # Уведомление владельцу
        try:
            status = "✅ Отправлено в группу" if group_sent else "❌ Не отправлено в группу"
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"✅ Новый клиент: {name} - {phone}\n{status}"
            )
        except:
            pass
        
        # Завершаем регистрацию
        await update.message.reply_text(
            f"✅ **РЕГИСТРАЦИЯ ЗАВЕРШЕНА!**\n\n"
            f"🎁 Ваша карта {COFFEE_SHOP_NAME} активирована!\n\n"
            f"**Как получать бонусы:**\n"
            f"• Называйте **{phone}** при заказе\n"
            f"• Получайте **{BONUS_PERCENT}%** бонусами\n\n"
            f"📍 {COFFEE_SHOP_ADDRESS}\n"
            f"📞 {COFFEE_SHOP_PHONE}\n\n"
            f"❓ **Узнать баланс:** спросите у бариста",
            parse_mode='Markdown'
        )
        
        # Очищаем данные пользователя
        del user_data[user_id]

async def barista_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок бариста"""
    query = update.callback_query
    await query.answer()
    
    # Проверяем что это группа бариста
    if update.effective_chat.id != BARISTA_GROUP_ID:
        await query.message.reply_text("❌ Эта кнопка работает только в группе бариста")
        return
    
    # Разбираем callback_data
    data = query.data.split('_')
    action = data[0]
    user_id = data[1]
    
    barista_name = query.from_user.first_name
    current_text = query.message.text
    
    # Если нажали "ВНЕСЁН"
    if action == 'done':
        # Обновляем текст
        new_text = f"{current_text}\n\n✅ **Внёс в базу:** {barista_name}"
        # Убираем кнопки
        await query.edit_message_text(
            text=new_text,
            parse_mode='Markdown'
        )
        await query.edit_message_reply_markup(reply_markup=None)
    
    # Если нажали "ЕЩЁ НЕ ВНЕСЁН"
    elif action == 'pending':
        # Добавляем отметку, но ОСТАВЛЯЕМ кнопку "ВНЕСЁН"
        new_text = f"{current_text}\n\n⏳ **Отметил:** {barista_name} (ждёт внесения)"
        
        # Создаем новую клавиатуру только с кнопкой "ВНЕСЁН"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ ВНЕСЁН В БАЗУ", callback_data=f"done_{user_id}")]
        ])
        
        await query.edit_message_text(
            text=new_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена регистрации"""
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]
    await update.message.reply_text("❌ Регистрация отменена")

async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение ID чата (только для владельца)"""
    if update.effective_user.id == OWNER_ID:
        await update.message.reply_text(f"🆔 ID этого чата: `{update.effective_chat.id}`", parse_mode='Markdown')

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Запуск"""
    app = Application.builder().token(TOKEN).build()
    
    # Обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("chat_id", chat_id))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^register$"))
    app.add_handler(CallbackQueryHandler(barista_callback, pattern="^(done|pending)_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("="*50)
    print(f"☕ {COFFEE_SHOP_NAME} БОТ ЗАПУЩЕН")
    print("="*50)
    print(f"📍 Адрес: {COFFEE_SHOP_ADDRESS}")
    print(f"📞 Телефон: {COFFEE_SHOP_PHONE}")
    print(f"🎯 Бонус: {BONUS_PERCENT}%")
    print("-"*50)
    print("✅ Для клиентов: одна кнопка")
    print("👥 Для бариста:")
    print("  • При нажатии 'ВНЕСЁН' - кнопки исчезают")
    print("  • При нажатии 'ЕЩЁ НЕ ВНЕСЁН' - остаётся кнопка 'ВНЕСЁН'")
    print("-"*50)
    print("❌ Ctrl+C для остановки")
    print("="*50)
    
    app.run_polling()

if __name__ == "__main__":
    main()
