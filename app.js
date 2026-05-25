// =================== ИНИЦИАЛИЗАЦИЯ TELEGRAM ===================

let tg = null;

if (typeof window !== 'undefined' && window.Telegram && window.Telegram.WebApp) {
    tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();
    tg.setHeaderColor('#ffffff');
    tg.setBackgroundColor('#f5f5f7');
} else {
    tg = { showAlert: (msg) => alert(msg), initDataUnsafe: {} };
}

const USER_ID = tg?.initDataUnsafe?.user?.id || 1;

// =================== API ===================

async function apiFetch(url, options = {}) {
    const res = await fetch(url, {
        ...options,
        headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

// =================== ФОРМАТИРОВАНИЕ ===================

function showToast(msg, isError = false) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.className = 'toast' + (isError ? ' error' : '');
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2500);
}

function fmt(n) {
    return '₽' + (Number(n) || 0).toLocaleString('ru-RU', { maximumFractionDigits: 0 });
}

function fmtDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr.includes('T') ? dateStr : dateStr + 'T00:00:00');
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);
    if (d.toDateString() === today.toDateString()) return 'Сегодня';
    if (d.toDateString() === yesterday.toDateString()) return 'Вчера';
    return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
}

function fmtDateShort(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr.includes('T') ? dateStr : dateStr + 'T00:00:00');
    return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
}

// =================== ИНИЦИАЛИЗАЦИЯ DOM ===================

document.addEventListener('DOMContentLoaded', async () => {
    document.getElementById('recordForm').addEventListener('submit', handleFormSubmit);

    document.getElementById('groupSelect').addEventListener('change', function () {
        document.getElementById('customSellerGroup').style.display =
            this.value === 'Другой' ? 'flex' : 'none';
    });

    ['buyPrice', 'sellPrice', 'quantity'].forEach(id =>
        document.getElementById(id).addEventListener('input', updateTotals)
    );

    await loadRecords();
});

// =================== ИТОГИ В ФОРМЕ ===================

function updateTotals() {
    const buy = parseFloat(document.getElementById('buyPrice').value) || 0;
    const sell = parseFloat(document.getElementById('sellPrice').value) || 0;
    const qty = parseInt(document.getElementById('quantity').value) || 1;

    document.getElementById('totalBuy').textContent =
        buy > 0 ? `Итого покупка (${qty} шт.): ${fmt(buy * qty)}` : '';
    document.getElementById('totalSell').textContent =
        sell > 0 ? `Итого продажа (${qty} шт.): ${fmt(sell * qty)}` : '';
    document.getElementById('totalsDisplay').style.display =
        (buy > 0 || sell > 0) ? 'flex' : 'none';
}

// =================== ОТПРАВКА ФОРМЫ ===================

async function handleFormSubmit(e) {
    e.preventDefault();

    const group = document.getElementById('groupSelect').value;
    const customSeller = document.getElementById('customSellerName').value.trim();
    const device = document.getElementById('deviceName').value.trim();
    const buy = parseFloat(document.getElementById('buyPrice').value) || 0;
    const sell = parseFloat(document.getElementById('sellPrice').value) || 0;
    const qty = parseInt(document.getElementById('quantity').value) || 1;
    const buyer = document.getElementById('buyerName').value.trim() || null;

    if (!group || !device) {
        showToast('Заполните группу и устройство', true);
        return;
    }
    if (group === 'Другой' && !customSeller) {
        showToast('Введите имя продавца', true);
        return;
    }
    if (buy === 0 && sell === 0) {
        showToast('Введите цену покупки или продажи', true);
        return;
    }

    const btn = document.querySelector('.submit-btn');
    btn.disabled = true;
    btn.textContent = 'Сохранение...';

    try {
        await apiFetch('/api/records', {
            method: 'POST',
            body: JSON.stringify({
                user_id: USER_ID,
                seller_group: group,
                custom_seller_name: group === 'Другой' ? customSeller : null,
                device,
                buy_price: buy,
                sell_price: sell,
                quantity: qty,
                buyer_name: buyer
            })
        });

        e.target.reset();
        document.getElementById('quantity').value = '1';
        document.getElementById('customSellerGroup').style.display = 'none';
        document.getElementById('totalsDisplay').style.display = 'none';

        showToast('✅ Запись добавлена');
        await loadRecords();
    } catch (err) {
        showToast('Ошибка сохранения', true);
        console.error(err);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Добавить запись';
    }
}

