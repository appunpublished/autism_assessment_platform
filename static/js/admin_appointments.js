function authHeaders() {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function setMessage(text) {
  document.getElementById('adminBookingMessage').textContent = text;
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: { ...(options.headers || {}), ...authHeaders() },
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Request failed');
  }
  return data;
}

function fillSelect(selectId, items, valueKey, labelBuilder, placeholder) {
  const select = document.getElementById(selectId);
  select.innerHTML = '';
  if (placeholder) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = placeholder;
    select.appendChild(option);
  }
  items.forEach((item) => {
    const option = document.createElement('option');
    option.value = item[valueKey];
    option.textContent = labelBuilder(item);
    select.appendChild(option);
  });
}

async function loadAssessments(patientId) {
  const select = document.getElementById('adminAssessmentId');
  select.innerHTML = '<option value="">Select assessment</option>';
  if (!patientId) return;

  const assessments = await fetchJson(`/assessment/patient/${patientId}`);
  assessments.forEach((item) => {
    const option = document.createElement('option');
    option.value = item.id;
    option.textContent = `#${item.id} - ${item.risk_level}`;
    select.appendChild(option);
  });
}

async function loadSlots() {
  const doctorId = document.getElementById('adminDoctorId').value;
  const date = document.getElementById('adminAppointmentDate').value;
  if (!doctorId || !date) {
    setMessage('Select doctor and date first.');
    return;
  }

  const data = await fetchJson(`/appointments/slots?doctor_id=${doctorId}&appointment_date=${date}`);
  const select = document.getElementById('adminTimeSlot');
  select.innerHTML = '';

  if (data.slots.length === 0) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = data.on_leave ? 'Doctor unavailable (leave)' : 'No slots available';
    select.appendChild(option);
    return;
  }

  data.slots.forEach((slot) => {
    const option = document.createElement('option');
    option.value = slot;
    option.textContent = slot;
    select.appendChild(option);
  });
}

async function init() {
  try {
    const [clinics, doctors, patients] = await Promise.all([
      fetchJson('/clinics'),
      fetchJson('/doctors'),
      fetchJson('/patients'),
    ]);

    fillSelect('adminClinicId', clinics, 'id', (x) => x.name, 'Select clinic');
    fillSelect('adminDoctorId', doctors, 'id', (x) => `${x.name} (${x.specialization})`, 'Select doctor');
    fillSelect('adminPatientId', patients, 'id', (x) => x.child_name, 'Select patient');

    if (patients.length > 0) {
      await loadAssessments(patients[0].id);
    }
  } catch (err) {
    setMessage(err.message);
  }
}

document.getElementById('adminPatientId').addEventListener('change', async (e) => {
  await loadAssessments(e.target.value);
});

document.getElementById('adminLoadSlots').addEventListener('click', async () => {
  try {
    await loadSlots();
  } catch (err) {
    setMessage(err.message);
  }
});

document.getElementById('adminDoctorId').addEventListener('change', async () => {
  try {
    await loadSlots();
  } catch (err) {
    setMessage(err.message);
  }
});

document.getElementById('adminAppointmentDate').addEventListener('change', async () => {
  try {
    await loadSlots();
  } catch (err) {
    setMessage(err.message);
  }
});

document.getElementById('adminBookingForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    clinic_id: Number(document.getElementById('adminClinicId').value),
    doctor_id: Number(document.getElementById('adminDoctorId').value),
    patient_id: Number(document.getElementById('adminPatientId').value),
    assessment_id: Number(document.getElementById('adminAssessmentId').value),
    appointment_date: document.getElementById('adminAppointmentDate').value,
    time_slot: document.getElementById('adminTimeSlot').value,
  };

  try {
    if (!payload.assessment_id) {
      setMessage('Select an assessment. Booking is risk-based.');
      return;
    }
    const data = await fetchJson('/appointments/book', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    setMessage(`Appointment booked: #${data.id}`);
    window.location.reload();
  } catch (err) {
    setMessage(err.message);
  }
});

init();
