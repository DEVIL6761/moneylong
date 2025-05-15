from flask import Flask, render_template, request, redirect, url_for, flash, g, jsonify
from datetime import datetime
import sqlite3
import os
import time
from functools import wraps
import pandas as pd
from contextlib import contextmanager

app = Flask(__name__, template_folder='templates')
app.secret_key = 'your-secret-key-123'
DATABASE = 'finance.db'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'finance.db')


# Database initialization
def init_db():
    with db_connection() as conn:
        cursor = conn.cursor()

        # Create tables with proper constraints
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
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        ''')

        # Add default data
        default_data(cursor)
        conn.commit()


def default_data(cursor):
    # Default categories
    categories = [
        ('Еда', 'expense'),
        ('Транспорт', 'expense'),
        ('Зарплата', 'income')
    ]

    for name, cat_type in categories:
        try:
            cursor.execute('INSERT OR IGNORE INTO categories (name, type) VALUES (?, ?)', (name, cat_type))
        except sqlite3.IntegrityError:
            pass

    # Default account
    try:
        cursor.execute('INSERT OR IGNORE INTO accounts (name, balance) VALUES (?, ?)', ('Основной счет', 0))
    except sqlite3.IntegrityError:
        pass


# Database connection management
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH, timeout=30)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=NORMAL")
        db.execute("PRAGMA busy_timeout=30000")
        db.execute("PRAGMA foreign_keys=ON")
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@contextmanager
def db_connection():
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()


# Retry decorator for database operations
def handle_db_locks(max_retries=3, delay=0.1):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return f(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
                        continue
                    flash('База данных временно недоступна. Попробуйте позже.', 'danger')
                    app.logger.error(f"Database locked error: {str(e)}")
                    raise
                except Exception as e:
                    flash(f'Ошибка: {str(e)}', 'danger')
                    app.logger.error(f"Error in {f.__name__}: {str(e)}")
                    raise

        return wrapped

    return decorator


# Helper functions
def get_finance_data():
    """Get all finance data in one query to reduce database access"""
    with db_connection() as conn:
        transactions = pd.read_sql('''
            SELECT t.*, c.name as category_name, a.name as account_name 
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            JOIN accounts a ON t.account_id = a.id
            ORDER BY t.date DESC
        ''', conn)

        categories = pd.read_sql('SELECT * FROM categories', conn)
        accounts = pd.read_sql('SELECT * FROM accounts', conn)
        total_balance = pd.read_sql('SELECT SUM(balance) as total FROM accounts', conn).iloc[0]['total'] or 0

    return {
        'transactions': transactions.to_dict('records'),
        'categories': categories.to_dict('records'),
        'accounts': accounts.to_dict('records'),
        'total_balance': total_balance
    }


# Routes
@app.route('/')
@handle_db_locks()
def home():
    try:
        data = get_finance_data()
        return render_template('index.html', **data)
    except Exception as e:
        app.logger.error(f"Error in home route: {str(e)}")
        return render_template('error.html', error=str(e)), 500


@app.route('/add_transaction', methods=['POST'])
@handle_db_locks()
def add_transaction_route():
    try:
        # Get form data
        amount = float(request.form['amount'].replace(',', '.'))
        trans_type = request.form['type']
        description = request.form.get('description', '')
        date_str = request.form.get('date')
        account_id = request.form.get('account')

        with db_connection() as conn:
            cursor = conn.cursor()

            # Handle category
            if request.form['category'] == '__new__':
                category = request.form.get('new_category', '').strip()
                category_type = request.form.get('new_category_type', 'expense')

                if not category:
                    flash('Необходимо указать название категории!', 'danger')
                    return redirect(url_for('home'))

                try:
                    cursor.execute('INSERT INTO categories (name, type) VALUES (?, ?)', (category, category_type))
                    conn.commit()
                except sqlite3.IntegrityError:
                    flash('Категория уже существует!', 'warning')
                    return redirect(url_for('home'))
            else:
                category = request.form['category']

            # Get category ID
            cursor.execute('SELECT id FROM categories WHERE name = ?', (category,))
            category_id = cursor.fetchone()
            if not category_id:
                flash('Выбранная категория не найдена!', 'danger')
                return redirect(url_for('home'))

            # Handle account
            if not account_id:
                cursor.execute('SELECT id FROM accounts LIMIT 1')
                account_result = cursor.fetchone()
                if not account_result:
                    flash('Необходимо создать хотя бы один счет!', 'danger')
                    return redirect(url_for('home'))
                account_id = account_result[0]

            # Check account exists
            cursor.execute('SELECT id FROM accounts WHERE id = ?', (account_id,))
            if not cursor.fetchone():
                flash('Выбранный счет не существует!', 'danger')
                return redirect(url_for('home'))

            # Prepare date
            date_obj = datetime.strptime(date_str, '%Y-%m-%d') if date_str else None
            date_str_db = date_obj.strftime('%Y-%m-%d %H:%M:%S') if date_obj else datetime.now().strftime(
                '%Y-%m-%d %H:%M:%S')

            # Add transaction
            cursor.execute('''
                INSERT INTO transactions (amount, category_id, date, description, type, account_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (amount, category_id[0], date_str_db, description, trans_type, account_id))

            # Update account balance
            if trans_type == 'income':
                cursor.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (amount, account_id))
            else:
                cursor.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (amount, account_id))

            conn.commit()
            flash('Операция успешно добавлена!', 'success')

    except ValueError as e:
        flash(f'Ошибка в данных: {str(e)}', 'danger')
    except Exception as e:
        flash(f'Неожиданная ошибка: {str(e)}', 'danger')
        app.logger.error(f"Error in add_transaction: {str(e)}")

    return redirect(url_for('home'))


