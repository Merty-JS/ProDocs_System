import telebot
from telebot import types
import sqlite3
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = telebot.TeleBot('8468296516:AAEYsvMdr_qFOGKIS_qu5J4JB_rzC-Pmgrs')

# Конфигурация
CONFIG = {
    'PAYMENT_GROUP_ID': -4877778456, # тест бота
    'ADMIN_ID': 5121921650, # я
    'DB_NAME': 'balances.db',
    'PAYMENT_DETAILS': {
        'phone': '+7 XXX XXX XX XX',
        'bank': 'XXX-банк',
        'account': 'XXXX XXXX XXXX XXXX',
        'recipient': 'Иванов И.И.'},
    'SERVICES': {
            'Товар 1': {
                'description': 'Описание товара 1\nЦена: 1000 руб.',
                'price': 1000,
                'btn_pay': '💳 Оплатить Товар 1'
            },
            'Товар 2': {
                'description': 'Описание товара 2\nЦена: 2000 руб.',
                'price': 2000,
                'btn_pay': '💳 Оплатить Товар 2'
            },
            'Товар 3': {
                'description': 'Описание товара 3\nЦена: 3000 руб.',
                'price': 3000,
                'btn_pay': '💳 Оплатить Товар 3'
            }
    }
}

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect(CONFIG['DB_NAME'], check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  username TEXT,
                  first_name TEXT,
                  last_name TEXT,
                  balance REAL DEFAULT 0,
                  registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS payments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  amount REAL,
                  status TEXT DEFAULT 'pending',
                  screenshot_id TEXT,
                  date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(user_id) REFERENCES users(user_id))''')

    conn.commit()
    return conn, cursor
conn, cursor = init_db()

# Класс для управления состояниями пользователей
class UserState:
    def __init__(self):
        self.states = {}

    def set_state(self, user_id, state, data=None):
        self.states[user_id] = {'state': state, 'data': data or {}}

    def get_state(self, user_id):
        return self.states.get(user_id)

    def clear_state(self, user_id):
        if user_id in self.states:
            del self.states[user_id]
user_state = UserState()


# Утилиты
def create_user_if_not_exists(user):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
                   (user.id, user.username, user.first_name, user.last_name))
    conn.commit()
def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0.0


# Клавиатуры
def main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Услуги"),
               types.KeyboardButton("Пополнить баланс"),
               types.KeyboardButton("О боте"),
               types.KeyboardButton("Мой баланс"))
    return markup
def services_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Товар 1"),
               types.KeyboardButton("Товар 2"),
               types.KeyboardButton("Товар 3"),
               types.KeyboardButton("Назад"))
    return markup
def back_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Назад"))
    return markup
def admin_actions_keyboard(payment_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{payment_id}"),
               types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{payment_id}"))
    return markup


# Обработчики команд
@bot.message_handler(commands=['start'])
def start(message):
    create_user_if_not_exists(message.from_user)
    bot.send_message(message.chat.id, "Привет! Выберите, что вас интересует:", reply_markup=main_menu_keyboard())


@bot.message_handler(func=lambda m: m.text == "О боте")
def about_bot(message):
    bot.send_message(message.chat.id, "Ваш персональный помощник в автозаполнении "
                                      "документов ориентированный на плательщиков НПД(самозанятых)",
                     reply_markup=back_keyboard())


@bot.message_handler(func=lambda m: m.text == "Назад")
def handle_back(message):
    user_state.clear_state(message.from_user.id)
    bot.send_message(message.chat.id, "Ты в главном меню, выбери куда пойдешь дальше", reply_markup=main_menu_keyboard())


@bot.message_handler(func=lambda m: m.text == "Мой баланс")
def show_balance(message):
    balance = get_balance(message.from_user.id)
    bot.send_message(message.chat.id, f"Ваш текущий баланс: {balance} руб.", reply_markup=main_menu_keyboard())


# обработчик кнопки "Услуги"
@bot.message_handler(func=lambda m: m.text == "Услуги")
def show_services(message):
    bot.send_message(message.chat.id,"Выберите товар из списка:",reply_markup=services_menu_keyboard())

@bot.message_handler(func=lambda m: m.text == "Пополнить баланс")
def handle_top_up_balance(message):

    payment_text = (
        "Оплатите любым удобным способом:\n\n"
        f"1. Переводом по номеру \n{CONFIG['PAYMENT_DETAILS']['phone']} \n{CONFIG['PAYMENT_DETAILS']['bank']} \n{CONFIG['PAYMENT_DETAILS']['recipient']}\n\n"
        f"2. Переводом на счет \n{CONFIG['PAYMENT_DETAILS']['account']} \n{CONFIG['PAYMENT_DETAILS']['bank']} \n{CONFIG['PAYMENT_DETAILS']['recipient']}\n\n"
        "После перевода пришлите скрин, где четко видно:\n"
        "- Ваше имя\n- Сумму перевода\n- Дату перевода\n\n"
        "И укажите сумму пополнения в сообщении со скриншотом"
    )

    bot.send_message(message.chat.id, payment_text, reply_markup=back_keyboard())
    bot.send_message(message.chat.id,"Пожалуйста, введите сумму пополнения:")

    user_state.set_state(message.from_user.id, "waiting_amount")

# Добавляем обработчики для каждого товара

# Обновляем обработчик выбора товара
@bot.message_handler(func=lambda m: m.text in CONFIG['SERVICES'])
def handle_service_selection(message):
    service_name = message.text
    service = CONFIG['SERVICES'][service_name]

    response = (f"🛒 {service_name}\n\n"
                f"{service['description']}\n\n"
                f"Для покупки нажмите кнопку ниже:")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(
        types.KeyboardButton(service['btn_pay']),  # Кнопка оплаты
        types.KeyboardButton("⬅️ Назад к услугам"),
        types.KeyboardButton("🏠 Главное меню")
    )

    bot.send_message(message.chat.id, response, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "⬅️ Назад к услугам")
def back_to_services(message):
    user_state.clear_state(message.from_user.id)
    show_services(message)

@bot.message_handler(func=lambda m: m.text == "🏠 Главное меню")
def back_to_main_menu(message):
    user_state.clear_state(message.from_user.id)
    bot.send_message(message.chat.id, "Ты в главном меню, выбери куда пойдешь дальше", reply_markup=main_menu_keyboard())

# Обработчики для кнопок оплаты
@bot.message_handler(func=lambda m: any(
    m.text == service['btn_pay'] for service in CONFIG['SERVICES'].values()
))
def handle_payment_button(message):
    # Находим какой товар оплачивается
    for service_name, service in CONFIG['SERVICES'].items():
        if message.text == service['btn_pay']:
            process_payment(message, service_name)
            break


# Общая функция обработки платежа
def process_payment(message, product_name):
    product = CONFIG['SERVICES'][product_name]
    balance = get_balance(message.from_user.id)

    if balance >= product['price']:
        # Списание средств
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?",
                       (product['price'], message.from_user.id))
        conn.commit()

        bot.send_message(message.chat.id,
                         f"✅ Документ '{product_name}' будет готов в течение 24 часов\n"
                         f"💰 Списано: {product['price']} руб.\n"
                         f"💳 Остаток: {balance - product['price']} руб.")
    else:
        bot.send_message(message.chat.id,
                         f"❌ Недостаточно средств!\n"
                         f"💸 Ваш баланс: {balance} руб.\n"
                         f"📌 Нужно ещё: {product['price'] - balance} руб.\n\n"
                         f"Пополните баланс и попробуйте снова")

    # Предлагаем вернуться в меню
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🛒 Ещё услуги"), types.KeyboardButton("🏠 Главное меню"))


@bot.message_handler(func=lambda m: user_state.get_state(m.from_user.id) and
                                    user_state.get_state(m.from_user.id)['state'] == 'waiting_amount')
def handle_amount(message):
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError

        user_state.set_state(message.from_user.id, 'waiting_screenshot', {'amount': amount})
        bot.send_message(message.chat.id, f"Ожидаю скриншот оплаты на сумму {amount} руб.",
                         reply_markup=back_keyboard())

    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректную сумму числами (например: 1000)")
        user_state.clear_state(message.from_user.id)


@bot.message_handler(content_types=['photo'],
                     func=lambda m: user_state.get_state(m.from_user.id) and
                                    user_state.get_state(m.from_user.id)['state'] == 'waiting_screenshot')
def handle_payment_screenshot(message):
    try:
        state_data = user_state.get_state(message.from_user.id)['data']
        amount = state_data['amount']
        file_id = message.photo[-1].file_id

        # Сохраняем платеж
        cursor.execute("INSERT INTO payments (user_id, amount, screenshot_id) VALUES (?, ?, ?)",
                       (message.from_user.id, amount, file_id))
        conn.commit()
        payment_id = cursor.lastrowid

        # Формируем сообщение для админа
        user = message.from_user
        caption = (
            f"Новый платеж #{payment_id}\n"
            f"Пользователь: @{user.username or 'нет'}\n"
            f"Имя: {user.first_name or ''} {user.last_name or ''}\n"
            f"ID: {user.id}\n"
            f"Сумма: {amount} руб."
        )

        # Отправляем админу
        bot.send_photo(
            CONFIG['PAYMENT_GROUP_ID'],
            file_id,
            caption=caption,
            reply_markup=admin_actions_keyboard(payment_id)
        )

        # Уведомляем пользователя
        bot.reply_to(message, "Спасибо! Ваш платеж принят в обработку. Ожидайте подтверждения.")

        # Сбрасываем состояние
        user_state.clear_state(message.from_user.id)

    except Exception as e:
        logger.error(f"Ошибка обработки платежа: {e}")
        bot.reply_to(message, "Произошла ошибка при обработке платежа. Попробуйте позже.")
    finally:
        bot.send_message(message.chat.id, "Главное меню:", reply_markup=main_menu_keyboard())


@bot.callback_query_handler(func=lambda call: True)
def handle_admin_callback(call):
    if call.from_user.id != CONFIG['ADMIN_ID']:
        bot.answer_callback_query(call.id, "Только для администраторов!")
        return

    action, payment_id = call.data.split('_')
    payment_id = int(payment_id)

    # Получаем данные о платеже
    cursor.execute("SELECT user_id, amount FROM payments WHERE id=?", (payment_id,))
    payment = cursor.fetchone()

    if not payment:
        bot.answer_callback_query(call.id, "Платеж не найден!")
        return

    user_id, amount = payment

    if action == 'approve':
        try:
            # Обновляем баланс
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
            cursor.execute("UPDATE payments SET status='approved' WHERE id=?", (payment_id,))
            conn.commit()

            # Уведомляем пользователя
            bot.send_message(user_id,
                             f"✅ Ваш баланс пополнен на {amount} руб. Текущий баланс: {get_balance(user_id)} руб.")

            # Обновляем сообщение у админа
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=f"✅ Подтвержден платеж #{payment_id}\nПользователь: {user_id}\nСумма: {amount} руб.",
                reply_markup=None
            )

            bot.answer_callback_query(call.id, "Платеж подтвержден!")

        except Exception as e:
            logger.error(f"Ошибка подтверждения платежа: {e}")
            bot.answer_callback_query(call.id, "Ошибка подтверждения платежа!")

    elif action == 'reject':
        try:
            cursor.execute("UPDATE payments SET status='rejected' WHERE id=?", (payment_id,))
            conn.commit()

            bot.send_message(user_id, f"❌ Платеж на {amount} руб. отклонен. Свяжитесь с администратором.")

            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=f"❌ Отклонен платеж #{payment_id}\nПользователь: {user_id}\nСумма: {amount} руб.",
                reply_markup=None
            )

            bot.answer_callback_query(call.id, "Платеж отклонен!")

        except Exception as e:
            logger.error(f"Ошибка отклонения платежа: {e}")
            bot.answer_callback_query(call.id, "Ошибка отклонения платежа!")


if __name__ == '__main__':
    logger.info("Бот запущен")
    bot.polling(none_stop=True)