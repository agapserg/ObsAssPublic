import os
import sqlite3
from datetime import datetime as dt
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import logging
from datetime import timedelta
import matplotlib.colors as mcolors
import numpy as np
import calendar
import re
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from pathlib import Path
import pandas as pd
from pathlib import Path
import numpy as np
import calendar
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from collections import Counter
import pandas as pd
from aiogram.types import ParseMode
from aiogram.types import Message, ContentType
import random
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os
import re
import random
import sqlite3
from contextlib import closing
from yt_dlp import YoutubeDL
import asyncio
import glob

from config import TOKEN, ROOT_PATH, READ_LATER_PATH, BOOK_PATH, WAKE_UP_PATH, SLEEP_PATH, VIDEO_PATH, PHOTO_PATH

# Глобальные переменные
global last_photo_time, last_photo_index
last_photo_time = None
last_photo_index = 0

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())
BASE_PATH = ROOT_PATH
directory = BOOK_PATH

async def send_birthday(user_id, days):
    directory = ROOT_PATH
    birthday_pattern = r'- \[ \] 🟩🎂 (.+) ⏫ 🔁 every year ➕ \d{4}-\d{2}-\d{2} 📅 (\d{4}-\d{2}-\d{2})'
    upcoming_birthdays = []
    today = dt.now().date()

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    content = f.read()
                    found_birthdays = re.findall(birthday_pattern, content)
                    for name, date in found_birthdays:
                        birthday_date = dt.strptime(date, '%Y-%m-%d').date()
                        if 0 <= (birthday_date - today).days < days:
                            upcoming_birthdays.append((name, date, birthday_date))

    # Сортировка по дате рождения
    upcoming_birthdays.sort(key=lambda x: x[2])

    if upcoming_birthdays:
        birthday_message = f"В ближайшие {days} дней будут дни рождения у вот этих людей:\n"
        birthday_message += "\n".join([f"▶️ {date} - {name}" for name, date, _ in upcoming_birthdays])
        birthday_message += "\n\nНе забудь написать им поздравления заранее или купить подарки"
    else:
        birthday_message = "В ближайшие дни дней рождений нет."

    await bot.send_message(user_id, birthday_message)

async def send_random_shorts(user_id):
    directory = ROOT_PATH
    db_path = "shorts.db"  # Новое название файла БД

    with closing(sqlite3.connect(db_path)) as connection:
        with closing(connection.cursor()) as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shorts (
                    id INTEGER PRIMARY KEY,
                    file TEXT NOT NULL,
                    short TEXT NOT NULL,
                    send_count INTEGER DEFAULT 0,
                    UNIQUE(file, short)
                )
            ''')
            connection.commit()

            # Измененный шаблон для поиска YouTube Shorts URL
            shorts_pattern = r'https?://(?:www\.)?youtube\.com/shorts/[^\s?]+'

            shorts = []

            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith(".md"):
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            content = f.read()
                            found_shorts = re.findall(shorts_pattern, content)
                            for short in found_shorts:
                                shorts.append((file, short))

            cursor.execute('SELECT file, short FROM shorts')
            sent_shorts = cursor.fetchall()
            unsent_shorts = [s for s in shorts if s not in sent_shorts]

            if not unsent_shorts:
                cursor.execute('DELETE FROM shorts')
                connection.commit()
                unsent_shorts = shorts.copy()

            selected_file, selected_short = random.choice(unsent_shorts)
            short_index = shorts.index((selected_file, selected_short)) + 1
            total_shorts = len(shorts)
            message = f"{short_index}/{total_shorts} - {selected_file}\n\n{selected_short}"

            cursor.execute('''
                INSERT INTO shorts (file, short, send_count)
                VALUES (?, ?, 1)
                ON CONFLICT(file, short)
                DO UPDATE SET send_count = send_count + 1
            ''', (selected_file, selected_short))
            connection.commit()

    await bot.send_message(user_id, message)

async def send_random_rss(user_id):
    file_path = READ_LATER_PATH
    db_path = "RSS.db"  # Новое название файла БД

    # Создаем или открываем БД и таблицу
    with closing(sqlite3.connect(db_path)) as connection:
        with closing(connection.cursor()) as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY,
                    file TEXT NOT NULL,
                    quote TEXT NOT NULL,
                    send_count INTEGER DEFAULT 0,
                    UNIQUE(file, quote)
                )
            ''')
            connection.commit()

            # Читаем файл и ищем цитаты
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            quotes = re.findall(r'- \[ \] (.+)', content)

            # Проверяем, какие цитаты уже были отправлены
            cursor.execute('SELECT quote FROM quotes WHERE file = ?', (file_path,))
            sent_quotes = [row[0] for row in cursor.fetchall()]
            unsent_quotes = [q for q in quotes if q not in sent_quotes]

            # Если все цитаты были отправлены, очищаем таблицу
            if not unsent_quotes:
                cursor.execute('DELETE FROM quotes WHERE file = ?', (file_path,))
                connection.commit()
                unsent_quotes = quotes.copy()

            # Выбираем случайную цитату
            selected_quote = random.choice(unsent_quotes)
            quote_index = quotes.index(selected_quote) + 1
            total_quotes = len(quotes)
            message = f"{quote_index}/{total_quotes} - {file_path}\n\n{selected_quote}"

            # Обновляем БД
            cursor.execute('''
                INSERT INTO quotes (file, quote, send_count)
                VALUES (?, ?, 1)
                ON CONFLICT(file, quote)
                DO UPDATE SET send_count = send_count + 1
            ''', (file_path, selected_quote))
            connection.commit()

            # Обновляем файл, заменяя "- [ ]" на "- [x]"
            updated_content = re.sub(r'- \[ \] ' + re.escape(selected_quote), '- [x] ' + selected_quote, content, 1)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

    await bot.send_message(user_id, message)

