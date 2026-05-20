// Инициализация Telegram Web App
let tg = null;

if (typeof window !== 'undefined' && window.Telegram && window.Telegram.WebApp) {
    tg = window.Telegram.WebApp;
    tg.ready();
    tg.setHeaderColor('#ffffff');
    tg.setBackgroundColor('#f5f5f7');
} else {
    // Mock объект для локального тестирования
    tg = {
        showAlert: (msg) => alert(msg),
        CloudStorage: {
            getItem: async (key) => localStorage.getItem(key),
            setItem: async (key, val) => localStorage.setItem(key, val)
        }
    };
}

// Данные приложения
let records = [];

// Функция для показа toast-уведомления
function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.remove('error');
    if (isError) {
        toast.classList.add('error');
    }
    toast.classList.add('show');

    setTimeout(() => {
        toast.classList.remove('show');
    }, 2500);
}

// Инициализация
document.addEventListener('DOMContentLoaded', async () => {
    const form = document.getElementById('recordForm');
    form.addEventListener('submit', handleFormSubmit);

    // Загружаем историю при открытии
    await loadRecords();
    displayHistory();
});

// Загрузка записей из Telegram CloudStorage
async function loadRecords() {
    try {
        const data = await tg.CloudStorage.getItem('records');
        if (data) {
            records = JSON.parse(data);
        } else {
            records = [];
        }
    } catch (error) {
        console.error('Ошибка загрузки:', error);
        // Fallback на localStorage если CloudStorage недоступно
        records = JSON.parse(localStorage.getItem('records')) || [];
    }
}

// Сохранение записей в Telegram CloudStorage
async function saveRecords() {
    try {
        await tg.CloudStorage.setItem('records', JSON.stringify(records));
    } catch (error) {
        console.error('Ошибка сохранения:', error);
        // Fallback на localStorage
        localStorage.setItem('records', JSON.stringify(records));
    }
}

// Обработка формы
async function handleFormSubmit(e) {
    e.preventDefault();

    const group = document.getElementById('groupSelect').value;
    const deviceName = document.getElementById('deviceName').value;
    const buyPrice = parseFloat(document.getElementById('buyPrice').value) || 0;
    const sellPrice = parseFloat(document.getElementById('sellPrice').value) || 0;

    if (!group || !deviceName) {
        showToast('⚠️ Заполните группу и название устройства', true);
        return;
    }

    if (buyPrice === 0 && sellPrice === 0) {
        showToast('⚠️ Введите цену покупки или продажи', true);
        return;
    }

    // Создаем запись
    const record = {
        id: Date.now(),
        timestamp: new Date().toLocaleString('ru-RU'),
        group: group,
        device: deviceName,
        buyPrice: buyPrice,
        sellPrice: sellPrice,
        profit: (sellPrice - buyPrice).toFixed(2)
    };

    // Добавляем в начало массива
    records.unshift(record);

    // Сохраняем в CloudStorage
    await saveRecords();

    // Очищаем форму
    document.getElementById('recordForm').reset();

    // Обновляем историю
    displayHistory();

    // Показываем уведомление
    showToast('✅ Запись добавлена');
}

// Отображение истории
function displayHistory() {
    const historyList = document.getElementById('historyList');

    if (records.length === 0) {
        historyList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📊</div>
                <div class="empty-text">Нет записей</div>
            </div>
        `;
        return;
    }

    historyList.innerHTML = records.map(record => {
        // Определяем тип (покупка или продажа)
        let type, typeClass, amount;
        if (record.buyPrice > 0 && record.sellPrice === 0) {
            type = 'ПОКУПКА';
            typeClass = 'buy';
            amount = `₽${record.buyPrice.toLocaleString('ru-RU')}`;
        } else if (record.sellPrice > 0 && record.buyPrice === 0) {
            type = 'ПРОДАЖА';
            typeClass = 'sell';
            amount = `₽${record.sellPrice.toLocaleString('ru-RU')}`;
        } else if (record.buyPrice > 0 && record.sellPrice > 0) {
            type = record.profit > 0 ? 'ПРИБЫЛЬ' : 'УБЫТОК';
            typeClass = record.profit > 0 ? 'buy' : 'sell';
            amount = `${record.profit > 0 ? '+' : ''}₽${record.profit}`;
        } else {
            return '';
        }

        return `
            <div class="history-item ${typeClass}" onclick="deleteRecord(${record.id})">
                <div class="history-item-group">${record.group}</div>
                <div class="history-item-device">${record.device}</div>
                <div class="history-item-price">
                    <span class="history-item-type ${typeClass}">${type}</span>
                    <span class="history-item-amount">${amount}</span>
                </div>
            </div>
        `;
    }).join('');
}

// Удаление записи
async function deleteRecord(id) {
    if (confirm('Удалить эту запись?')) {
        records = records.filter(r => r.id !== id);
        await saveRecords();
        displayHistory();
    }
}

// Закрытие приложения при нажатии кнопки закрытия
tg.onEvent('mainButtonClicked', () => {
    tg.close();
});
