function authHeaders() {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function setMessage(text) {
  document.getElementById('consultationMessage').textContent = text;
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

const loadAnswersBtn = document.getElementById('loadAssessmentAnswers');
if (loadAnswersBtn) {
  loadAnswersBtn.addEventListener('click', async () => {
    const assessmentId = loadAnswersBtn.dataset.assessmentId;
    try {
      const data = await fetchJson(`/assessment/${assessmentId}/details`);
      const rows = data.answers.map((x) => `
        <tr>
          <td>${x.section}</td>
          <td>${x.question}</td>
          <td>${x.selected_text}</td>
          <td>${x.score}</td>
        </tr>
      `).join('');
      document.getElementById('assessmentAnswers').innerHTML = `
        <table class="table table-sm table-bordered">
          <thead><tr><th>Section</th><th>Question</th><th>Answer</th><th>Score</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      `;
    } catch (err) {
      setMessage(err.message);
    }
  });
}

document.getElementById('doctorConsultationForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const appointmentId = Number(document.getElementById('appointmentId').value);
  const doctorId = Number(document.getElementById('doctorId').value);
  const payload = {
    appointment_id: appointmentId,
    doctor_id: doctorId,
    diagnosis: document.getElementById('diagnosis').value,
    notes: document.getElementById('notes').value,
    recommendation: document.getElementById('recommendation').value,
  };

  try {
    const data = await fetchJson(`/consultations/doctor/appointment/${appointmentId}/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    setMessage(`Consultation saved (ID: ${data.id})`);
    setTimeout(() => window.location.reload(), 600);
  } catch (err) {
    setMessage(err.message);
  }
});

const reportBtn = document.getElementById('generateReportBtn');
if (reportBtn) {
  reportBtn.addEventListener('click', async () => {
    const consultationId = reportBtn.dataset.consultationId;
    try {
      const data = await fetchJson(`/reports/generate?consultation_id=${consultationId}`, {
        method: 'POST',
      });
      window.open(data.file_url, '_blank');
    } catch (err) {
      setMessage(err.message);
    }
  });
}
