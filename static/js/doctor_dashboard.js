function authHeaders() {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

document.querySelectorAll('.open-consultation').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.getElementById('appointmentId').value = btn.dataset.appointmentId;
    document.getElementById('doctorId').value = btn.dataset.doctorId;
  });
});

document.getElementById('consultationForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    appointment_id: Number(document.getElementById('appointmentId').value),
    doctor_id: Number(document.getElementById('doctorId').value),
    diagnosis: document.getElementById('diagnosis').value,
    notes: document.getElementById('notes').value,
    recommendation: document.getElementById('recommendation').value,
  };

  const res = await fetch('/consultations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  const msg = document.getElementById('doctorDashboardMessage');
  msg.textContent = res.ok ? `Consultation saved (ID: ${data.id})` : (data.detail || 'Failed to save consultation');
});

document.querySelectorAll('.generate-report').forEach((btn) => {
  btn.addEventListener('click', async () => {
    const consultationId = btn.dataset.consultationId;
    if (!consultationId) {
      alert('Create consultation first.');
      return;
    }

    const res = await fetch(`/reports/generate?consultation_id=${consultationId}`, {
      method: 'POST',
      headers: authHeaders(),
    });
    const data = await res.json();
    if (res.ok) {
      window.open(data.file_url, '_blank');
    } else {
      alert(data.detail || 'Failed to generate report');
    }
  });
});
