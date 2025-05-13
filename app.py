from flask import Flask, render_template, request, redirect, url_for, flash

from database import init_db
from finance_app import FinanceApp
import sqlite3
import os
from flask import render_template, request, jsonify
from datetime import datetime
import pandas as pd



app = Flask(__name__, template_folder='templates')
app.secret_key = 'your-secret-key-123'
finance_app = FinanceApp()

# Инициализация БД
init_db()

# Путь к базе данных
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'finance.db')


@app.route('/')
def home():
    try:
        # Преобразуем DataFrame в словари с ID
        transactions = finance_app.get_transactions().to_dict('records')
        # Проверка данных (для дебага)
        print(transactions[0])  # Посмотрите в консоли Flask, есть ли там 'id'
        return render_template('index.html',
                            transactions=transactions,
                            categories=finance_app.get_categories().to_dict('records'))
    except Exception as e:
        return f"Ошибка: {str(e)}", 500


@app.route('/add_transaction', methods=['POST'])
def add_transaction_route():
    try:
        amount = float(request.form['amount'].replace(',', '.'))
        trans_type = request.form['type']
        description = request.form.get('description', '')
        date_str = request.form.get('date')

        if request.form['category'] == '__new__':
            category = request.form['new_category']
            category_type = request.form['new_category_type']
            if not finance_app.add_category(category, category_type):
                flash('Категория уже существует!', 'warning')
                return redirect(url_for('home'))
        else:
            category = request.form['category']

        date_obj = datetime.strptime(date_str, '%Y-%m-%d') if date_str else None

        finance_app.add_transaction(
            amount=amount,
            category_name=category,
            trans_type=trans_type,
            date=date_obj,
            description=description
        )

        flash('Операция успешно добавлена!', 'success')
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'danger')

    return redirect(url_for('home'))


@app.route('/add_category', methods=['POST'])
def add_category_route():
    try:
        name = request.form['name']
        trans_type = request.form['type']

        if finance_app.add_category(name, trans_type):
            flash('Категория добавлена!', 'success')
        else:
            flash('Категория уже существует!', 'warning')
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'danger')
    return redirect(url_for('home'))


@app.route('/analytics')
def analytics():
    selected_month = request.args.get('month') or datetime.now().strftime('%Y-%m')

    daily_stats = finance_app.get_daily_stats(month=selected_month)
    expense_stats = finance_app.get_expense_stats()
    income_stats = finance_app.get_income_stats()

    # Все уникальные месяцы в базе
    df = finance_app.get_transactions()
    df['month'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')
    months = sorted(df['month'].unique(), reverse=True)

    return render_template('analytics.html',
                           daily_stats=daily_stats,
                           expense_stats=expense_stats,
                           income_stats=income_stats,
                           selected_month=selected_month,
                           months=months)


@app.route('/delete_transaction/<int:transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
        conn.commit()
        return '', 200
    except Exception as e:
        return str(e), 500
    finally:
        conn.close()


@app.route('/edit_transaction/<int:transaction_id>', methods=['GET', 'POST'])
def edit_transaction(transaction_id):
    if request.method == 'GET':
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.id, t.amount, t.type, t.description, t.date, c.name 
                FROM transactions t 
                JOIN categories c ON t.category_id = c.id 
                WHERE t.id = ?
            ''', (transaction_id,))
            transaction = cursor.fetchone()

            if not transaction:
                flash('Операция не найдена', 'danger')
                return redirect(url_for('home'))

            return render_template('edit_transaction.html',
                                   transaction=transaction,
                                   categories=finance_app.get_categories().to_dict('records'))
        finally:
            conn.close()

    elif request.method == 'POST':
        try:
            amount = float(request.form['amount'].replace(',', '.'))
            trans_type = request.form['type']
            description = request.form.get('description', '')
            date_str = request.form.get('date')
            category_name = request.form['category']

            finance_app.update_transaction(
                transaction_id=transaction_id,
                amount=amount,
                category_name=category_name,
                trans_type=trans_type,
                date=datetime.strptime(date_str, '%Y-%m-%d') if date_str else None,
                description=description
            )

            flash('Операция успешно обновлена', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            flash(f'Ошибка: {str(e)}', 'danger')
            return redirect(url_for('edit_transaction', transaction_id=transaction_id))


if __name__ == '__main__':
    app.run(debug=True)