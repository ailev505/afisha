// ============================================================
// Конфигурация API
// ============================================================
// ВАЖНО: замени на свой Forwarded Address из Codespaces (Ports → 5000)
const API_URL = 'https://probable-halibut-jjxj7695rx5g3pqwr-5000.app.github.dev/';

// ============================================================
// Утилиты
// ============================================================
function formatDate(iso) {
  const d = new Date(iso);
  const months = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
  const day = d.getDate();
  const month = months[d.getMonth()];
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${day} ${month}, ${hh}:${mm}`;
}

function seatsLeft(play) {
  return play.seats_total - play.seats_taken;
}

async function apiGet(path) {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `API error ${res.status}`);
  return data;
}

async function apiDelete(path) {
  const res = await fetch(`${API_URL}${path}`, { method: 'DELETE' });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `API error ${res.status}`);
  return data;
}

// ============================================================
// Главная страница — афиша
// ============================================================
async function initIndexPage() {
  const container = document.getElementById('plays-list');
  if (!container) return;

  try {
    const plays = await apiGet('/plays');

    if (!plays.length) {
      container.innerHTML = '<p class="loading">Спектаклей пока нет.</p>';
      return;
    }

    container.innerHTML = plays.map(play => `
      <div class="play-card">
        <h3>${play.title}</h3>
        <p class="date">📅 ${formatDate(play.date)}</p>
        <p class="price">${play.price} ₽</p>
        <p class="seats-left">Свободно мест: ${seatsLeft(play)} из ${play.seats_total}</p>
        <a href="seats.html?play=${play.id}" class="btn-primary">Выбрать место</a>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = `<p class="loading">Ошибка загрузки: ${e.message}</p>`;
  }
}

// ============================================================
// Страница выбора мест
// ============================================================
let currentPlay = null;
let selectedSeats = [];

async function initSeatsPage() {
  const params = new URLSearchParams(window.location.search);
  const playId = params.get('play');

  if (!playId) {
    document.getElementById('play-title').textContent = 'Спектакль не выбран';
    document.getElementById('seats-grid').innerHTML = '';
    return;
  }

  try {
    currentPlay = await apiGet(`/plays/${playId}`);
    const seatsData = await apiGet(`/plays/${playId}/seats`);
    currentPlay.seatsTaken = seatsData.seats_taken;

    document.getElementById('play-title').textContent =
      `${currentPlay.title} — ${formatDate(currentPlay.date)}`;

    renderSeats();
    updateCheckoutBar();

    document.getElementById('buy-btn').addEventListener('click', buyTickets);
  } catch (e) {
    document.getElementById('play-title').textContent = 'Ошибка загрузки';
    document.getElementById('seats-grid').innerHTML =
      `<p class="loading">${e.message}</p>`;
  }
}

function renderSeats() {
  const grid = document.getElementById('seats-grid');
  grid.innerHTML = '';

  for (let i = 1; i <= currentPlay.seats_total; i++) {
    const seat = document.createElement('div');
    seat.className = 'seat';
    seat.textContent = i;

    if (currentPlay.seatsTaken.includes(i)) {
      seat.classList.add('taken');
    } else {
      seat.classList.add('free');
      seat.addEventListener('click', () => toggleSeat(i, seat));
    }

    grid.appendChild(seat);
  }
}

function toggleSeat(num, el) {
  const idx = selectedSeats.indexOf(num);
  if (idx === -1) {
    selectedSeats.push(num);
    el.classList.add('selected');
    el.classList.remove('free');
  } else {
    selectedSeats.splice(idx, 1);
    el.classList.remove('selected');
    el.classList.add('free');
  }
  updateCheckoutBar();
}

function updateCheckoutBar() {
  document.getElementById('selected-count').textContent = selectedSeats.length;
  document.getElementById('total-price').textContent = selectedSeats.length * currentPlay.price;
  document.getElementById('buy-btn').disabled = selectedSeats.length === 0;
}

async function buyTickets() {
  if (!selectedSeats.length) return;

  const order = {
    play_id: currentPlay.id,
    seats: [...selectedSeats].sort((a, b) => a - b),
    order_number: 'ORD-' + Date.now()
  };

  try {
    await apiPost('/buy', order);

    // Сохраняем для страницы билета
    sessionStorage.setItem('lastOrder', JSON.stringify({
      playTitle: currentPlay.title,
      playDate: currentPlay.date,
      seats: order.seats,
      total: order.seats.length * currentPlay.price,
      orderNumber: order.order_number
    }));

    window.location.href = 'checkout.html';
  } catch (e) {
    alert('Ошибка покупки: ' + e.message);
  }
}

// ============================================================
// Страница билета
// ============================================================
function initCheckoutPage() {
  const data = sessionStorage.getItem('lastOrder');
  if (!data) {
    document.getElementById('ticket').innerHTML = '<p class="loading">Заказ не найден.</p>';
    return;
  }

  const order = JSON.parse(data);
  document.getElementById('ticket-play').textContent = order.playTitle;
  document.getElementById('ticket-date').textContent = formatDate(order.playDate);
  document.getElementById('ticket-seats').textContent = order.seats.join(', ');
  document.getElementById('ticket-total').textContent = order.total;
  document.getElementById('ticket-order').textContent = order.orderNumber;

  if (typeof QRCode !== 'undefined') {
    new QRCode(document.getElementById('qrcode'), {
      text: JSON.stringify(order),
      width: 160,
      height: 160,
      colorDark: '#000000',
      colorLight: '#ffffff'
    });
  }
}

// ============================================================
// Админка
// ============================================================
async function initAdminPage() {
  await renderAdminTable();

  const form = document.getElementById('add-play-form');
  if (form) {
    form.addEventListener('submit', async e => {
      e.preventDefault();
      const title = document.getElementById('play-title-input').value.trim();
      const date = document.getElementById('play-date-input').value;
      const price = Number(document.getElementById('play-price-input').value);
      const seats_total = Number(document.getElementById('play-seats-input').value);

      if (!title || !date || price < 0 || seats_total < 1) {
        alert('Заполните все поля корректно.');
        return;
      }

      try {
        await apiPost('/plays', { title, date, price, seats_total });
        form.reset();
        document.getElementById('play-seats-input').value = 50;
        await renderAdminTable();
      } catch (e) {
        alert('Ошибка добавления: ' + e.message);
      }
    });
  }
}

async function renderAdminTable() {
  const tbody = document.getElementById('admin-plays-body');
  if (!tbody) return;

  try {
    const plays = await apiGet('/plays');

    if (!plays.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="loading">Спектаклей нет.</td></tr>';
      return;
    }

    tbody.innerHTML = plays.map(p => `
      <tr>
        <td>${p.id}</td>
        <td>${p.title}</td>
        <td>${formatDate(p.date)}</td>
        <td>${p.price} ₽</td>
        <td>${seatsLeft(p)} / ${p.seats_total}</td>
        <td><button class="btn-danger" onclick="deletePlay(${p.id})">Удалить</button></td>
      </tr>
    `).join('');
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6" class="loading">Ошибка: ${e.message}</td></tr>`;
  }
}

async function deletePlay(id) {
  if (!confirm('Удалить спектакль?')) return;
  try {
    await apiDelete(`/plays/${id}`);
    await renderAdminTable();
  } catch (e) {
    alert('Ошибка удаления: ' + e.message);
  }
}

// ============================================================
// Автозапуск
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('plays-list')) initIndexPage();
});