// =================== ЗАГРУЗКА И ОТОБРАЖЕНИЕ ИСТОРИИ ===================

let records = [];

async function loadRecords() {
    try {
        const data = await apiFetch('/api/records');
        records = data.records || [];
        displayHistory();
    } catch (e) {
        console.error('Load error:', e);
        showToast('Ошибка загрузки данных', true);
    }
}

function displayHistory() {
    const list = document.getElementById('historyList');

    if (!records?.length) {
        list.innerHTML = `<div class="empty-state">
            <div class="empty-icon">📊</div>
            <div class="empty-text">Нет записей</div>
        </div>`;
        return;
    }

    // Группируем по дате
    const grouped = {};
    records.forEach(r => {
        const key = r.date || (r.timestamp || '').split('T')[0] || 'unknown';
        (grouped[key] = grouped[key] || []).push(r);
    });

    const dates = Object.keys(grouped).sort((a, b) => b.localeCompare(a));

    let html = '';
    dates.forEach(key => {
        const dayRecs = grouped[key];
        const dayProfit = dayRecs.reduce((s, r) => s + (Number(r.profit) || 0), 0);

        html += `<div class="date-group-header">
            <span>${fmtDate(key)}</span>
            <span class="${dayProfit >= 0 ? 'positive' : 'negative'}">${dayProfit >= 0 ? '+' : ''}${fmt(dayProfit)}</span>
        </div>`;

        dayRecs.forEach(r => {
            const seller = r.custom_seller_name || r.seller_group || '';
            const profit = Number(r.profit) || 0;
            let type, cls, amount;

            if (r.buy_price > 0 && (!r.sell_price || r.sell_price === 0)) {
                type = 'ПОКУПКА'; cls = 'purchase';
                amount = fmt(r.buy_price * r.quantity);
            } else if (r.sell_price > 0 && (!r.buy_price || r.buy_price === 0)) {
                type = 'ПРОДАЖА'; cls = 'sold';
                amount = fmt(r.sell_price * r.quantity);
            } else {
                type = profit >= 0 ? 'ПРИБЫЛЬ' : 'УБЫТОК';
                cls = profit >= 0 ? 'buy' : 'sell';
                amount = `${profit >= 0 ? '+' : ''}${fmt(profit)}`;
            }

            const qtyBadge = r.quantity > 1
                ? `<span class="qty-badge">${r.quantity} шт.</span>` : '';
            const buyerLine = r.buyer_name
                ? `<div class="history-item-buyer">→ ${r.buyer_name}</div>` : '';
            const detailsLine = (r.buy_price > 0 && r.sell_price > 0)
                ? `<div class="history-item-details">
                    <span>Покупка: ${fmt(r.buy_price * r.quantity)}</span>
                    <span>Продажа: ${fmt(r.sell_price * r.quantity)}</span>
                   </div>` : '';

            html += `<div class="history-item ${cls}" onclick="confirmDelete(${r.id})">
                <div class="history-item-top">
                    <span class="history-item-group">${seller}</span>
                    ${qtyBadge}
                </div>
                <div class="history-item-device">${r.device}</div>
                ${buyerLine}
                <div class="history-item-price">
                    <span class="history-item-type ${cls}">${type}</span>
                    <span class="history-item-amount">${amount}</span>
                </div>
                ${detailsLine}
            </div>`;
        });
    });

    list.innerHTML = html;
}

async function confirmDelete(id) {
    if (!confirm('Удалить запись?')) return;
    try {
        await apiFetch(`/api/records/${id}`, { method: 'DELETE' });
        showToast('Запись удалена');
        await loadRecords();
    } catch (e) {
        showToast('Ошибка удаления', true);
    }
}

