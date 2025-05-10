from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
from database import init_db
from finance_app import FinanceApp  # Импорт класса



app = Flask(__name__)
app.secret_key = 'your-secret-key-123'
finance_app = FinanceApp()  # Создаём экземпляр здесь

# Инициализация БД
init_db()

@app.route('/')
def home():
    try:
        transactions = finance_app.get_transactions().to_dict('records')
        categories = finance_app.get_categories().to_dict('records')
        return render_template('index.html',
                            transactions=transactions,
                            finance_app=finance_app,
                            categories=categories)
    except Exception as e:
        return f"Ошибка: {str(e)}", 500


@app.route('/add_transaction', methods=['POST'])
def add_transaction_route():
    try:
        # Преобразуем строку в float, заменяя запятые на точки
        amount = float(request.form['amount'].replace(',', '.'))
        # Остальной код без изменений...
        trans_type = request.form['type']
        description = request.form.get('description', '')
        date_str = request.form.get('date')

        # Обработка новой категории
        if request.form['category'] == '__new__':
            category = request.form['new_category']
            category_type = request.form['new_category_type']
            if not finance_app.add_category(category, category_type):
                flash('Категория уже существует!', 'warning')
                return redirect(url_for('home'))
        else:
            category = request.form['category']

        # Остальная логика добавления транзакции
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
def add_category_route():  # Изменили имя функции
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
    try:
        # Получаем данные для аналитики
        expenses = finance_app.get_transactions(trans_type='expense')
        incomes = finance_app.get_transactions(trans_type='income')

        # Готовим данные для графиков
        expense_stats = finance_app.get_expense_stats()
        income_stats = finance_app.get_income_stats()

        return render_template('analytics.html',
                               expenses=expenses.to_dict('records'),
                               incomes=incomes.to_dict('records'),
                               expense_stats=expense_stats,
                               income_stats=income_stats)
    except Exception as e:
        flash(f'Ошибка при загрузке аналитики: {str(e)}', 'danger')
        return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)  # Добавьте debug=True