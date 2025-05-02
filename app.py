
from flask import Flask, jsonify, request, render_template, redirect, url_for
from finance_app import FinanceApp

app = Flask(__name__)
finance_app = FinanceApp()


# Главная страница с формой
@app.route('/')
def home():
    expenses = finance_app.get_expenses('all').to_dict('records')  # Получаем все расходы
    return render_template('index.html', expenses=expenses)


# API: Добавление расхода (теперь принимает данные из формы)
@app.route('/add_expense', methods=['POST'])
def add_expense():
    try:
        amount = float(request.form['amount'])
        category = request.form['category'].strip()
        description = request.form.get('description', '').strip()

        if amount <= 0:
            raise ValueError("Сумма должна быть положительной")
        if not category:
            raise ValueError("Категория не может быть пустой")

        finance_app.add_expense(amount, category, description)
        return redirect(url_for('home'))

    except Exception as e:
        return f"Ошибка: {str(e)}", 400

# API: Получение расходов в JSON (оставим для мобильного приложения)
@app.route('/api/expenses')
def api_expenses():
    period = request.args.get('period', 'month')
    expenses = finance_app.get_expenses(period).to_dict('records')
    return jsonify(expenses)


if __name__ == '__main__':
    app.run(debug=True)