// =================== СТАТИСТИКА ===================

let currentStatsPeriod = 'day';

async function openStats() {
    document.getElementById('statsModal').classList.remove('hidden');
    await loadStats('day');
    await loadCashBalance();
    await populateSellerDropdown();
}

function closeStats() {
    document.getElementById('statsModal').classList.add('hidden');
}

async function loadStats(period) {
    currentStatsPeriod = period;

    document.querySelectorAll('.period-tab').forEach(btn =>
        btn.classList.toggle('active', btn.dataset.period === period)
    );

    try {
        const data = await apiFetch(`/api/stats?period=${period}`);
        const s = data.data;

        const profit = Number(s.total_profit) || 0;
        const profitEl = document.getElementById('statProfit');
        profitEl.textContent = fmt(profit);
        profitEl.className = 'stat-card-value ' + (profit >= 0 ? 'positive' : 'negative');

        document.getElementById('statBuys').textContent = fmt(s.total_buys || 0);
        document.getElementById('statSells').textContent = fmt(s.total_sells || 0);
        document.getElementById('statDeals').textContent = (s.deals_count || 0) + ' шт.';

        renderChart(s, period);
    } catch (e) {
        console.error('Stats error:', e);
        showToast('Ошибка загрузки статистики', true);
    }
}

function renderChart(data, period) {
    const container = document.getElementById('statsChartContainer');
    const byDate = data.by_date || {};
    const dates = Object.keys(byDate).sort();

    if (!dates.length) {
        container.innerHTML = '<div class="no-chart-data">Нет данных за выбранный период</div>';
        return;
    }

    if (typeof Plotly === 'undefined') {
        container.innerHTML = '<div class="no-chart-data">График загружается...</div>';
        return;
    }

    let xLabels, yValues;

    if (period === 'all' && dates.length > 30) {
        // За всё время — агрегируем по месяцам
        const byMonth = {};
        dates.forEach(d => {
            const m = d.slice(0, 7);
            byMonth[m] = (byMonth[m] || 0) + (byDate[d].profit || 0);
        });
        const months = Object.keys(byMonth).sort();
        xLabels = months.map(m => {
            const [y, mo] = m.split('-');
            return new Date(+y, +mo - 1).toLocaleDateString('ru-RU', { month: 'short', year: '2-digit' });
        });
        yValues = months.map(m => byMonth[m]);
    } else {
        xLabels = dates.map(fmtDateShort);
        yValues = dates.map(d => byDate[d].profit || 0);
    }

    Plotly.newPlot(container, [{
        x: xLabels,
        y: yValues,
        type: 'bar',
        marker: { color: yValues.map(p => p >= 0 ? '#34c759' : '#ff3b30') },
        hovertemplate: '<b>%{x}</b><br>Прибыль: %{y:,.0f}₽<extra></extra>'
    }], {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: {
            family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif',
            color: '#1d1d1f',
            size: 10
        },
        margin: { t: 10, r: 8, b: 55, l: 55 },
        xaxis: { gridcolor: '#e5e5e7', tickangle: -30, fixedrange: true },
        yaxis: { gridcolor: '#e5e5e7', tickformat: ',.0f', ticksuffix: '₽', fixedrange: true },
        bargap: 0.3
    }, { displayModeBar: false, responsive: true });
}

// =================== ИСТОРИЯ ПО ПРОДАВЦУ ===================

async function populateSellerDropdown() {
    try {
        const data = await apiFetch('/api/records');
        const sellers = [...new Set(
            (data.records || []).map(r => r.custom_seller_name || r.seller_group).filter(Boolean)
        )].sort();

        const select = document.getElementById('sellerStatsSelect');
        select.innerHTML = '<option value="">Выберите продавца</option>' +
            sellers.map(s => `<option value="${encodeURIComponent(s)}">${s}</option>`).join('');
    } catch (e) {
        console.error('Seller dropdown:', e);
    }
}

