import sqlite3

def create_tasks_db():
    conn = sqlite3.connect('tasks_settings.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        enabled INTEGER NOT NULL
                      )''')
    conn.commit()
    conn.close()

def initialize_tasks():
    conn = sqlite3.connect('tasks_settings.db')
    cursor = conn.cursor()
    tasks = ['send_random_quote', 'send_random_minds', 'send_random_shorts', 'send_birthday', 'send_random_rss']
    for task in tasks:
        cursor.execute("INSERT OR IGNORE INTO tasks (name, enabled) VALUES (?, ?)", (task, 1))
    conn.commit()
    conn.close()

create_tasks_db()
initialize_tasks()
