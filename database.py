import sqlite3
from datetime import datetime


def init_db():
    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()

    # Таблица категорий расходов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    ''')

    # Таблица расходов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL,
        category_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        description TEXT,
        FOREIGN KEY (category_id) REFERENCES categories (id)
    )
    ''')

    # Стандартные категории
    default_categories = ['Еда', 'Транспорт', 'Жилье', 'Развлечения', 'Здоровье']
    for category in default_categories:
        try:
            cursor.execute('INSERT INTO categories (name) VALUES (?)', (category,))
        except sqlite3.IntegrityError:
            pass  # категория уже существует

    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()