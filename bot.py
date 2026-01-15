import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = "8010829617:AAFY8zqUCg40iSMqgH2cmO7fB3yd-OjcWyw"
ADMIN_COMMAND = "/gOEv36HaWm"
ADMIN_PASSWORD = "LwvRBB01Qq"

# Состояния для ConversationHandler
WAITING_FOR_PASSWORD, ADMIN_MODE, WAITING_FOR_USER_ID, WAITING_FOR_MESSAGE = range(4)

# Хранилище данных (в реальном боте лучше использовать базу данных)
user_messages = {}
admin_sessions = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    await update.message.reply_text(
        "Здравствуйте! Здесь вы можете общаться со мной! "
        "Этот бот сделан для моей анонимности! Можешь написать мне своё сообщение ниже!"
    )
    
    # Сохраняем информацию о пользователе
    user_id = user.id
    username = user.username or f"user_{user_id}"
    user_messages[user_id] = {
        'username': username,
        'messages': []
    }

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик сообщений от пользователей"""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Сохраняем сообщение пользователя
    if user_id not in user_messages:
        user_messages[user_id] = {
            'username': update.effective_user.username or f"user_{user_id}",
            'messages': []
        }
    
    user_messages[user_id]['messages'].append({
        'text': message_text,
        'timestamp': update.message.date
    })
    
    await update.message.reply_text("✅ Ваше сообщение получено и сохранено!")

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало админ-сессии"""
    user_id = update.effective_user.id
    
    if user_id in admin_sessions:
        await update.message.reply_text(
            "Вы уже в админ-режиме. Используйте команды:\n"
            "/list - список пользователей\n"
            "/send <user_id> - ответить пользователю\n"
            "/exit - выход из админ-режима"
        )
        return ADMIN_MODE
    
    await update.message.reply_text("🔐 Введите пароль для доступа к админ-панели:")
    return WAITING_FOR_PASSWORD

async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка пароля админа"""
    password = update.message.text
    
    if password == ADMIN_PASSWORD:
        user_id = update.effective_user.id
        admin_sessions.add(user_id)
        await update.message.reply_text(
            "✅ Пароль верный! Вы вошли в админ-панель.\n\n"
            "Доступные команды:\n"
            "/list - показать список пользователей и их сообщений\n"
            "/send - ответить пользователю\n"
            "/exit - выйти из админ-режима"
        )
        return ADMIN_MODE
    else:
        await update.message.reply_text("❌ Неверный пароль! Попробуйте снова или отмените команду /cancel")
        return WAITING_FOR_PASSWORD

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список пользователей и их сообщений"""
    if not user_messages:
        await update.message.reply_text("📭 Сообщений от пользователей пока нет.")
        return ADMIN_MODE
    
    response = "📋 Список пользователей и их сообщений:\n\n"
    
    for user_id, data in user_messages.items():
        username = data['username']
        messages = data['messages']
        
        response += f"👤 Пользователь: {username} (ID: {user_id})\n"
        
        if messages:
            for i, msg in enumerate(messages[-5:], 1):  # Показываем последние 5 сообщений
                response += f"  {i}. {msg['text'][:50]}...\n"
        else:
            response += "  Сообщений нет\n"
        
        response += "\n" + "─"*40 + "\n\n"
    
    await update.message.reply_text(response[:4000])  # Ограничение Telegram на длину сообщения
    return ADMIN_MODE

async def send_message_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать процесс отправки сообщения пользователю"""
    await update.message.reply_text("Введите ID пользователя, которому хотите отправить сообщение:")
    return WAITING_FOR_USER_ID

async def get_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить ID пользователя для ответа"""
    try:
        user_id = int(update.message.text)
        context.user_data['target_user_id'] = user_id
        
        if user_id not in user_messages:
            await update.message.reply_text(f"❌ Пользователь с ID {user_id} не найден. Попробуйте снова:")
            return WAITING_FOR_USER_ID
        
        username = user_messages[user_id]['username']
        await update.message.reply_text(
            f"Выбран пользователь: {username} (ID: {user_id})\n\n"
            "Введите сообщение для отправки:"
        )
        return WAITING_FOR_MESSAGE
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID. Введите числовой ID пользователя:")
        return WAITING_FOR_USER_ID

async def send_message_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить сообщение пользователю"""
    target_user_id = context.user_data.get('target_user_id')
    message_text = update.message.text
    
    if not target_user_id:
        await update.message.reply_text("❌ Ошибка: не указан пользователь. Начните заново с /send")
        return ADMIN_MODE
    
    try:
        # Отправляем сообщение пользователю
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"📨 Ответ от администратора:\n\n{message_text}"
        )
        
        # Сохраняем в истории
        if 'admin_replies' not in user_messages[target_user_id]:
            user_messages[target_user_id]['admin_replies'] = []
        
        user_messages[target_user_id]['admin_replies'].append({
            'text': message_text,
            'timestamp': update.message.date
        })
        
        username = user_messages[target_user_id]['username']
        await update.message.reply_text(f"✅ Сообщение отправлено пользователю {username} (ID: {target_user_id})")
        
        # Очищаем временные данные
        context.user_data.pop('target_user_id', None)
        
        return ADMIN_MODE
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        await update.message.reply_text(f"❌ Ошибка отправки сообщения: {e}")
        return ADMIN_MODE

async def admin_exit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выход из админ-режима"""
    user_id = update.effective_user.id
    if user_id in admin_sessions:
        admin_sessions.remove(user_id)
    
    await update.message.reply_text("👋 Вы вышли из админ-режима.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущей операции"""
    user_id = update.effective_user.id
    if user_id in admin_sessions:
        admin_sessions.remove(user_id)
    
    await update.message.reply_text("❌ Операция отменена.")
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка при обработке обновления: {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Произошла ошибка. Пожалуйста, попробуйте снова или обратитесь к разработчику."
        )

def main():
    """Основная функция запуска бота"""
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Создаем ConversationHandler для админ-панели
    admin_conv_handler = ConversationHandler(
        entry_points=[CommandHandler(ADMIN_COMMAND.strip('/'), admin_start)],
        states={
            WAITING_FOR_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_password)],
            ADMIN_MODE: [
                CommandHandler("list", list_users),
                CommandHandler("send", send_message_start),
                CommandHandler("exit", admin_exit),
                CommandHandler("cancel", cancel),
            ],
            WAITING_FOR_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_user_id)],
            WAITING_FOR_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_message_to_user)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("exit", admin_exit),
        ],
    )
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(admin_conv_handler)
    
    # Обработчик обычных сообщений (должен быть после всех CommandHandler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))
    
    # Регистрируем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    print("🤖 Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
