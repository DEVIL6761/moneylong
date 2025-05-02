import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd


class FinanceApp:
    def __init__(self, db_name='finance.db'):
        self.db_name = db_name

    def _get_connection(self):
        return sqlite3.connect(self.db_name)

    def add_expense(self, amount, category_name, description=None):
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = self._get_connection()
        cursor = conn.cursor()

        # Получаем или создаем категорию
        cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
        category = cursor.fetchone()

        if not category:
            cursor.execute('INSERT INTO categories (name) VALUES (?)', (category_name,))
            category_id = cursor.lastrowid
        else:
            category_id = category[0]

        # Добавляем расход
        cursor.execute('''
        INSERT INTO expenses (amount, category_id, date, description)
        VALUES (?, ?, ?, ?)
        ''', (amount, category_id, date, description))

        conn.commit()
        conn.close()
        return True

    def get_expenses(self, period='month'):
        conn = self._get_connection()

        # Определяем период для фильтрации
        now = datetime.now()
        if period == 'day':
            date_filter = now.strftime('%Y-%m-%d')
            query = "SELECT e.amount, c.name, e.date, e.description FROM expenses e JOIN categories c ON e.category_id = c.id WHERE date(e.date) = date(?) ORDER BY e.date DESC"
        elif period == 'week':
            query = "SELECT e.amount, c.name, e.date, e.description FROM expenses e JOIN categories c ON e.category_id = c.id WHERE date(e.date) >= date('now', '-7 days') ORDER BY e.date DESC"
        elif period == 'month':
            query = "SELECT e.amount, c.name, e.date, e.description FROM expenses e JOIN categories c ON e.category_id = c.id WHERE strftime('%Y-%m', e.date) = strftime('%Y-%m', 'now') ORDER BY e.date DESC"
        else:  # all
            query = "SELECT e.amount, c.name, e.date, e.description FROM expenses e JOIN categories c ON e.category_id = c.id ORDER BY e.date DESC"

        df = pd.read_sql(query, conn, params=(date_filter,) if period == 'day' else None)
        conn.close()
        return df

    def get_statistics(self, period='month'):
        expenses = self.get_expenses(period)
        if expenses.empty:
            return None

        stats = {
            'total': expenses['amount'].sum(),
            'by_category': expenses.groupby('name')['amount'].sum().to_dict(),
            'average_per_day': expenses.groupby(expenses['date'].str[:10])['amount'].sum().mean()
        }
        return stats

    def show_plot(self, period='month'):
        expenses = self.get_expenses(period)
        if expenses.empty:
            print("Нет данных для отображения")
            return

        # График по категориям
        by_category = expenses.groupby('name')['amount'].sum()
        by_category.plot.pie(title=f'Расходы по категориям ({period})', autopct='%1.1f%%')
        plt.show()

        # График по дням
        expenses['day'] = expenses['date'].str[:10]
        by_day = expenses.groupby('day')['amount'].sum()
        by_day.plot.bar(title=f'Расходы по дням ({period})')
        plt.show()


# Пример использования
if __name__ == '__main__':
    app = FinanceApp()

    # Добавление тестовых данных
    app.add_expense(1500, 'Еда', 'Продукты на неделю')
    app.add_expense(300, 'Транспорт', 'Такси')
    app.add_expense(2500, 'Жилье', 'Аренда')

    # Получение статистики
    print("Статистика за месяц:")
    stats = app.get_statistics('month')
    print(stats)

    # Визуализация
    app.show_plot('month')