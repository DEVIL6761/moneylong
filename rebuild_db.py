import sqlite3
import os


def rebuild_database():
    # Удаляем старую базу данных, если она существует
    if os.path.exists('finance.db'):
        os.remove('finance.db')

    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()

    # Создаем таблицу accounts
    cursor.execute('''
    CREATE TABLE accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        balance REAL NOT NULL DEFAULT 0,
        currency TEXT DEFAULT 'BYN',
        description TEXT
    )
    ''')

    # Создаем таблицу categories
    cursor.execute('''
    CREATE TABLE categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        type TEXT NOT NULL CHECK(type IN ('expense', 'income'))
    )
    ''')

    # Создаем таблицу transactions с правильными связями
    cursor.execute('''
    CREATE TABLE transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL,
        category_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        description TEXT,
        type TEXT NOT NULL CHECK(type IN ('expense', 'income')),
        account_id INTEGER NOT NULL,
        FOREIGN KEY (category_id) REFERENCES categories (id),
        FOREIGN KEY (account_id) REFERENCES accounts (id)
    )
    ''')

    # Добавляем дефолтные данные
    default_categories = [
        ('Еда', 'expense'),
        ('Транспорт', 'expense'),
        ('Зарплата', 'income')
    ]

    for name, type in default_categories:
        try:
            cursor.execute('INSERT INTO categories (name, type) VALUES (?, ?)', (name, type))
        except sqlite3.IntegrityError:
            pass

    # Добавляем основной счет
    try:
        cursor.execute('INSERT INTO accounts (name, balance) VALUES (?, ?)', ('Основной счет', 0))
    except sqlite3.IntegrityError:
        pass

    conn.commit()
    conn.close()
    print("База данных успешно пересоздана с новой структурой")


if __name__ == '__main__':
    rebuild_database()