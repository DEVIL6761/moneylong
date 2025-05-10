import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd


class FinanceApp:
    def __init__(self, db_name='finance.db'):
        self.db_name = db_name

    def _get_connection(self):
        return sqlite3.connect(self.db_name)

    def get_transactions(self):
        conn = sqlite3.connect(self.db_name)
        df = pd.read_sql('SELECT * FROM transactions', conn)
        conn.close()
        return df

    def add_transaction(self, amount, category_name, trans_type, date=None, description=None):
        """Добавляет новую транзакцию"""
        conn = self._get_connection()
        try:
            # Получаем ID категории по имени
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
            category_id = cursor.fetchone()

            if not category_id:
                raise ValueError(f"Категория '{category_name}' не найдена")

            # Если дата не указана, используем текущую
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(date, datetime):
                date = date.strftime('%Y-%m-%d %H:%M:%S')

            # Вставляем транзакцию
            cursor.execute('''
                INSERT INTO transactions (amount, category_id, date, description, type)
                VALUES (?, ?, ?, ?, ?)
            ''', (amount, category_id[0], date, description, trans_type))

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_transactions(self, period='all', trans_type=None):
        """Возвращает список операций"""
        conn = self._get_connection()

        query = '''
        SELECT t.amount, c.name, 
               date(t.date) as date,  -- Берем только дату
               t.description, t.type 
        FROM transactions t 
        JOIN categories c ON t.category_id = c.id
        '''

        params = []
        conditions = []

        if trans_type:
            conditions.append('t.type = ?')
            params.append(trans_type)

        if period != 'all':
            if period == 'day':
                conditions.append("date(t.date) = date('now')")
            elif period == 'week':
                conditions.append("date(t.date) >= date('now', '-7 days')")
            elif period == 'month':
                conditions.append("strftime('%Y-%m', t.date) = strftime('%Y-%m', 'now')")

        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

        query += ' ORDER BY t.date DESC'

        df = pd.read_sql(query, conn, params=params if params else None)
        conn.close()
        return df

    def get_categories(self, trans_type=None):
        """Возвращает список категорий"""
        conn = self._get_connection()

        if trans_type:
            query = 'SELECT name FROM categories WHERE type = ?'
            categories = pd.read_sql(query, conn, params=(trans_type,))
        else:
            query = 'SELECT name, type FROM categories'
            categories = pd.read_sql(query, conn)

        conn.close()
        return categories

    def add_category(self, name, trans_type):
        """Добавляет новую категорию"""
        conn = self._get_connection()
        try:
            conn.execute('INSERT INTO categories (name, type) VALUES (?, ?)',
                         (name, trans_type))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

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

    def show_plot(self, period='month', trans_type='expense'):
        """Отображает кольцевую диаграмму с суммой в центре"""
        transactions = self.get_transactions(period=period, trans_type=trans_type)

        if transactions.empty:
            print("Нет данных для отображения")
            return

        plt.figure(figsize=(8, 8))

        # Подготовка данных
        by_category = transactions.groupby('name')['amount'].sum()
        total = by_category.sum()

        # Создание кольцевой диаграммы
        wedges, texts, autotexts = plt.pie(
            by_category,
            labels=by_category.index,
            autopct='%1.1f%%',
            startangle=90,
            wedgeprops={'width': 0.4, 'edgecolor': 'w'},  # Делаем кольцо
            pctdistance=0.85
        )

        # Добавляем общую сумму в центр
        centre_circle = plt.Circle((0, 0), 0.3, color='white')
        plt.gca().add_artist(centre_circle)
        plt.text(0, 0.1, f"Всего:\n{total:.2f} ₽",
                 ha='center', va='center', fontsize=12)

        plt.title(f"{'Доходы' if trans_type == 'income' else 'Расходы'} ({period})")
        plt.show()

    def get_expense_stats(self):
        """Возвращает статистику по расходам"""
        conn = self._get_connection()
        query = '''
        SELECT c.name, SUM(t.amount) as total 
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.type = 'expense'
        GROUP BY c.name
        ORDER BY total DESC
        '''
        df = pd.read_sql(query, conn)
        conn.close()
        return df.to_dict('records')

    def get_income_stats(self):
        """Возвращает статистику по доходам"""
        conn = self._get_connection()
        query = '''
        SELECT c.name, SUM(t.amount) as total 
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.type = 'income'
        GROUP BY c.name
        ORDER BY total DESC
        '''
        df = pd.read_sql(query, conn)
        conn.close()
        return df.to_dict('records')


# Пример использования
if __name__ == '__main__':
    app = FinanceApp()