async def send_random_minds(user_id):
    directory = ROOT_PATH
    db_path = "Minds.db"  # Обновленное название файла БД

    # Создаем или открываем БД и таблицу
    with closing(sqlite3.connect(db_path)) as connection:
        with closing(connection.cursor()) as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY,
                    file TEXT NOT NULL,
                    quote TEXT NOT NULL,
                    send_count INTEGER DEFAULT 0,
                    UNIQUE(file, quote)
                )
            ''')
            connection.commit()

            # Обновленный шаблон поиска
            prefix_pattern = r'- \[x\] #мысли 🟩 (.+)'
            quotes = []
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith(".md"):
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            content = f.read()
                            found_quotes = re.findall(prefix_pattern, content)
                            for quote in found_quotes:
                                quotes.append((file, quote))

            # Проверяем, какие цитаты уже были отправлены
            cursor.execute('SELECT file, quote FROM quotes')
            sent_quotes = cursor.fetchall()
            unsent_quotes = [q for q in quotes if q not in sent_quotes]

            # Если все цитаты были отправлены, очищаем таблицу
            if not unsent_quotes:
                cursor.execute('DELETE FROM quotes')
                connection.commit()
                unsent_quotes = quotes.copy()

            # Выбираем случайную цитату
            selected_file, selected_quote = random.choice(unsent_quotes)
            quote_index = quotes.index((selected_file, selected_quote)) + 1
            total_quotes = len(quotes)
            message = f"{quote_index}/{total_quotes} - {selected_file}\n\n{selected_quote}"

            # Обновляем БД
            cursor.execute('''
                INSERT INTO quotes (file, quote, send_count)
                VALUES (?, ?, 1)
                ON CONFLICT(file, quote)
                DO UPDATE SET send_count = send_count + 1
            ''', (selected_file, selected_quote))
            connection.commit()

    await bot.send_message(user_id, message)

async def send_random_quote(user_id):
    directory = BOOK_PATH
    db_path = "quotes_database.db"  # Путь к файлу БД

    # Создаем или открываем БД и таблицу
    with closing(sqlite3.connect(db_path)) as connection:
        with closing(connection.cursor()) as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY,
                    file TEXT NOT NULL,
                    quote TEXT NOT NULL,
                    send_count INTEGER DEFAULT 0,
                    UNIQUE(file, quote)
                )
            ''')
            connection.commit()

            # Получаем список цитат
            prefix_patterns = [
                r'- \[[ ]\] 🟩 (.+)',
                r'- \[[x]\] 🟩 (.+)',
            ]
            quotes = []
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith(".md"):
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            content = f.read()
                            for pattern in prefix_patterns:
                                found_quotes = re.findall(pattern, content)
                                for quote in found_quotes:
                                    quote = re.sub(r'TG - \[razbivator\]\(https://t.me/razbivator_bot\) ', '', quote)
                                    quote = re.sub(r'TG - \[ReadStreakBot\]\(https://t.me/ReadStreakBot\) ', '', quote)
                                    quotes.append((file, quote))

            # Проверяем, какие цитаты уже были отправлены
            cursor.execute('SELECT file, quote FROM quotes')
            sent_quotes = cursor.fetchall()
            unsent_quotes = [q for q in quotes if q not in sent_quotes]

            # Если все цитаты были отправлены, очищаем таблицу
            if not unsent_quotes:
                cursor.execute('DELETE FROM quotes')
                connection.commit()
                unsent_quotes = quotes.copy()

            # Выбираем случайную цитату
            selected_file, selected_quote = random.choice(unsent_quotes)
            quote_index = quotes.index((selected_file, selected_quote)) + 1
            total_quotes = len(quotes)
            message = f"{quote_index}/{total_quotes} - {selected_file}\n\n{selected_quote}"

            # Обновляем БД
            cursor.execute('''
                INSERT INTO quotes (file, quote, send_count)
                VALUES (?, ?, 1)
                ON CONFLICT(file, quote)
                DO UPDATE SET send_count = send_count + 1
            ''', (selected_file, selected_quote))
            connection.commit()

    await bot.send_message(user_id, message)

