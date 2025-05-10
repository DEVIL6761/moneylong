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
    document.querySelectorAll('select').forEach(select => {
        select.addEventListener('click', function(e) {
            e.preventDefault();
            this.focus();
            this.size = this.options.length; // Принудительное открытие вниз
            setTimeout(() => this.size = 1, 100);
        });
    });
});