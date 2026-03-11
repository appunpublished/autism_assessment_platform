function authHeaders() {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const assessmentById = new Map();

function setMessage(text) {
  document.getElementById('bookingMessage').textContent = text;
}

function setRiskDetails(riskLevel) {
  const riskInput = document.getElementById('selectedRiskLevel');
  const priorityInput = document.getElementById('appointmentPriority');

  if (!riskLevel) {
    riskInput.value = '';
    priorityInput.value = '';
    return;
  }

  riskInput.value = riskLevel;
  const map = {
    'Low Risk': 'Routine Consultation',
    'Moderate Risk': 'Priority Consultation',
    'High Risk': 'Urgent Consultation',
  };
  priorityInput.value = map[riskLevel] || 'Routine Consultation';
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: { ...(options.headers || {}), ...authHeaders() },
  });
  const data = await res.json();
  if (!res.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : 'Request failed';
    throw new Error(detail);
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

async function loadBaseDropdowns() {
  try {
    const [clinics, doctors, patients] = await Promise.all([
      fetchJson('/clinics'),
      fetchJson('/doctors'),
      fetchJson('/patients'),
    ]);

    fillSelect('clinicId', clinics, 'id', (x) => x.name, 'Select clinic');
    fillSelect('doctorId', doctors, 'id', (x) => `${x.name} (${x.specialization})`, 'Select doctor');
    fillSelect('patientId', patients, 'id', (x) => `${x.child_name} - Parent: ${x.parent_name}`, 'Select patient');

    if (patients.length > 0) {
      document.getElementById('patientId').value = String(patients[0].id);
      await loadAssessmentsForPatient(patients[0].id);
    }
  } catch (err) {
    setMessage(`Failed to load booking data: ${err.message}`);
  }
}

async function loadAssessmentsForPatient(patientId) {
  const select = document.getElementById('assessmentId');
  select.innerHTML = '<option value="">Select assessment</option>';
  assessmentById.clear();
  setRiskDetails('');

  if (!patientId) {
    return;
  }

  try {
    const assessments = await fetchJson(`/assessment/patient/${patientId}`);
    assessments.forEach((item) => {
      assessmentById.set(String(item.id), item);
      const option = document.createElement('option');
      option.value = item.id;
      option.textContent = `#${item.id} - ${item.risk_level} (Score ${item.score})`;
      select.appendChild(option);
    });

    if (assessments.length > 0) {
      select.value = String(assessments[0].id);
      setRiskDetails(assessments[0].risk_level);
    }
  } catch (err) {
    setMessage(`Could not load assessments: ${err.message}`);
  }
}

async function loadSlots() {
  const doctorId = document.getElementById('doctorId').value;
  const appointmentDate = document.getElementById('appointmentDate').value;
  if (!doctorId || !appointmentDate) {
    setMessage('Select doctor and date first to load slots.');
    return;
  }

  try {
    const data = await fetchJson(`/appointments/slots?doctor_id=${doctorId}&appointment_date=${appointmentDate}`);
    const select = document.getElementById('timeSlot');
    select.innerHTML = '';

    if (data.on_leave) {
      setMessage('Selected doctor is marked out of office for this date.');
    } else {
      setMessage('');
    }

    (data.slots || []).forEach((slot) => {
      const option = document.createElement('option');
      option.value = slot;
      option.textContent = slot;
      select.appendChild(option);
    });

    if (!data.slots || data.slots.length === 0) {
      const option = document.createElement('option');
      option.value = '';
      option.textContent = data.on_leave ? 'Doctor unavailable (leave)' : 'No slots available';
      select.appendChild(option);
    }
  } catch (err) {
    setMessage(`Failed to load slots: ${err.message}`);
  }
}

document.getElementById('loadSlots').addEventListener('click', loadSlots);

const doctorSelect = document.getElementById('doctorId');
const dateInput = document.getElementById('appointmentDate');
doctorSelect.addEventListener('change', loadSlots);
dateInput.addEventListener('change', loadSlots);

document.getElementById('patientId').addEventListener('change', async (e) => {
  await loadAssessmentsForPatient(e.target.value);
});

document.getElementById('assessmentId').addEventListener('change', (e) => {
  const picked = assessmentById.get(e.target.value);
  setRiskDetails(picked ? picked.risk_level : '');
});

document.getElementById('bookingForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const selectedAssessmentId = document.getElementById('assessmentId').value;
  if (!selectedAssessmentId) {
    setMessage('Select an assessment. Appointment booking is based on risk level.');
    return;
  }

  const payload = {
    clinic_id: Number(document.getElementById('clinicId').value),
    doctor_id: Number(document.getElementById('doctorId').value),
    patient_id: Number(document.getElementById('patientId').value),
    assessment_id: Number(selectedAssessmentId),
    appointment_date: document.getElementById('appointmentDate').value,
    time_slot: document.getElementById('timeSlot').value,
  };

  if (!payload.time_slot) {
    setMessage('Load and select a valid time slot before booking.');
    return;
  }

  try {
    const data = await fetchJson('/appointments/book', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    setMessage(`Booked successfully. Appointment ID: ${data.id}`);
    await loadSlots();
  } catch (err) {
    setMessage(err.message || 'Booking failed');
  }
});

loadBaseDropdowns();