# Хендлер для команды /quote
@dp.message_handler(commands=['quote'])
async def quote_handler(message: types.Message):
    user_id = message.from_user.id
    await send_random_quote(user_id)

@dp.message_handler(commands=['minds'])
async def quote_handler(message: types.Message):
    user_id = message.from_user.id
    await send_random_minds(user_id)

@dp.message_handler(commands=['rss'])
async def quote_handler(message: types.Message):
    user_id = message.from_user.id
    await send_random_rss(user_id)

@dp.message_handler(commands=['bd7'])
async def quote_handler(message: types.Message):
    user_id = message.from_user.id
    await send_birthday(user_id, 7)

@dp.message_handler(commands=['bd30'])
async def quote_handler(message: types.Message):
    user_id = message.from_user.id
    await send_birthday(user_id, 30)

@dp.message_handler(commands=['shorts'])
async def quote_handler(message: types.Message):
    user_id = message.from_user.id
    await send_random_shorts(user_id)

@dp.message_handler(commands=['todayscore'])
async def todayscore_handler(message: types.Message):
    # Define directory
    directory = ROOT_PATH
    current_date = dt.now().strftime('%Y-%m-%d')
    
    # Get the scores
    total_score, role_task_points = count_tasks_points_for_today(directory, current_date)
    
    # Prepare a list of tuples containing scores and roles
    scores_roles = []
    for role, scores in role_task_points.items():
        role_score = sum(scores.values())
        if role_score > 0:
            scores_roles.append((role_score, role))

    # Sort roles by score in descending order
    sorted_scores_roles = sorted(scores_roles, key=lambda x: x[0], reverse=True)
    
    # Prepare the response
    response = f"Сегодня за день набрано: {total_score} очков\n\n"
    
    for score, role in sorted_scores_roles:
        response += f"{score:02} = {role}\n"

    await message.answer(response, parse_mode=ParseMode.MARKDOWN)

def count_tasks_points_for_today(directory, date):
    scores = {'🟩': 1, '🟨': 5, '🟥': 10}
    role_task_counter = {}
    total_score = 0
    
    # Iterate over files in the directory and subdirectories
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.md'):
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    content = f.read()
                # Extract the role name
                match = re.search(r'Role2:: #(\w+)', content)
                if match:
                    role = match.group(1)
                else:
                    continue  # Skip file if no role is found
                
                if role not in role_task_counter:
                    role_task_counter[role] = Counter()
                
                # Find all completed tasks for today
                completed_tasks = re.findall(r'- \[x\].*✅ ' + date, content)
                for task in completed_tasks:
                    # Check each type of task in each completed task
                    for task_type, score in scores.items():
                        if task_type in task:
                            total_score += score
                            role_task_counter[role][task_type] += score

    return total_score, role_task_counter

async def todayscore_handler(message: types.Message):
    # Define directory
    directory = ROOT_PATH
    current_date = dt.now().strftime('%Y-%m-%d')
    
    # Get the scores
    total_score, role_task_points = count_tasks_points_for_today(directory, current_date)
    
    # Prepare the response
    response = f"Сегодня за день набрано: {total_score} очков\n\n"
    for role, scores in role_task_points.items():
        response += f"{role}: {sum(scores.values())} очков\n"

    await message.answer(response)

