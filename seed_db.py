import sqlite3
from datetime import datetime, timedelta
import random


def seed_database():
    # Подключение к базе данных
    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()

    try:
        # Очистка существующих данных (осторожно!)
        cursor.execute("DELETE FROM transactions")
        cursor.execute("DELETE FROM categories WHERE name NOT IN ('Еда', 'Транспорт', 'Зарплата')")
        conn.commit()

        # Дополнительные категории
        categories = [
            ('Продукты', 'expense'),
            ('Кафе', 'expense'),
            ('Такси', 'expense'),
            ('Комунальные', 'expense'),
            ('Развлечения', 'expense'),
            ('Премия', 'income'),
            ('Фриланс', 'income'),
            ('Инвестиции', 'income'),
            ('Подарок', 'income'),
            ('Возврат долга', 'income')
        ]

        # Добавление категорий
        for name, type in categories:
            try:
                cursor.execute("INSERT INTO categories (name, type) VALUES (?, ?)", (name, type))
            except sqlite3.IntegrityError:
                pass

        # Функция для генерации случайной даты
        def random_date(start_date, end_date):
            time_between = end_date - start_date
            random_days = random.randrange(time_between.days)
            return start_date + timedelta(days=random_days)

        # Генерация транзакций
        expense_categories = ['Еда', 'Транспорт', 'Продукты', 'Кафе', 'Такси', 'Комунальные', 'Развлечения']
        income_categories = ['Зарплата', 'Премия', 'Фриланс', 'Инвестиции', 'Подарок', 'Возврат долга']

        # 10 расходов
        for _ in range(10):
            category_name = random.choice(expense_categories)
            category_id = cursor.execute(
                "SELECT id FROM categories WHERE name = ?",
                (category_name,)
            ).fetchone()[0]

            cursor.execute('''
                INSERT INTO transactions (amount, category_id, date, description, type)
                VALUES (?, ?, ?, ?, 'expense')
            ''', (
                round(random.uniform(100, 5000), 2),
                category_id,
                random_date(datetime.now() - timedelta(days=60), datetime.now()).strftime('%Y-%m-%d %H:%M:%S'),
                random.choice(['Покупка', 'Оплата', 'Чек', 'Покупка в магазине', ''])
            ))

        # 10 доходов
        for _ in range(10):
            category_name = random.choice(income_categories)
            category_id = cursor.execute(
                "SELECT id FROM categories WHERE name = ?",
                (category_name,)
            ).fetchone()[0]

            cursor.execute('''
                INSERT INTO transactions (amount, category_id, date, description, type)
                VALUES (?, ?, ?, ?, 'income')
            ''', (
                round(random.uniform(5000, 50000), 2),
                category_id,
                random_date(datetime.now() - timedelta(days=60), datetime.now()).strftime('%Y-%m-%d %H:%M:%S'),
                random.choice(['Зарплата', 'Перевод', 'Оплата заказа', 'Доход', ''])
            ))

        # Сохранение изменений
        conn.commit()
        print("База данных успешно заполнена тестовыми данными!")

    except Exception as e:
        print(f"Ошибка при заполнении базы данных: {e}")
    finally:
        conn.close()


if __name__ == '__main__':
    seed_database()