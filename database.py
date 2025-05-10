import sqlite3


def init_db():
    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()

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
        FOREIGN KEY (category_id) REFERENCES categories (id)
    )
    ''')

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

    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()