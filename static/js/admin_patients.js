function authHeaders() {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function setMessage(text) {
  document.getElementById('patientAdminMessage').textContent = text;
}

document.getElementById('addPatientForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    clinic_id: Number(document.getElementById('patientClinicId').value),
    parent_name: document.getElementById('patientParentName').value,
    child_name: document.getElementById('patientChildName').value,
    child_age: Number(document.getElementById('patientChildAge').value),
    email: document.getElementById('patientEmail').value.trim(),
    phone: document.getElementById('patientPhone').value,
    password: document.getElementById('patientPassword').value || null,
  };

  const res = await fetch('/patients', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  setMessage(res.ok ? `Patient added: ${data.child_name}` : (data.detail || 'Failed to add patient'));
  if (res.ok) window.location.reload();
});
