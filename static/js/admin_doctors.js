function authHeaders() {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function setMessage(text) {
  document.getElementById('doctorAdminMessage').textContent = text;
}

document.getElementById('addDoctorForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    clinic_id: Number(document.getElementById('doctorClinicId').value),
    name: document.getElementById('doctorName').value,
    specialization: document.getElementById('doctorSpec').value,
    email: document.getElementById('doctorEmail').value.trim(),
    phone: document.getElementById('doctorPhone').value,
    password: document.getElementById('doctorPassword').value || null,
  };

  const res = await fetch('/doctors', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  setMessage(res.ok ? `Doctor created: ${data.name}` : (data.detail || 'Failed to create doctor'));
  if (res.ok) window.location.reload();
});

document.getElementById('doctorLeaveForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const doctorId = document.getElementById('leaveDoctorId').value;
  const payload = {
    start_date: document.getElementById('leaveStartDate').value,
    end_date: document.getElementById('leaveEndDate').value,
    reason: document.getElementById('leaveReason').value,
    status: document.getElementById('leaveStatus').value,
  };

  const res = await fetch(`/admin/doctors/${doctorId}/leave`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  setMessage(res.ok ? data.message : (data.detail || 'Failed to mark leave'));
});
