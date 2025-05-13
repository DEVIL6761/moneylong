import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

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
        conn = self._get_connection()
        query = '''
        SELECT t.id, t.amount, c.name, 
               date(t.date) as date,
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

    def update_transaction(self, transaction_id, amount, category_name, trans_type, date=None, description=None):
        """Обновляет существующую транзакцию"""
        conn = self._get_connection()
        try:
            # Получаем ID категории
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
            category_id = cursor.fetchone()

            if not category_id:
                raise ValueError(f"Категория '{category_name}' не найдена")

            # Форматируем дату
            date_str = date.strftime('%Y-%m-%d %H:%M:%S') if date else None

            # Обновляем транзакцию
            cursor.execute('''
                UPDATE transactions 
                SET amount = ?, category_id = ?, type = ?, date = ?, description = ?
                WHERE id = ?
            ''', (amount, category_id[0], trans_type, date_str, description, transaction_id))

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_daily_stats(self, month=None):
        df = self.get_transactions()

        # Преобразуем в datetime
        df['date'] = pd.to_datetime(df['date'])

        # Фильтруем по месяцу, если передан
        if month:
            df = df[df['date'].dt.strftime('%Y-%m') == month]
        else:
            month = datetime.now().strftime('%Y-%m')
            df = df[df['date'].dt.strftime('%Y-%m') == month]

        # Добавим день месяца как число
        df['day'] = df['date'].dt.day

        # Группируем по дню и типу транзакции
        grouped = df.groupby(['day', 'type'])['amount'].sum().unstack(fill_value=0).reset_index()

        # Получаем все дни в месяце
        days_in_month = pd.date_range(start=f'{month}-01', end=pd.to_datetime(f'{month}-01') + pd.offsets.MonthEnd(0))
        full_days = pd.DataFrame({'day': days_in_month.day})

        # Объединяем с группировкой и заполняем пропуски
        merged = pd.merge(full_days, grouped, on='day', how='left').fillna(0)

        # Убедимся, что нужные колонки есть
        if 'income' not in merged.columns:
            merged['income'] = 0
        if 'expense' not in merged.columns:
            merged['expense'] = 0

        # Формат в список словарей
        result = merged[['day', 'income', 'expense']].to_dict(orient='records')
        return result

        days_in_month = pd.date_range(start=f"{month}-01", periods=31, freq='D')
        days_in_month = days_in_month[days_in_month.month == int(month[-2:])]

        full_days = pd.DataFrame({'day': days_in_month.day})
        grouped = df.groupby(['day', 'type'])['amount'].sum().unstack().fillna(0)
        grouped = full_days.merge(grouped, on='day', how='left').fillna(0)

        # Построение
        fig, ax = plt.subplots(figsize=(12, 5))  # Растянутая ширина

        ax.bar(grouped['day'], grouped.get('доход', 0), label='Доходы', color='green')
        ax.bar(grouped['day'], -grouped.get('расход', 0), label='Расходы', color='red')

        ax.set_xticks(grouped['day'])  # Показываем все числа месяца
        ax.set_xticklabels(grouped['day'].astype(int))  # Только число
        ax.tick_params(axis='x', rotation=0)  # Перпендикулярноget
        ax.legend()
        ax.set_title(f'Доходы и расходы за {month}')
        ax.set_xlabel('День')
        ax.set_ylabel('Сумма')

        # Преобразование в base64
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()

        return image_base64


# Пример использования
if __name__ == '__main__':
    app = FinanceApp()


