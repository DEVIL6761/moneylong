
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

// Обработчик удаления операции
document.addEventListener('click', async function(e) {
    if (e.target.closest('.delete-btn')) {
        const id = e.target.closest('.delete-btn').dataset.id;
        if (confirm('Вы уверены, что хотите удалить эту операцию?')) {
            try {
                const response = await fetch(`/delete_transaction/${id}`, {
                    method: 'DELETE'
                });

                if (response.ok) {
                    e.target.closest('tr').remove();
                    location.reload(); // Обновляем страницу для обновления аналитики
                } else {
                    alert('Ошибка при удалении операции');
                }
            } catch (error) {
                console.error('Error:', error);
            }
        }
    }
});

// Обработчик редактирования операции
document.addEventListener('click', function(e) {
    if (e.target.closest('.edit-btn')) {
        const id = e.target.closest('.edit-btn').dataset.id;
        window.location.href = `/edit_transaction/${id}`;
    }
});


// Фильтрация категорий по типу операции
document.addEventListener('DOMContentLoaded', function() {
    const typeSelect = document.querySelector('select[name="type"]');
    const categorySelect = document.getElementById('categorySelect');

    if (typeSelect && categorySelect) {
        // При изменении типа операции
        typeSelect.addEventListener('change', function() {
            const selectedType = this.value;
            const options = categorySelect.querySelectorAll('option[data-type]');

            // Сначала скрываем все опции
            options.forEach(option => {
                option.style.display = 'none';
                option.disabled = true;
            });

            // Показываем только соответствующие выбранному типу
            const validOptions = categorySelect.querySelectorAll(`option[data-type="${selectedType}"]`);
            validOptions.forEach(option => {
                option.style.display = 'block';
                option.disabled = false;
            });

            // Сбрасываем выбранную категорию
            categorySelect.value = '';

            // Активируем первый доступный вариант
            if (validOptions.length > 0) {
                validOptions[0].selected = true;
            }
        });

        // Инициализация при загрузке
        typeSelect.dispatchEvent(new Event('change'));
    }
});



// Для формы редактирования
document.addEventListener('DOMContentLoaded', function() {
    const editTypeSelect = document.querySelector('select[name="type"]');
    const editCategorySelect = document.getElementById('editCategorySelect');

    if (editTypeSelect && editCategorySelect) {
        editTypeSelect.addEventListener('change', function() {
            const selectedType = this.value;
            const options = editCategorySelect.querySelectorAll('option[data-type]');

            options.forEach(option => {
                if (option.getAttribute('data-type') === selectedType || option.selected) {
                    option.style.display = 'block';
                    option.disabled = false;
                } else {
                    option.style.display = 'none';
                    option.disabled = true;
                }
            });
        });

        // Инициализация при загрузке
        editTypeSelect.dispatchEvent(new Event('change'));
    }
});


// Обработчик для кнопки добавления счета
document.getElementById('addAccountBtn').addEventListener('click', function() {
    // Показываем модальное окно
    document.getElementById('accountModal').style.display = 'block';
});

// Закрытие модального окна
document.querySelector('.modal .close')?.addEventListener('click', function() {
    document.getElementById('accountModal').style.display = 'none';
});

// Закрытие при клике вне окна
window.addEventListener('click', function(event) {
    if (event.target === document.getElementById('accountModal')) {
        document.getElementById('accountModal').style.display = 'none';
    }
});


// Удаление счета
document.querySelectorAll('.delete-account-btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
        e.stopPropagation(); // Предотвращаем всплытие события
        const accountId = this.getAttribute('data-id');

        if (confirm('Вы уверены, что хотите удалить этот счет? Все связанные транзакции будут удалены.')) {
            fetch(`/delete_account/${accountId}`, {
                method: 'DELETE',
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Ошибка: ' + (data.error || 'Не удалось удалить счет'));
                }
            })
            .catch(error => {
                alert('Ошибка сети: ' + error);
            });
        }
    });
});


// Ensure account is selected before form submission
document.querySelector('form').addEventListener('submit', function(e) {
    const accountSelect = this.querySelector('select[name="account"]');
    if (!accountSelect.value) {
        e.preventDefault();
        alert('Пожалуйста, выберите счет для операции');
        accountSelect.focus();
    }
});


// Подсветка активной ссылки в навигации
    document.addEventListener('DOMContentLoaded', function() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-link');

        navLinks.forEach(link => {
            if (link.getAttribute('href') === currentPath) {
                link.classList.add('active');
            }
        });
    });