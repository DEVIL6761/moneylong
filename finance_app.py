from contextlib import contextmanager

import matplotlib.pyplot as plt
import io
import base64
import sqlite3
from datetime import datetime, time
import pandas as pd


class FinanceApp:
    def __init__(self, db_name='finance.db'):
        self.db_name = db_name
        self.timeout = 30  # секунд


    def _get_connection(self):
        conn = sqlite3.connect(self.db_name, timeout=20)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _execute_with_retry(self, query, params=(), max_retries=3):
        for attempt in range(max_retries):
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("BEGIN IMMEDIATE")  # Явное начало транзакции
                    cursor.execute(query, params)
                    conn.commit()
                    return cursor
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))
                    continue
                raise

    def get_transactions(self):
        conn = sqlite3.connect(self.db_name)
        df = pd.read_sql('SELECT * FROM transactions', conn)
        conn.close()
        return df

    def add_transaction(self, amount, category_name, trans_type, date=None, description=None, account_id=None):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("BEGIN IMMEDIATE")

                # Получаем ID категории
                cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
                category_id = cursor.fetchone()
                if not category_id:
                    raise ValueError(f"Категория '{category_name}' не найдена")

                # Если счет не указан, используем первый доступный
                if not account_id:
                    cursor.execute('SELECT id FROM accounts LIMIT 1')
                    account_id = cursor.fetchone()[0]
                    if not account_id:
                        raise ValueError("Нет доступных счетов")

                # Вставляем транзакцию
                date_str = date.strftime('%Y-%m-%d %H:%M:%S') if date else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute('''
                    INSERT INTO transactions (amount, category_id, date, description, type, account_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (amount, category_id[0], date_str, description, trans_type, account_id))

                # Обновляем баланс счета
                if trans_type == 'income':
                    cursor.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (amount, account_id))
                else:
                    cursor.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (amount, account_id))

                conn.commit()
                return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_transactions(self, period='all', trans_type=None):
        conn = sqlite3.connect(self.db_name, timeout=20)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            cursor = conn.cursor()

            query = '''
            SELECT t.id, t.amount, c.name, 
                   date(t.date) as date,
                   t.description, t.type,
                   a.name as account_name,
                   a.id as account_id
            FROM transactions t 
            JOIN categories c ON t.category_id = c.id
            JOIN accounts a ON t.account_id = a.id
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

            # Выполняем запрос через курсор
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Получаем результаты и преобразуем в DataFrame
            columns = [column[0] for column in cursor.description]
            data = cursor.fetchall()

            return pd.DataFrame(data, columns=columns) if data else pd.DataFrame(columns=columns)

        finally:
            conn.close()

    def get_categories(self, trans_type=None):
        conn = sqlite3.connect(self.db_name)
        try:
            cursor = conn.cursor()

            if trans_type:
                cursor.execute('SELECT name, type FROM categories WHERE type = ?', (trans_type,))
            else:
                cursor.execute('SELECT name, type FROM categories')

            columns = [column[0] for column in cursor.description]
            data = cursor.fetchall()

            return pd.DataFrame(data, columns=columns) if data else pd.DataFrame(columns=columns)

        finally:
            conn.close()

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

    def get_expense_stats(self, month=None):
        """Возвращает статистику по расходам за указанный месяц"""
        conn = self._get_connection()

        query = '''
        SELECT c.name, SUM(t.amount) as total 
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.type = 'expense'
        '''

        params = []
        if month:
            query += " AND strftime('%Y-%m', t.date) = ?"
            params.append(month)

        query += '''
        GROUP BY c.name
        ORDER BY total DESC
        '''

        df = pd.read_sql(query, conn, params=params if params else None)
        conn.close()
        return df.to_dict('records')

    def get_income_stats(self, month=None):
        """Возвращает статистику по доходам за указанный месяц"""
        conn = self._get_connection()

        query = '''
        SELECT c.name, SUM(t.amount) as total 
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.type = 'income'
        '''

        params = []
        if month:
            query += " AND strftime('%Y-%m', t.date) = ?"
            params.append(month)

        query += '''
        GROUP BY c.name
        ORDER BY total DESC
        '''

        df = pd.read_sql(query, conn, params=params if params else None)
        conn.close()
        return df.to_dict('records')

    def update_transaction(self, transaction_id, amount, category_name, trans_type, date=None, description=None,
                           account_id=None):
        """Обновляет существующую транзакцию"""
        conn = self._get_connection()
        try:
            # Получаем старые данные транзакции
            cursor = conn.cursor()
            cursor.execute('SELECT amount, type, account_id FROM transactions WHERE id = ?', (transaction_id,))
            old_data = cursor.fetchone()

            if not old_data:
                raise ValueError("Транзакция не найдена")

            old_amount, old_type, old_account_id = old_data

            # Получаем ID категории
            cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
            category_id = cursor.fetchone()

            if not category_id:
                raise ValueError(f"Категория '{category_name}' не найдена")

            # Если счет не указан, оставляем старый
            if account_id is None:
                account_id = old_account_id

            # Проверяем существование счета
            if account_id:
                cursor.execute('SELECT id FROM accounts WHERE id = ?', (account_id,))
                if not cursor.fetchone():
                    raise ValueError("Указанный счет не существует")

            # Форматируем дату
            date_str = date.strftime('%Y-%m-%d %H:%M:%S') if date else None

            # Обновляем транзакцию
            cursor.execute('''
                UPDATE transactions 
                SET amount = ?, category_id = ?, type = ?, date = ?, description = ?, account_id = ?
                WHERE id = ?
            ''', (amount, category_id[0], trans_type, date_str, description, account_id, transaction_id))

            # Обновляем балансы счетов, если они изменились
            if old_account_id or account_id:
                # Отменяем старую операцию
                if old_account_id:
                    if old_type == 'income':
                        cursor.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?',
                                       (old_amount, old_account_id))
                    else:
                        cursor.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?',
                                       (old_amount, old_account_id))

                # Применяем новую операцию
                if account_id:
                    if trans_type == 'income':
                        cursor.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (amount, account_id))
                    else:
                        cursor.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (amount, account_id))

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

    def get_accounts(self):
        """Возвращает список всех счетов"""
        conn = self._get_connection()
        df = pd.read_sql('SELECT * FROM accounts', conn)
        conn.close()
        return df

    def add_account(self, name, initial_balance=0, currency='BYN', description=None):
        """Добавляет новый счет"""
        conn = self._get_connection()
        try:
            conn.execute('INSERT INTO accounts (name, balance, currency, description) VALUES (?, ?, ?, ?)',
                         (name, initial_balance, currency, description))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def update_account_balance(self, account_id, amount, operation='add'):
        """Обновляет баланс счета"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            if operation == 'add':
                cursor.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (amount, account_id))
            else:
                cursor.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (amount, account_id))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_total_balance(self):
        """Возвращает общий баланс по всем счетам"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT SUM(balance) FROM accounts')
        total = cursor.fetchone()[0] or 0
        conn.close()
        return total

    # Обновленный метод добавления транзакции
    def add_transaction(self, amount, category_name, trans_type, date=None, description=None, account_id=None):
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
                INSERT INTO transactions (amount, category_id, date, description, type, account_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (amount, category_id[0], date, description, trans_type, account_id))

            # Обновляем баланс счета, если указан
            if account_id:
                if trans_type == 'income':
                    self.update_account_balance(account_id, amount, 'add')
                else:
                    self.update_account_balance(account_id, amount, 'subtract')

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    # Обновленный метод обновления транзакции
    def update_transaction(self, transaction_id, amount, category_name, trans_type, date=None, description=None,
                           account_id=None):
        """Обновляет существующую транзакцию"""
        conn = self._get_connection()
        try:
            # Получаем старые данные транзакции
            cursor = conn.cursor()
            cursor.execute('SELECT amount, type, account_id FROM transactions WHERE id = ?', (transaction_id,))
            old_data = cursor.fetchone()

            if not old_data:
                raise ValueError("Транзакция не найдена")

            old_amount, old_type, old_account_id = old_data

            # Получаем ID категории
            cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
            category_id = cursor.fetchone()

            if not category_id:
                raise ValueError(f"Категория '{category_name}' не найдена")

            # Форматируем дату
            date_str = date.strftime('%Y-%m-%d %H:%M:%S') if date else None

            # Обновляем транзакцию
            cursor.execute('''
                UPDATE transactions 
                SET amount = ?, category_id = ?, type = ?, date = ?, description = ?, account_id = ?
                WHERE id = ?
            ''', (amount, category_id[0], trans_type, date_str, description, account_id, transaction_id))

            # Обновляем балансы счетов, если они изменились
            if old_account_id or account_id:
                # Отменяем старую операцию
                if old_account_id:
                    if old_type == 'income':
                        self.update_account_balance(old_account_id, old_amount, 'subtract')
                    else:
                        self.update_account_balance(old_account_id, old_amount, 'add')

                # Применяем новую операцию
                if account_id:
                    if trans_type == 'income':
                        self.update_account_balance(account_id, amount, 'add')
                    else:
                        self.update_account_balance(account_id, amount, 'subtract')

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def set_default_account_for_existing_transactions(self):
        conn = sqlite3.connect('finance.db')
        cursor = conn.cursor()

        try:
            # Находим ID основного счета
            cursor.execute("SELECT id FROM accounts WHERE name = 'Основной счет'")
            account_id = cursor.fetchone()

            if account_id:
                # Обновляем все существующие транзакции
                cursor.execute('''
                UPDATE transactions 
                SET account_id = ?
                WHERE account_id IS NULL
                ''', (account_id[0],))
                print(f"Обновлено {cursor.rowcount} транзакций")

            conn.commit()
        except Exception as e:
            print(f"Ошибка: {str(e)}")
            conn.rollback()
        finally:
            conn.close()




    if __name__ == '__main__':
        set_default_account_for_existing_transactions()
# Пример использования
if __name__ == '__main__':
    app = FinanceApp()


