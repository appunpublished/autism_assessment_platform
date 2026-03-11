const token = localStorage.getItem('token');
const headers = token ? { Authorization: `Bearer ${token}` } : {};
const hasAuth = Boolean(token);

function setMessage(text) {
  document.getElementById('assessmentMessage').textContent = text;
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: { ...(options.headers || {}), ...headers },
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

function groupedQuestionsMarkup(questions) {
  const groups = {};
  questions.forEach((q) => {
    if (!groups[q.section]) groups[q.section] = [];
    groups[q.section].push(q);
  });

  const sections = Object.entries(groups);
  return sections.map(([section, items]) => {
    const cards = items.map((q, idx) => `
      <div class="card mb-2 question-card" data-section="${section}">
        <div class="card-body">
          <h6>${q.question}</h6>
          ${['a', 'b', 'c', 'd'].map((opt) => `
            <div class="form-check">
              <input
                class="form-check-input"
                type="radio"
                name="q_${q.id}"
                id="q_${q.id}_${opt}"
                value="${opt}"
                data-score="${q[`score_${opt}`]}"
                data-section="${section}"
                required
              >
              <label class="form-check-label" for="q_${q.id}_${opt}">${q[`option_${opt}`]}</label>
            </div>
          `).join('')}
        </div>
      </div>
    `).join('');

    return `
      <div class="mb-3">
        <h5>${section}</h5>
        ${cards}
      </div>
    `;
  }).join('');
}

function updateProgress() {
  const cards = document.querySelectorAll('.question-card');
  const answered = Array.from(cards).filter((card) => card.querySelector('input[type="radio"]:checked')).length;
  const percent = cards.length ? Math.round((answered / cards.length) * 100) : 0;
  document.getElementById('progressBar').style.width = `${percent}%`;
  document.getElementById('progressText').innerText = `${percent}%`;

  const sectionScores = {};
  document.querySelectorAll('input[type="radio"]:checked').forEach((input) => {
    const section = input.dataset.section || 'General';
    const score = Number(input.dataset.score || 0);
    sectionScores[section] = (sectionScores[section] || 0) + score;
  });

  const summary = document.getElementById('sectionSummary');
  const body = document.getElementById('sectionSummaryBody');
  const entries = Object.entries(sectionScores);
  if (entries.length > 0) {
    body.innerHTML = entries.map(([section, score]) => `<div><strong>${section}</strong>: ${score}</div>`).join('');
    summary.classList.remove('d-none');
  } else {
    body.innerHTML = '';
    summary.classList.add('d-none');
  }
}

async function loadQuestions() {
  try {
    const questions = await fetchJson('/assessment/questions');
    const container = document.getElementById('assessmentForm');
    container.innerHTML = groupedQuestionsMarkup(questions);
    container.querySelectorAll('input[type="radio"]').forEach((item) => item.addEventListener('change', updateProgress));
  } catch (err) {
    document.getElementById('assessmentForm').innerHTML = `<div class="alert alert-danger">${err.message}</div>`;
  }
}

async function loadSelectors() {
  try {
    const clinics = await fetchJson('/clinics');
    fillSelect('assessmentClinicId', clinics, 'id', (x) => x.name, 'Select clinic');

    const existingPatientGroup = document.getElementById('existingPatientGroup');
    const publicAssessmentFields = document.getElementById('publicAssessmentFields');
    if (hasAuth) {
      const patients = await fetchJson('/patients');
      fillSelect('assessmentPatientId', patients, 'id', (x) => `${x.child_name} - Parent: ${x.parent_name}`, 'Select patient');
      existingPatientGroup.classList.remove('d-none');
      publicAssessmentFields.classList.add('d-none');
    } else {
      existingPatientGroup.classList.add('d-none');
      publicAssessmentFields.classList.remove('d-none');
    }
  } catch (err) {
    setMessage(`Failed to load assessment selectors: ${err.message}`);
  }
}

async function submitAssessment() {
  const clinicId = Number(document.getElementById('assessmentClinicId').value);
  const patientId = Number(document.getElementById('assessmentPatientId').value);
  const parentName = document.getElementById('assessmentParentName').value.trim();
  const childName = document.getElementById('assessmentChildName').value.trim();
  const childAge = Number(document.getElementById('assessmentChildAge').value);
  const email = document.getElementById('assessmentEmail').value.trim();
  const phone = document.getElementById('assessmentPhone').value.trim();

  if (!clinicId) {
    setMessage('Please select clinic.');
    return;
  }
  if (hasAuth && !patientId) {
    setMessage('Please select patient.');
    return;
  }
  if (!hasAuth && (!parentName || !childName || !childAge || !email || !phone)) {
    setMessage('Please complete the parent and child details.');
    return;
  }

  const cards = document.querySelectorAll('.question-card');
  const answers = [];
  for (const card of cards) {
    const checked = card.querySelector('input[type="radio"]:checked');
    if (!checked) {
      setMessage('Please answer all questions.');
      return;
    }
    answers.push({ question_id: Number(checked.name.split('_')[1]), selected_option: checked.value });
  }

  try {
    const data = await fetchJson('/assessment/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: hasAuth ? patientId : null,
        clinic_id: clinicId,
        answers,
        parent_name: hasAuth ? null : parentName,
        child_name: hasAuth ? null : childName,
        child_age: hasAuth ? null : childAge,
        email: hasAuth ? null : email,
        phone: hasAuth ? null : phone,
      }),
    });

    if (data.section_scores) {
      sessionStorage.setItem(`assessment_section_scores_${data.id}`, JSON.stringify(data.section_scores));
    }
    window.location.href = `/assessment/result/${data.id}`;
  } catch (err) {
    setMessage(err.message || 'Submission failed');
  }
}

document.getElementById('submitAssessment').addEventListener('click', submitAssessment);
loadSelectors();
loadQuestions();