@app.route('/add_account', methods=['POST'])
@handle_db_locks()
def add_account():
    try:
        name = request.form['name']
        initial_balance = float(request.form.get('initial_balance', 0))
        currency = request.form.get('currency', 'BYN')
        description = request.form.get('description', '')

        with db_connection() as conn:
            try:
                conn.execute('''
                    INSERT INTO accounts (name, balance, currency, description)
                    VALUES (?, ?, ?, ?)
                ''', (name, initial_balance, currency, description))
                conn.commit()
                flash('Счет успешно добавлен!', 'success')
            except sqlite3.IntegrityError:
                flash('Счет с таким именем уже существует!', 'warning')

    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'danger')
        app.logger.error(f"Error in add_account: {str(e)}")

    return redirect(url_for('home'))


@app.route('/add_category', methods=['POST'])
@handle_db_locks()
def add_category_route():
    try:
        name = request.form['name']
        trans_type = request.form['type']

        with db_connection() as conn:
            try:
                conn.execute('INSERT INTO categories (name, type) VALUES (?, ?)', (name, trans_type))
                conn.commit()
                flash('Категория добавлена!', 'success')
            except sqlite3.IntegrityError:
                flash('Категория уже существует!', 'warning')

    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'danger')
        app.logger.error(f"Error in add_category: {str(e)}")

    return redirect(url_for('home'))


@app.route('/analytics')
@handle_db_locks()
def analytics():
    try:
        selected_month = request.args.get('month') or datetime.now().strftime('%Y-%m')

        with db_connection() as conn:
            # Get available months
            months_df = pd.read_sql('''
                SELECT DISTINCT strftime('%Y-%m', date) as month 
                FROM transactions 
                ORDER BY month DESC
            ''', conn)
            months = months_df['month'].tolist()

            # Get daily stats
            daily_stats = pd.read_sql(f'''
                SELECT 
                    strftime('%d', date) as day,
                    SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
                    SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense
                FROM transactions
                WHERE strftime('%Y-%m', date) = ?
                GROUP BY day
                ORDER BY day
            ''', conn, params=(selected_month,)).to_dict('records')

            # Get expense stats
            expense_stats = pd.read_sql(f'''
                SELECT c.name, SUM(t.amount) as total
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE t.type = 'expense' AND strftime('%Y-%m', t.date) = ?
                GROUP BY c.name
                ORDER BY total DESC
            ''', conn, params=(selected_month,)).to_dict('records')

            # Get income stats
            income_stats = pd.read_sql(f'''
                SELECT c.name, SUM(t.amount) as total
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE t.type = 'income' AND strftime('%Y-%m', t.date) = ?
                GROUP BY c.name
                ORDER BY total DESC
            ''', conn, params=(selected_month,)).to_dict('records')

        return render_template('analytics.html',
                               daily_stats=daily_stats,
                               expense_stats=expense_stats,
                               income_stats=income_stats,
                               selected_month=selected_month,
                               months=months)

    except Exception as e:
        app.logger.error(f"Error in analytics: {str(e)}")
        return render_template('error.html', error=str(e)), 500


