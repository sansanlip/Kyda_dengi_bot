import telebot
import json
import time
import threading
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup

TOKEN = "7655454535:AAEmhdfP1shVkHHyVervaPwdTZFX9HjvQjc"
bot = telebot.TeleBot(TOKEN)

DATA_FILE = 'data.json'

# Хранилища
data = {
    "expenses": {},
    "reminders": {},
    "last_reminder_time": {},
    "goals": {}
}

# Загрузка данных из файла
def load_data():
    global data
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            # Преобразуем даты из строки в datetime
            for chat_id in data["expenses"]:
                data["expenses"][chat_id] = [
                    (datetime.fromisoformat(e[0]), e[1], e[2]) for e in data["expenses"][chat_id]
                ]
    except Exception:
        pass

# Сохранение данных в файл
def save_data():
    to_save = {
        "expenses": {},
        "reminders": data["reminders"],
        "last_reminder_time": data["last_reminder_time"],
        "goals": data["goals"]
    }
    for chat_id in data["expenses"]:
        to_save["expenses"][chat_id] = [
            (e[0].isoformat(), e[1], e[2]) for e in data["expenses"][chat_id]
        ]
    with open(DATA_FILE, 'w') as f:
        json.dump(to_save, f, indent=2)

# Клавиатуры
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("💰 Внести расход", "📊 Просмотр расходов")
    keyboard.add("🎯 Цель накопления", "⏰ Напоминания")
    return keyboard

def get_expense_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🍎 Продукты", "🚕 Транспорт", "💊 Здоровье")
    keyboard.add("🛍 Личное", "🎉 Отдых", "🏠 Дом", "📚 Обучение", "📦 Подписки")
    keyboard.add("⬅️ Назад")
    return keyboard

def get_reminder_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🔔 Каждые 3 часа", "🕒 Указать время")
    keyboard.add("🚫 Отключить напоминания", "⬅️ Назад")
    return keyboard

def get_view_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📅 Сегодня", "📆 Неделя", "📅 Месяц")
    keyboard.add("🗑 Удалить последний", "⬅️ Назад")
    return keyboard

# Команда /start
@bot.message_handler(commands=['start'])
def welcome(message):
    bot.send_message(message.chat.id, "Привет! Я бот для учёта расходов 💰", reply_markup=get_main_keyboard())

# Главное меню
@bot.message_handler(func=lambda m: m.text in ["💰 Внести расход", "📊 Просмотр расходов", "🎯 Цель накопления", "⏰ Напоминания"])
def main_menu(message):
    if message.text == "💰 Внести расход":
        bot.send_message(message.chat.id, "Выбери категорию:", reply_markup=get_expense_keyboard())
    elif message.text == "📊 Просмотр расходов":
        bot.send_message(message.chat.id, "Выбери период:", reply_markup=get_view_keyboard())
    elif message.text == "🎯 Цель накопления":
        bot.send_message(message.chat.id, "Введи сумму накопления:")
        bot.register_next_step_handler(message, save_goal)
    elif message.text == "⏰ Напоминания":
        bot.send_message(message.chat.id, "Настройка напоминаний:", reply_markup=get_reminder_keyboard())

# Цель накопления
def save_goal(message):
    try:
        goal = float(message.text)
        data["goals"][str(message.chat.id)] = goal
        save_data()
        bot.send_message(message.chat.id, f"Цель накопления: {goal} ₽", reply_markup=get_main_keyboard())
    except ValueError:
        bot.send_message(message.chat.id, "Введите число")

# Внесение расходов
@bot.message_handler(func=lambda m: m.text in ["🍎 Продукты", "🚕 Транспорт", "💊 Здоровье", "🛍 Личное", "🎉 Отдых", "🏠 Дом", "📚 Обучение", "📦 Подписки"])
def ask_expense(message):
    category = message.text
    bot.send_message(message.chat.id, f"Сколько потратил на {category}?")
    bot.register_next_step_handler(message, lambda m: save_expense(m, category))

def save_expense(message, category):
    try:
        amount = float(message.text)
        chat_id = str(message.chat.id)
        if chat_id not in data["expenses"]:
            data["expenses"][chat_id] = []
        data["expenses"][chat_id].append((datetime.now(), category, amount))
        save_data()
        bot.send_message(message.chat.id, f"Записано: {amount} ₽ на {category}", reply_markup=get_main_keyboard())
    except ValueError:
        bot.send_message(message.chat.id, "Введите сумму цифрами.")

# Просмотр расходов
@bot.message_handler(func=lambda m: m.text in ["📅 Сегодня", "📆 Неделя", "📅 Месяц"])
def view_expenses(message):
    chat_id = str(message.chat.id)
    now = datetime.now()
    expenses = data["expenses"].get(chat_id, [])

    if message.text == "📅 Сегодня":
        start = now.replace(hour=0, minute=0, second=0)
    elif message.text == "📆 Неделя":
        start = now - timedelta(days=7)
    else:
        start = now - timedelta(days=30)

    filtered = [e for e in expenses if e[0] >= start]
    total = sum(e[2] for e in filtered)
    lines = [f"{e[0].strftime('%d.%m %H:%M')} — {e[1]}: {e[2]} ₽" for e in filtered]
    goal = data["goals"].get(chat_id)
    msg = "\n".join(lines) + f"\n\n💰 Всего: {total} ₽"
    if goal:
        msg += f"\n🎯 Осталось до цели: {max(0, goal - total)} ₽"
    bot.send_message(message.chat.id, msg, reply_markup=get_main_keyboard())

# Удалить последний расход
@bot.message_handler(func=lambda m: m.text == "🗑 Удалить последний")
def delete_last(message):
    chat_id = str(message.chat.id)
    if chat_id in data["expenses"] and data["expenses"][chat_id]:
        deleted = data["expenses"][chat_id].pop()
        save_data()
        bot.send_message(message.chat.id, f"Удалено: {deleted[1]} - {deleted[2]} ₽")
    else:
        bot.send_message(message.chat.id, "Нет расходов для удаления.")

# Напоминания
@bot.message_handler(func=lambda m: m.text == "🔔 Каждые 3 часа")
def set_reminder(message):
    chat_id = str(message.chat.id)
    data["reminders"][chat_id] = 3
    data["last_reminder_time"][chat_id] = datetime.now().isoformat()
    save_data()
    bot.send_message(message.chat.id, "Буду напоминать каждые 3 часа 💬", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda m: m.text == "🚫 Отключить напоминания")
def disable_reminder(message):
    chat_id = str(message.chat.id)
    data["reminders"].pop(chat_id, None)
    data["last_reminder_time"].pop(chat_id, None)
    save_data()
    bot.send_message(message.chat.id, "Напоминания отключены", reply_markup=get_main_keyboard())

# Фоновая проверка напоминаний
def reminder_thread():
    while True:
        now = datetime.now()
        for chat_id, hours in data["reminders"].items():
            last_time_str = data["last_reminder_time"].get(chat_id)
            if not last_time_str:
                continue
            last_time = datetime.fromisoformat(last_time_str)
            if now - last_time >= timedelta(hours=hours):
                bot.send_message(chat_id, "⏰ Напомни себе внести расходы!")
                data["last_reminder_time"][chat_id] = now.isoformat()
                save_data()
        time.sleep(60)

# Запуск
load_data()
threading.Thread(target=reminder_thread, daemon=True).start()
bot.polling(none_stop=True)