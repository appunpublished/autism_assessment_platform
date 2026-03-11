function authHeaders() {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const today = new Date();
let state = { month: today.getMonth() + 1, year: today.getFullYear(), map: {} };

async function fetchJson(url) {
  const res = await fetch(url, { headers: authHeaders() });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Request failed');
  return data;
}

function renderCalendar(days) {
  const grid = document.getElementById('calendarGrid');
  grid.innerHTML = '';
  state.map = {};
  days.forEach((item) => {
    state.map[item.date] = item;
    const col = document.createElement('div');
    col.className = 'col';
    const day = Number(item.date.split('-')[2]);

    let colorClass = 'bg-success';
    if (item.status === 'booked') colorClass = 'bg-danger';
    if (item.status === 'leave') colorClass = 'bg-secondary';

    col.innerHTML = `<button class="btn ${colorClass} text-white w-100 day-btn" data-date="${item.date}">${day}</button>`;
    grid.appendChild(col);
  });

  document.querySelectorAll('.day-btn').forEach((btn) => {
    btn.addEventListener('click', async () => {
      await loadDaySlots(btn.dataset.date);
    });
  });
}

async function loadCalendar() {
  const title = document.getElementById('calendarTitle');
  title.textContent = `${state.year}-${String(state.month).padStart(2, '0')}`;
  const data = await fetchJson(`/consultations/doctor/calendar-data?month=${state.month}&year=${state.year}`);
  renderCalendar(data.days);
}

async function loadDaySlots(day) {
  const data = await fetchJson(`/consultations/doctor/day-slots?selected_date=${day}`);
  document.getElementById('selectedDateTitle').textContent = `Slots for ${day}`;

  const bookedRows = data.booked.map((item) => `
    <tr>
      <td>${item.time_slot}</td>
      <td>${item.patient_name}</td>
      <td>${item.status}</td>
      <td><a class="btn btn-sm btn-primary" href="/consultations/doctor/appointment/${item.appointment_id}">Consultation</a></td>
    </tr>
  `).join('');

  const freeRows = data.free_slots.map((slot) => `<span class="badge text-bg-success me-1 mb-1">${slot}</span>`).join('');

  document.getElementById('daySlots').innerHTML = `
    <h6>Booked Slots</h6>
    <table class="table table-sm table-striped">
      <thead><tr><th>Time</th><th>Patient</th><th>Status</th><th>Action</th></tr></thead>
      <tbody>${bookedRows || '<tr><td colspan="4">No booked slots</td></tr>'}</tbody>
    </table>
    <h6>Free Slots</h6>
    <div>${freeRows || 'No free slots'}</div>
  `;
}

document.getElementById('prevMonth').addEventListener('click', async () => {
  state.month -= 1;
  if (state.month < 1) {
    state.month = 12;
    state.year -= 1;
  }
  await loadCalendar();
});

document.getElementById('nextMonth').addEventListener('click', async () => {
  state.month += 1;
  if (state.month > 12) {
    state.month = 1;
    state.year += 1;
  }
  await loadCalendar();
});

loadCalendar();