@app.route('/delete_transaction/<int:transaction_id>', methods=['DELETE'])
@handle_db_locks()
def delete_transaction(transaction_id):
    try:
        with db_connection() as conn:
            cursor = conn.cursor()

            # Get transaction details first
            cursor.execute('SELECT amount, type, account_id FROM transactions WHERE id = ?', (transaction_id,))
            trans = cursor.fetchone()

            if trans:
                amount, trans_type, account_id = trans

                # Delete the transaction
                cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))

                # Update account balance
                if account_id:
                    if trans_type == 'income':
                        cursor.execute('UPDATE accounts SET balance = balance - ? WHERE id = ?', (amount, account_id))
                    else:
                        cursor.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (amount, account_id))

                conn.commit()
                return jsonify({'success': True}), 200
            else:
                return jsonify({'success': False, 'error': 'Transaction not found'}), 404

    except Exception as e:
        app.logger.error(f"Error deleting transaction: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/edit_transaction/<int:transaction_id>', methods=['GET', 'POST'])
@handle_db_locks()
def edit_transaction(transaction_id):
    """
    Обработчик редактирования существующей транзакции
    GET - отображает форму редактирования
    POST - сохраняет изменения
    """
    try:
        if request.method == 'GET':
            # Получение данных для формы редактирования
            with db_connection() as conn:
                # Получаем полные данные транзакции
                transaction = pd.read_sql('''
                    SELECT 
                        t.id,
                        t.amount,
                        t.type,
                        t.description,
                        DATE(t.date) as date,
                        c.name as category_name,
                        c.type as category_type,
                        t.account_id,
                        a.name as account_name,
                        a.currency
                    FROM transactions t
                    JOIN categories c ON t.category_id = c.id
                    JOIN accounts a ON t.account_id = a.id
                    WHERE t.id = ?
                ''', conn, params=(transaction_id,))

                if transaction.empty:
                    flash('Транзакция не найдена', 'danger')
                    return redirect(url_for('home'))

                transaction_data = transaction.iloc[0].to_dict()

                # Получаем все категории для выпадающего списка
                categories = pd.read_sql('''
                    SELECT id, name, type 
                    FROM categories 
                    WHERE type = ?
                    ORDER BY name
                ''', conn, params=(transaction_data['type'],))

                # Получаем все счета для выпадающего списка
                accounts = pd.read_sql('''
                    SELECT id, name, balance, currency 
                    FROM accounts 
                    ORDER BY name
                ''', conn)

                return render_template(
                    'edit_transaction.html',
                    transaction=transaction_data,
                    categories=categories.to_dict('records'),
                    accounts=accounts.to_dict('records'),
                    transaction_id=transaction_id
                )

        elif request.method == 'POST':
            # Обработка сохранения изменений
            form = request.form

            # Валидация данных
            errors = []

            try:
                amount = float(form['amount'].replace(',', '.'))
                if amount <= 0:
                    errors.append("Сумма должна быть положительной")
            except (ValueError, KeyError):
                errors.append("Некорректный формат суммы")

            if form['type'] not in ('income', 'expense'):
                errors.append("Некорректный тип транзакции")

            if not form.get('category'):
                errors.append("Не указана категория")

            if errors:
                for error in errors:
                    flash(error, 'danger')
                return redirect(url_for('edit_transaction', transaction_id=transaction_id))

            with db_connection() as conn:
                cursor = conn.cursor()

                # 1. Получаем старые данные транзакции
                cursor.execute('''
                    SELECT amount, type, account_id, category_id
                    FROM transactions
                    WHERE id = ?
                ''', (transaction_id,))
                old_data = cursor.fetchone()

                if not old_data:
                    flash('Транзакция не найдена в базе данных', 'danger')
                    return redirect(url_for('home'))

                old_amount, old_type, old_account_id, old_category_id = old_data

                # 2. Получаем ID новой категории
                cursor.execute('''
                    SELECT id, type 
                    FROM categories 
                    WHERE name = ?
                ''', (form['category'],))
                category_data = cursor.fetchone()

                if not category_data:
                    flash('Указанная категория не существует', 'danger')
                    return redirect(url_for('edit_transaction', transaction_id=transaction_id))

                category_id, category_type = category_data

                # 3. Проверяем соответствие типа категории и транзакции
                if category_type != form['type']:
                    flash('Тип категории не соответствует типу транзакции', 'danger')
                    return redirect(url_for('edit_transaction', transaction_id=transaction_id))

                # 4. Проверяем существование счета
                account_id = form.get('account')
                if account_id:
                    cursor.execute('SELECT 1 FROM accounts WHERE id = ?', (account_id,))
                    if not cursor.fetchone():
                        flash('Указанный счет не существует', 'danger')
                        return redirect(url_for('edit_transaction', transaction_id=transaction_id))

                # 5. Подготавливаем дату (без времени)
                date_value = form.get('date') or datetime.now().strftime('%Y-%m-%d')

                # 6. Обновляем транзакцию
                cursor.execute('''
                    UPDATE transactions SET
                        amount = ?,
                        category_id = ?,
                        type = ?,
                        date = DATE(?),
                        description = ?,
                        account_id = ?
                    WHERE id = ?
                ''', (
                    amount,
                    category_id,
                    form['type'],
                    date_value,
                    form.get('description', ''),
                    account_id,
                    transaction_id
                ))

                # 7. Корректируем балансы счетов
                # 7.1. Отменяем влияние старой транзакции
                if old_account_id:
                    adjustment = old_amount if old_type == 'expense' else -old_amount
                    cursor.execute('''
                        UPDATE accounts 
                        SET balance = balance + ?
                        WHERE id = ?
                    ''', (adjustment, old_account_id))

                # 7.2. Применяем влияние новой транзакции
                if account_id:
                    adjustment = -amount if form['type'] == 'expense' else amount
                    cursor.execute('''
                        UPDATE accounts 
                        SET balance = balance + ?
                        WHERE id = ?
                    ''', (adjustment, account_id))

                conn.commit()
                flash('Транзакция успешно обновлена', 'success')
                return redirect(url_for('home'))

    except sqlite3.Error as e:
        flash('Ошибка базы данных при обновлении транзакции', 'danger')
        app.logger.error(f'Database error in edit_transaction: {str(e)}', exc_info=True)
        return redirect(url_for('home'))

    except Exception as e:
        flash('Неизвестная ошибка при обработке транзакции', 'danger')
        app.logger.error(f'Unexpected error in edit_transaction: {str(e)}', exc_info=True)
        return redirect(url_for('home'))


# Template filter
@app.template_filter('format_month')
def format_month(value):
    month_names = {
        '01': 'январь', '02': 'февраль', '03': 'март', '04': 'апрель',
        '05': 'май', '06': 'июнь', '07': 'июль', '08': 'август',
        '09': 'сентябрь', '10': 'октябрь', '11': 'ноябрь', '12': 'декабрь'
    }
    try:
        year, month = value.split('-')
        return f"{month_names.get(month, month)} {year}"
    except Exception:
        return value


if __name__ == '__main__':
    init_db()
    app.run(debug=True)