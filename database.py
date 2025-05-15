import sqlite3
import os


def init_db():
    conn = sqlite3.connect('finance.db', timeout=20)
    cursor = conn.cursor()

    # Оптимальные настройки для многопользовательского доступа
    cursor.execute("PRAGMA journal_mode=WAL")  # Режим Write-Ahead Logging
    cursor.execute("PRAGMA synchronous=NORMAL")  # Баланс между безопасностью и производительностью
    cursor.execute("PRAGMA busy_timeout=30000")  # Увеличиваем таймаут до 30 секунд

    # Создаем таблицы с явным указанием внешних ключей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        balance REAL NOT NULL DEFAULT 0,
        currency TEXT DEFAULT 'BYN',
        description TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        type TEXT NOT NULL CHECK(type IN ('expense', 'income'))
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL,
        category_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        description TEXT,
        type TEXT NOT NULL CHECK(type IN ('expense', 'income')),
        account_id INTEGER NOT NULL,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL
    )
    ''')

    # Добавляем начальные данные
    default_data(conn)

    conn.commit()
    conn.close()


def default_data(conn):
    cursor = conn.cursor()
    # Дефолтные категории
    categories = [
        ('Еда', 'expense'),
        ('Транспорт', 'expense'),
        ('Зарплата', 'income')
    ]

    for name, type in categories:
        try:
            cursor.execute('INSERT OR IGNORE INTO categories (name, type) VALUES (?, ?)', (name, type))
        except sqlite3.IntegrityError:
            pass

    # Дефолтный счет
    try:
        cursor.execute('INSERT OR IGNORE INTO accounts (name, balance) VALUES (?, ?)', ('Основной счет', 0))
    except sqlite3.IntegrityError:
        pass


def rebuild_database():
    if os.path.exists('finance.db'):
        os.remove('finance.db')
    init_db()
    print("База данных успешно пересоздана")


if __name__ == '__main__':
    rebuild_database()