async function loadSellerStats() {
    const encoded = document.getElementById('sellerStatsSelect').value;
    const container = document.getElementById('sellerHistoryContainer');

    if (!encoded) {
        container.innerHTML = '';
        return;
    }

    const seller = decodeURIComponent(encoded);

    try {
        const data = await apiFetch(`/api/records/seller/${encoded}`);
        const recs = data.records || [];

        if (!recs.length) {
            container.innerHTML = '<div class="no-data">Нет записей по этому продавцу</div>';
            return;
        }

        const totalProfit = recs.reduce((s, r) => s + (Number(r.profit) || 0), 0);
        const totalBuys = recs.reduce((s, r) => s + (r.buy_price || 0) * (r.quantity || 1), 0);
        const totalSells = recs.reduce((s, r) => s + (r.sell_price || 0) * (r.quantity || 1), 0);

        container.innerHTML = `
            <div class="seller-summary">
                <div class="seller-stat-card">
                    <div class="seller-stat-label">Сделок</div>
                    <div class="seller-stat-value">${recs.length}</div>
                </div>
                <div class="seller-stat-card">
                    <div class="seller-stat-label">Покупки</div>
                    <div class="seller-stat-value">${fmt(totalBuys)}</div>
                </div>
                <div class="seller-stat-card">
                    <div class="seller-stat-label">Продажи</div>
                    <div class="seller-stat-value">${fmt(totalSells)}</div>
                </div>
                <div class="seller-stat-card">
                    <div class="seller-stat-label">Прибыль</div>
                    <div class="seller-stat-value ${totalProfit >= 0 ? 'positive' : 'negative'}">${fmt(totalProfit)}</div>
                </div>
            </div>
            <div class="seller-table-wrapper">
                <table class="seller-table">
                    <thead>
                        <tr>
                            <th>Устройство</th>
                            <th>Кол</th>
                            <th>Покупка</th>
                            <th>Продажа</th>
                            <th>Прибыль</th>
                            <th>Дата</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${recs.map(r => `<tr>
                            <td>${r.device || '—'}</td>
                            <td>${r.quantity || 1}</td>
                            <td>${r.buy_price > 0 ? fmt(r.buy_price * (r.quantity || 1)) : '—'}</td>
                            <td>${r.sell_price > 0 ? fmt(r.sell_price * (r.quantity || 1)) : '—'}</td>
                            <td class="${(Number(r.profit) || 0) >= 0 ? 'positive' : 'negative'}">${fmt(r.profit || 0)}</td>
                            <td>${fmtDateShort(r.date)}</td>
                        </tr>`).join('')}
                    </tbody>
                </table>
            </div>`;
    } catch (e) {
        showToast('Ошибка загрузки истории продавца', true);
    }
}

// =================== КАССА ===================

async function loadCashBalance() {
    try {
        const [cashRes, statsRes] = await Promise.all([
            apiFetch('/api/cash/balance'),
            apiFetch('/api/stats?period=all')
        ]);
        const initial = Number(cashRes.balance) || 0;
        const profit = Number(statsRes.data?.total_profit) || 0;
        const balance = initial + profit;

        document.getElementById('cashInitial').textContent =
            `Начальный капитал: ${fmt(initial)}`;
        document.getElementById('cashProfitLine').textContent =
            `Прибыль от сделок: ${profit >= 0 ? '+' : ''}${fmt(profit)}`;

        const balEl = document.getElementById('cashBalance');
        balEl.textContent = fmt(balance);
        balEl.className = 'cash-balance-value ' + (balance >= 0 ? 'positive' : 'negative');
    } catch (e) {
        console.error('Cash error:', e);
    }
}

async function handleInitCash() {
    const input = prompt('Введите начальный баланс кассы (₽):');
    if (input === null) return;

    const amount = parseFloat(input.replace(/\s/g, '').replace(',', '.'));
    if (isNaN(amount) || amount < 0) {
        showToast('Введите корректную сумму', true);
        return;
    }

    try {
        await apiFetch(`/api/cash/initialize?amount=${amount}`, { method: 'POST' });
        showToast('Касса обновлена');
        await loadCashBalance();
    } catch (e) {
        showToast('Ошибка установки кассы', true);
    }
}