def get_wu7_data(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()
    data = {}
    for line in lines:
        match = re.search(r"✅ (\d{4}-\d{2}-\d{2})", line)
        if match:
            date = match.group(1)
            if "вставатьв7" in line:
                color_code = 0  # Вы можете изменить код цвета, если хотите использовать другой
            else:
                continue
            data[date] = color_code
    return data

@dp.message_handler(Command('wu7'))
async def send_sww_chart(message: types.Message):
    file_path = Path(WAKE_UP_PATH)
    if not file_path.exists():
        await message.answer("Файл не найден!")
        return
    # Получение текущей даты
    today = dt.now()
    # Получение данных и создание графика
    sww_data = get_wu7_data(file_path)
    img_path = visualize_sleep_calendar(sww_data, today.year, today.month, chart_title="Трекер просыпания в 7", file_name="wu7_chart.png")
    # Отправка графика пользователю
    with open(img_path, "rb") as file:
        await bot.send_photo(chat_id=message.from_user.id, photo=file)

def get_sleep_data(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()
    data = {}
    for line in lines:
        match = re.search(r"✅ (\d{4}-\d{2}-\d{2})", line)
        if match:
            date = match.group(1)
            if "Лёг спать до 22:00" in line:
                color_code = 0
            elif "Лёг спать до 23:00" in line:
                color_code = 1
            elif "Лёг спать до 00:00" in line:
                color_code = 2
            else:
                continue
            data[date] = color_code
    return data

colormap = ListedColormap(['white', 'red', 'yellow', 'green'])

def visualize_sleep_calendar(data, year, month, chart_title="Трекер сна", file_name="sleep_chart.png"):
    colors = {
        -1: "Lavender", # Нет данных
        0: "SpringGreen",    # До 22:00
        1: "Gold", # До 23:00
        2: "DarkOrange"   # До 00:00
    }
    # Создаем пустой календарь
    month_calendar = np.zeros((5, 7), dtype=int) - 1
    first_weekday, days_in_month = calendar.monthrange(year, month)
    for day in range(1, days_in_month + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        if date_str in data:
            week = (day + first_weekday - 1) // 7
            weekday = (day + first_weekday - 1) % 7
            month_calendar[week, weekday] = data[date_str]
    fig, ax = plt.subplots(figsize=(10, 6))
    cax = ax.matshow(month_calendar, cmap=ListedColormap([colors[val] for val in [-1, 0, 1, 2]]), vmin=-1, vmax=2)
    ax.set_xticks(np.arange(7))
    ax.set_yticks(np.arange(5))
    ax.set_xticklabels(calendar.day_abbr)
    ax.set_yticklabels(range(1, 6))
    for i in range(5):
        for j in range(7):
            day_num = i*7 + j - first_weekday + 1
            if 0 < day_num <= days_in_month:
                ax.text(j, i, str(day_num), va='center', ha='center', color='black', fontsize=16)
    plt.title(f"{chart_title} - {calendar.month_name[month]} {year}")
    plt.savefig(file_name) # Сохраняем изображение
    plt.close() # Закрываем рисунок
    return file_name

@dp.message_handler(Command('sleep'))
async def send_sleep_chart(message: types.Message):
    file_path = Path(SLEEP_PATH)
    if not file_path.exists():
        await message.answer("Файл не найден!")
        return
    # Получение текущей даты
    today = dt.now()
    # Получение данных и создание графика
    sleep_data = get_sleep_data(file_path)
    img_path = visualize_sleep_calendar(sleep_data, today.year, today.month, chart_title="Трекер сна")
    # Отправка графика пользователю
    with open(img_path, "rb") as file:
        await bot.send_photo(chat_id=message.from_user.id, photo=file)

# Добавление нового состояния для удаления строки по id
class DelForm(StatesGroup):
    row_id = State()

# Обработчик команды /del
@dp.message_handler(Command('del'))
async def delete_trigger(message: types.Message):
    await DelForm.row_id.set()
    await message.answer("Напишите номер строки связки, которую надо удалить.")

# Обработчик для ввода id после команды /del
@dp.message_handler(state=DelForm.row_id)
async def process_delete(message: types.Message, state: FSMContext):
    row_id = message.text
    if not row_id.isdigit():
        await message.answer("Пожалуйста, введите корректный номер строки.")
        return

    conn = sqlite3.connect('trigger_words.db')
    cursor = conn.cursor()
    
    # Проверка наличия строки с данным id в базе данных
    cursor.execute("SELECT * FROM triggers WHERE id=?", (row_id,))
    row = cursor.fetchone()

    if row:
        # Если строка найдена, сохраняем ее содержимое
        row_data = str(row)

        # Удаляем строку
        cursor.execute("DELETE FROM triggers WHERE id=?", (row_id,))
        conn.commit()

        # Отправляем сообщение с данными удаленной строки
        await message.answer(f"Строка с номером {row_id} успешно удалена! Это была строка со следующими данными: \"{row_data}\"")
    else:
        await message.answer(f"Строка с номером {row_id} не найдена в базе данных.")
    
    await state.finish()  # Завершение работы с состоянием


# Создание стейтов (состояний) для нашего бота
class Form(StatesGroup):
    trigger_word = State()  # Введение триггерного слова
    inbox_path = State()  # Выбор пути до файла
    filename = State()  # Введение имени файла

@dp.message_handler(Command('add'))
async def add_trigger_word(message: types.Message):
    await Form.trigger_word.set()
    await message.answer("Пожалуйста, укажите триггерное слово.")

def get_unique_paths_from_db():
    conn = sqlite3.connect('trigger_words.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT inbox_path FROM triggers")
    paths = [row[0] for row in cursor.fetchall()]
    return paths

@dp.message_handler(state=Form.trigger_word)
async def process_trigger_word(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['trigger_word'] = message.text.lower()

    unique_paths = "123"
    
    if unique_paths:
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        
        # Получаем только конечные части путей для отображения на кнопках
        display_paths = [path.replace(BASE_PATH, '') for path in unique_paths]
        # Сортируем конечные части путей
        display_paths = sorted(display_paths)

        for display_path in display_paths:
            markup.add(KeyboardButton(text=display_path))
        
        await message.answer("Выберите путь до файла или напишите новый.", reply_markup=markup)
        await Form.inbox_path.set()  # Переход к состоянию ожидания пути
    else:
        await message.answer("В базе данных нет сохраненных путей. Напишите путь.")
        await Form.inbox_path.set()  # Переход к состоянию ожидания пути


# Не забывайте проверить ввод пользователя на следующем этапе:
@dp.message_handler(state=Form.inbox_path)
async def process_inbox_path(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        # Если введенный путь не полный, добавляем базовый путь к началу
        if BASE_PATH not in message.text:
            full_path = BASE_PATH + message.text
        else:
            full_path = message.text
        data['inbox_path'] = full_path

    await message.answer("Укажите название файла")
    await Form.filename.set()  # Переход к состоянию ожидания имени файла

@dp.message_handler(state=Form.filename)
async def process_filename(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        trigger_word = data['trigger_word']
        inbox_path = data['inbox_path']
        filename = message.text
    
    # Сохранение данных в базу данных
    conn = sqlite3.connect('trigger_words.db')
    cursor = conn.cursor()

    # Проверка существования таблицы triggers и её создание, если она не найдена
    cursor.execute("""CREATE TABLE IF NOT EXISTS triggers (
                        id INTEGER PRIMARY KEY,
                        trigger_word TEXT NOT NULL,
                        inbox_path TEXT NOT NULL,
                        filename TEXT NOT NULL
                      )""")
    
    cursor.execute("INSERT INTO triggers (trigger_word, inbox_path, filename) VALUES (?, ?, ?)",
                   (trigger_word, inbox_path, filename))
    conn.commit()
    conn.close()

    await state.finish()
    await message.answer(f"Новая связка добавлена: {trigger_word}, {inbox_path}, {filename}")

@dp.message_handler(Command('help'))
async def send_triggers(message: types.Message):
    # Соединение с базой данных и выбор данных
    conn = sqlite3.connect('trigger_words.db')
    cursor = conn.cursor()
    # Измененный запрос для выбора id, trigger_word и filename
    cursor.execute("SELECT id, trigger_word, filename FROM triggers")
    triggers = cursor.fetchall()
    # Измененное форматирование данных для вывода, чтобы включить id
    triggers_str_list = [f"{id}. {trigger} = {filename}" for id, trigger, filename in triggers]
    triggers_str = "\n".join(triggers_str_list)

    # Дополнительный текст с описанием новых триггеров
    additional_text = (
        "ггг - это готово, выполненная задача сегодняшней датой\n"
        "ссс - проставляет дату сегодня\n"
        "ххх и ХХХ - хай приоритет, проставляет высокий приоритет\n"
        "ззз - завтра\n"
        "ппзз - послезавтра\n"
        "ввчч - вчера\n"
        "сспп - следующий понедельник\n"
        "222 - жёлтая задача\n"
        "333 - красная задача\n"
        "ммм - добавляет тег мысль в задачу\n"
        "купить - добавляет эмодзю 💰\n"
        "аптека - добавляет эмодзю 💊\n"
        "ачивка - добавляет эмодзю 🏆\n"
        "линкс - добавляет эмодзю 🔗\n"
        "ппп - помощник - добавляет эмодзю 👩‍💼\n"
        "др - добавляет эмодзю 🎂\n"
    )

    # Объединение и отправка данных пользователю
    full_message = additional_text + "\n\nHere are the available triggers:\n" + triggers_str
    if triggers_str:
        await message.answer(full_message)
    else:
        await message.answer("No triggers found in the database.")


async def add_note(message: types.Message, filename, is_trigger_word=True):
    note_content = message.text
    if is_trigger_word:
        note_content = " ".join(message.text.split()[1:])
    
    note_content_words = note_content.split()
    if note_content_words:
        first_word = note_content_words[0]
        # Проверяем, является ли первое слово URL-ссылкой
        if not re.match(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', first_word):
            note_content_words[0] = first_word.lower()

        note_content = ' '.join(note_content_words)

        if note_content:
            curr_date = dt.now().strftime('%Y-%m-%d')
            
            # Проверка наличия "ззз" и "ппзз"
            
            
            # Проверка наличия "готово" и модификация note_text
            if "ггг" in note_content:
                note_text = f'\n- [x] 🟩 {note_content} ➕ {curr_date} 📅 {curr_date} ✅ {curr_date}'
            else:
                note_text = f'\n- [ ] 🟩 {note_content} ➕ {curr_date} '
            
            if "ммм" in note_content:
                note_text = note_text.replace("🟩", "#мысль 🟩")
                note_content = note_content.replace("ммм", "")
            # Добавление эмодзи в начало по ключевым словам
            emoji_dict = {
                "купить": "💰",
                "аптека": "💊",
                "ачивка": "🏆",
                "линкс": "🔗",
                "ппп": "👩‍💼",
                " др ": "🎂"
            }
            for word, emoji in emoji_dict.items():
                if word in note_content:
                    note_text = note_text.replace("🟩", f"🟩{emoji}")
            
            # Проверка наличия "линкс"
            if "линкс" in note_content:
                note_text = note_text.replace("🟩", "🟩🔗")
            
            # Остальные проверки, которые уже были в функции
            if "ссс" in note_content and "готово" not in note_content:
                note_text += f'📅 {curr_date} '
            
            if "ззз" in note_content:
                curr_date = (dt.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                note_content = note_content.replace("ззз", "")
                note_text += f'📅 {curr_date} '

            if "сспп" in note_content:
                # Найти ближайший понедельник
                today = dt.now()
                next_monday = today + timedelta(days=(7 - today.weekday()))
                curr_date = next_monday.strftime('%Y-%m-%d')
                note_content = note_content.replace("сспп", "")
                note_text += f'📅 {curr_date} '            

            if "ппзз" in note_content:
                curr_date = (dt.now() + timedelta(days=2)).strftime('%Y-%m-%d')
                note_content = note_content.replace("ппзз", "")
                note_text += f'📅 {curr_date} '
            
            if "ввчч" in note_content:
                curr_date = (dt.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                note_content = note_content.replace("ввчч", "")
                note_text += f'📅 {curr_date} '

            if "ххх" in note_content:
                note_text = note_text.replace('➕', f'⏫ ➕')

            if "ХХХ" in note_content:
                note_text = note_text.replace('➕', f'⏫ ➕')
            
            if "222" in note_content:
                note_text = note_text.replace('🟩', '🟨')
            elif "333" in note_content:
                note_text = note_text.replace('🟩', '🟥')
            
            # Убираем ключевые слова из note_text
            search_pattern = os.path.join(ROOT_PATH, '**', f"{filename}.md")
            files_found = [file for file in glob.glob(search_pattern, recursive=True) if os.path.basename(file) == f"{filename}.md"]
            
            if files_found:
                DIRNAME = files_found[0]  # Используем первый найденный файл, соответствующий критериям
                with open(DIRNAME, 'a', encoding='UTF-8') as f:
                    f.write(note_text)
                await message.answer("Заметка добавлена!")
            else:
                await message.answer("Файл не найден. Пожалуйста, проверьте название файла!")


def clean_filename(filename):
    # Удаление недопустимых символов в именах файлов и эмодзи
    filename = re.sub(r'[\\/*?:"<>|]', '', filename)  # Удаление символов, недопустимых в Windows
    filename = re.sub(r'[#]', '', filename)  # Удаление хэштегов
    # Удаление всех точек из строки
    filename = filename.replace('.', '')
    filename = filename.replace('(', '')
    filename = filename.replace(')', '')
    # Удаление эмодзи и других специальных символов, оставляя только буквы, цифры и пробелы
    filename = re.sub(r'[^\w\s\-_,()]', '', filename)
    # Замена двойных, тройных и любых последовательностей пробелов на одинарные
    filename = re.sub(r'\s+', ' ', filename)
    return filename

async def download_youtube_video(url, path_to_save):
    def _download():
        ydl_opts = {
            'format': 'best',
            'outtmpl': path_to_save,
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',  # Укажите ваш предпочтительный формат здесь
            }],
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    await asyncio.get_event_loop().run_in_executor(None, _download)

async def get_video_title(url):
    with YoutubeDL() as ydl:
        info_dict = ydl.extract_info(url, download=False)
        video_title = info_dict.get("title", None)
    return clean_filename(video_title)

async def save_shorts(message: types.Message, file_name_suffix, bot):
    urls = re.findall(r'(https?://(?:www\.)?youtube\.com/shorts/[^\s?]+)', message.text)
    if not urls:
        urls = re.findall(r'(https?://youtube\.com/shorts/[^\s?]+)', message.text)
        if not urls:
            return None  # Возвращаем None, если URL не найден
    video_url = urls[0]  # Берём первый найденный URL
    video_title = await get_video_title(video_url)  # Получаем название видео
    video_path = VIDEO_PATH
    current_time = dt.now()
    # Формируем имя файла без расширения и очищаем его
    cleaned_filename = clean_filename(f"шортс - {current_time.strftime('%Y-%m-%d %H%M%S')} - {video_title}")
    # Ограничиваем длину имени файла до 100 символов, не считая расширение
    if len(cleaned_filename) > 100:  # Уменьшаем до 95, чтобы оставить место для расширения
        cleaned_filename = cleaned_filename[:100]
    # Добавляем расширение .mp4
    filename_with_extension = f"{cleaned_filename}.mp4"
    full_path = os.path.join(video_path, filename_with_extension)
    await download_youtube_video(video_url, full_path)  # Используем извлечённый URL
    return filename_with_extension

@dp.message_handler(content_types=['text', 'photo', 'document', 'voice'])
async def process_message(message: types.Message):
    # Условие, если в ОбсАсс репостишь с РидСтрик бота, то он предлагает выбрать книжку куда сохранить
    if message.forward_from and message.forward_from.is_bot:
        files = [f for f in os.listdir(directory) if f.endswith('.md') and '+' not in f]  # Исключаем файлы с "+" в названии
        markup = InlineKeyboardMarkup(row_width=2)
        for file in files:
            file_name_without_extension = file[:-3]  # Удаляем расширение ".md"
            # Если название начинается на "книга - ", удаляем эту часть
            if file_name_without_extension.startswith("книга - "):
                file_name_without_extension = file_name_without_extension.replace("книга - ", "", 1)
            short_name = shorten_name(file_name_without_extension)  # Используем имя файла без "книга - " и без расширения
            short_code = generate_short_code(file)  # Генерируем короткий код для callback_data
            button = InlineKeyboardButton(short_name, callback_data='save_to_file:' + short_code)
            markup.add(button)
        await message.reply("Выберите файл для сохранения:", reply_markup=markup)
    elif message.text and ("youtube.com/shorts/" in message.text or "youtu.be/" in message.text): # Логика обработки шортсов
        # Сохраняем шортс с ключевым словом "шортс"
        filename = await save_shorts(message, "шортс", bot)
        # Формируем текст, который будет отправлен в заметку, включая исходную ссылку и название файла
        current_time = dt.now().strftime("%Y-%m-%d")
        message_text_with_filename = f"[[{filename}]] - {message.text}?feature=share"
        # Создаём фейковое сообщение для последующей обработки
        message_timestamp = int(message.date.timestamp())
        fake_message = types.Message(message_id=message.message_id, chat=message.chat, date=message_timestamp, text=message_text_with_filename)
        await handle_non_trigger_message_shorts(fake_message)  # Изменено на прямой вызов функции для не-триггерных сообщений
    elif message.text:
        # Проверяем, начинается ли текст сообщения с триггера
        if message.text.split()[0].lower() in get_triggers():
            await handle_message(message)
        else:
            # Если текст не начинается с триггера, вызываем функцию для обработки не-триггерных сообщений
            await handle_non_trigger_message(message)
    
    elif message.photo: # Логика обработки фото
        if message.caption:  # Фото с описанием
            trigger_word = message.caption.split()[0].lower()
            file_name_suffix = trigger_word if trigger_word in get_triggers() else "инбокс"
            filename = await save_photo(message, file_name_suffix, bot)

            # Добавляем название файла к тексту описания
            message_with_filename = f"{message.caption} [[{filename}]]"
            
            if trigger_word in get_triggers():
                # Обновляем текст сообщения и отправляем в handle_message
                message.text = message_with_filename
                await handle_message(message)
            else:
                # Создаем фейковое сообщение для не-триггерных сообщений
                message_timestamp = int(message.date.timestamp())
                fake_message = Message(message_id=message.message_id, chat=message.chat, date=message_timestamp, text=message_with_filename)
                await handle_non_trigger_message(fake_message)
        else:  # Фото без описания
            filename = await save_photo(message, "инбокс", bot)
            # Создание фейкового сообщения с названием файла в квадратных скобках
            message_timestamp = int(message.date.timestamp())
            fake_message_text = f"[[{filename}]]"
            fake_message = Message(message_id=message.message_id, chat=message.chat, date=message_timestamp, text=fake_message_text)
            await handle_non_trigger_message(fake_message)

# Функция для сохранения фото
async def save_photo(message: types.Message, file_name_suffix, bot):
    global last_photo_time, last_photo_index
    photo_path = PHOTO_PATH
    current_time = dt.now()
    if last_photo_time and current_time.strftime("%Y-%m-%d %H-%M-%S") == last_photo_time.strftime("%Y-%m-%d %H-%M-%S"):
        last_photo_index += 1
    else:
        last_photo_index = 1
        last_photo_time = current_time
    filename = f"{current_time.strftime('%Y-%m-%d %H-%M-%S')} - {file_name_suffix} - {str(last_photo_index).zfill(2)}.jpg"
    photo_id = message.photo[-1].file_id
    file_path = await bot.get_file(photo_id)
    file = await bot.download_file(file_path.file_path)
    with open(os.path.join(photo_path, filename), 'wb') as photo_file:
        photo_file.write(file.getvalue())
    return filename


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('save_to_file:'))
async def handle_file_selection(callback_query: types.CallbackQuery):
    file_codes = {generate_short_code(f): f for f in os.listdir(directory) if f.endswith('.md')}
    short_code = callback_query.data.split(':')[1]
    file_name = file_codes.get(short_code)  # Получаем полное имя файла из словаря
    if not file_name:
        await bot.answer_callback_query(callback_query.id, "Ошибка: Файл не найден")
        return
    file_path = os.path.join(directory, file_name)
    message = callback_query.message  # Сообщение, на которое пользователь нажал кнопку
    if message.reply_to_message and message.reply_to_message.text:
        # Заменяем переносы строки на пробелы и удаляем лишние пробелы
        text = ' '.join(message.reply_to_message.text.replace('\r\n', '\n').split())
        
        # Форматируем текст с датами и специальными символами
        current_date = dt.now().strftime("%Y-%m-%d")
        formatted_text = f"\n- [x] 🟩 {text} ➕ {current_date} ✅ {current_date}\n"
        
        with open(file_path, 'a', encoding='utf-8') as file:  # Убедитесь, что используете кодировку UTF-8
            file.write(formatted_text)
        await bot.answer_callback_query(callback_query.id, f"Текст сохранен в {shorten_name(file_name)}")
    else:
        await bot.answer_callback_query(callback_query.id, "Ошибка: Нет текста для сохранения")

# Функция для сокращения названия файла
def shorten_name(name, max_length=40):
    if len(name) > max_length:
        return name[:max_length-3] + '...'
    return name

def generate_short_code(file_name, max_length=10):
    # Здесь можно реализовать более сложную логику для уникальности
    return file_name[:max_length]

@dp.message_handler(lambda message: message.text and message.text.split()[0].lower() in get_triggers())
async def handle_message(message: types.Message):
    conn = sqlite3.connect('trigger_words.db')
    cursor = conn.cursor()
    first_word = message.text.split()[0]
    if re.match(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', first_word):
        trigger_word = first_word
    else:
        trigger_word = first_word.lower()
    cursor.execute("SELECT trigger_word, filename FROM triggers WHERE trigger_word = ?", (trigger_word,))
    fetch_result = cursor.fetchone()
    if fetch_result is None:
        trigger_word = "инбокс"
        cursor.execute("SELECT trigger_word, filename FROM triggers WHERE trigger_word = ?", (trigger_word,))
        fetch_result = cursor.fetchone()
    _, filename = fetch_result
    await add_note(message, filename, True)


@dp.message_handler(lambda message: not message.text.split()[0].lower() in get_triggers())
async def handle_non_trigger_message(message: types.Message):
    # Так как ключевого слова нет, считаем, что оно "инбокс"
    trigger_word = "инбокс"
    conn = sqlite3.connect('trigger_words.db')
    cursor = conn.cursor()
    # Обновляем запрос к базе данных, чтобы извлечь только нужные поля
    cursor.execute("SELECT trigger_word, filename FROM triggers WHERE trigger_word = ?", (trigger_word,))
    _, filename = cursor.fetchone()
    conn.close()

    # Обновляем вызов функции add_note, убрав параметр inbox_path
    await add_note(message, filename, False)


@dp.message_handler(lambda message: not message.text.split()[0].lower() in get_triggers())
async def handle_non_trigger_message_shorts(message: types.Message):
    # Так как ключевого слова нет, считаем, что оно "шортс"
    trigger_word = "шортс"
    conn = sqlite3.connect('trigger_words.db')
    cursor = conn.cursor()
    # Обновляем запрос к базе данных, чтобы извлечь только нужные поля
    cursor.execute("SELECT trigger_word, filename FROM triggers WHERE trigger_word = ?", (trigger_word,))
    _, filename = cursor.fetchone()
    conn.close()

    # Обновляем вызов функции add_note, убрав параметр inbox_path
    await add_note(message, filename, False)


def get_triggers():
    # Получение всех триггерных слов из базы данных
    conn = sqlite3.connect('trigger_words.db')
    cursor = conn.cursor()

    cursor.execute("SELECT trigger_word FROM triggers")
    triggers = [row[0] for row in cursor.fetchall()]


    return triggers

@dp.errors_handler()
async def error_handler(update: types.Update, exception: Exception):
    logging.exception(f"Exception: {repr(exception)}")
    return True  # Предотвращает вызов следующего обработчика ошибок

@dp.message_handler(lambda message: True, state="*")
async def debug_state(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    logging.info(f"Current state: {current_state}")
    await message.answer(f"Current state: {current_state}")


if __name__ == "__main__":
    from aiogram import executor
    scheduler = AsyncIOScheduler()
    user_id_to_send = 5922128322
    days = 30
    scheduler.add_job(send_random_quote, 'cron', day='*', hour=4, minute=0, args=[user_id_to_send], misfire_grace_time=300)  # 300 секунд грации  # Например, каждый день в 00:01
    scheduler.add_job(send_random_minds, 'cron', day='*', hour=4, minute=2, args=[user_id_to_send], misfire_grace_time=300)
    scheduler.add_job(send_random_rss, 'cron', day='*', hour=4, minute=4, args=[user_id_to_send], misfire_grace_time=300)
    scheduler.add_job(send_random_shorts, 'cron', day='*', hour=4, minute=6, args=[user_id_to_send], misfire_grace_time=300)
    scheduler.add_job(send_birthday, 'cron', day_of_week='mon', hour=4, minute=8, args=[user_id_to_send, days], misfire_grace_time=300)
    scheduler.start()
    executor.start_polling(dp, skip_updates=True)
