document.addEventListener('DOMContentLoaded', function() {
    // Показ/скрытие истории операций
    const historyToggle = document.getElementById('historyToggle');
    const transactionHistory = document.getElementById('transactionHistory');

    // Обработчик для кнопки истории
    historyToggle.addEventListener('click', function() {
        const history = document.getElementById('transactionHistory');
        history.style.display = history.style.display === 'block' ? 'none' : 'block';
        this.innerHTML = history.style.display === 'block'
            ? '<i class="fas fa-times"></i> Скрыть историю'
            : '<i class="fas fa-history"></i> История операций';
    });

    // Инициализация - скрываем историю при загрузке
    transactionHistory.style.display = 'none';

    // Валидация поля суммы
    document.querySelector('input[name="amount"]').addEventListener('input', function(e) {
        // Заменяем запятую на точку для корректного парсинга
        this.value = this.value.replace(',', '.');

        // Проверяем формат числа с 2 знаками после точки
        if (!/^\d*\.?\d{0,2}$/.test(this.value)) {
            this.setCustomValidity('Введите сумму (например: 125.50)');
        } else {
            this.setCustomValidity('');
        }
    });

    // Анимация выбора категории
    // Удалите этот блок полностью, если не нужны специальные эффекты:
document.querySelectorAll('select').forEach(select => {
    select.addEventListener('click', function(e) {
        // Убрать e.preventDefault() и setTimeout
        this.focus();
    });
});




// Обработчик формы
document.querySelector('form').addEventListener('submit', function(e) {
    const submitBtn = this.querySelector('button[type="submit"]');

    // Добавляем состояние загрузки
    submitBtn.classList.add('btn-loading');
    submitBtn.disabled = true;

    // Для демонстрации - в реальном приложении это будет после ответа сервера
    setTimeout(() => {
        submitBtn.classList.remove('btn-loading');

        // Симуляция успешного ответа (замените на реальную проверку)
        const isSuccess = Math.random() > 0.5;

        if (isSuccess) {
            submitBtn.classList.add('btn-success-pulse');
            submitBtn.innerHTML = '<i class="fas fa-check"></i> Успешно!';
        } else {
            submitBtn.classList.add('btn-error-pulse');
            submitBtn.innerHTML = '<i class="fas fa-times"></i> Ошибка!';
        }

        // Возвращаем исходное состояние через 3 секунды
        setTimeout(() => {
            submitBtn.classList.remove('btn-success-pulse', 'btn-error-pulse');
            submitBtn.innerHTML = '<i class="fas fa-save"></i> Добавить операцию';
            submitBtn.disabled = false;
        }, 3000);
    }, 1000);
});

 if (document.getElementById('expenseChart')) {
        initAnalyticsCharts();
    }
});

function initAnalyticsCharts() {
    // Данные для графиков (должны передаваться из Flask)
    const expenseData = {
        labels: JSON.parse(document.getElementById('expenseChart').dataset.labels),
        values: JSON.parse(document.getElementById('expenseChart').dataset.values),
        total: parseFloat(document.getElementById('expenseChart').dataset.total)
    };

    const incomeData = {
        labels: JSON.parse(document.getElementById('incomeChart').dataset.labels),
        values: JSON.parse(document.getElementById('incomeChart').dataset.values),
        total: parseFloat(document.getElementById('incomeChart').dataset.total)
    };

    // Создаем кольцевые диаграммы
    createDoughnutChart('expenseChart', expenseData);
    createDoughnutChart('incomeChart', incomeData);
}

function createDoughnutChart(chartId, data) {
    const ctx = document.getElementById(chartId).getContext('2d');
    const totalElement = document.getElementById(chartId.replace('Chart', 'Total'));

    // Отображаем общую сумму в центре
    totalElement.textContent = `${data.total.toFixed(2)} ₽`;

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.values,
                backgroundColor: [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                    '#9966FF', '#FF9F40', '#8AC24A', '#607D8B'
                ],
                borderWidth: 1
            }]
        },
        options: {
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'right'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.raw.toFixed(2)} ₽ (${context.percentage.toFixed(1)}%)`;
                        }
                    }
                }
            },
            animation: {
                animateScale: true,
                animateRotate: true
            }
        }
    });
}