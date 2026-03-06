"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const state = {
    questions: [],
    responses: {},
    currentIndex: 0,
    intake: {},
  };

  const els = {
    name: document.getElementById("name"),
    respondentName: document.getElementById("respondent_name"),
    respondentRole: document.getElementById("respondent_role"),
    respondentEmail: document.getElementById("respondent_email"),
    childAgeMonths: document.getElementById("child_age_months"),
    startBtn: document.getElementById("startBtn"),
    intakeError: document.getElementById("intakeError"),
    questionnaireState: document.getElementById("questionnaireState"),
    questionnaireContent: document.getElementById("questionnaireContent"),
    questionCounter: document.getElementById("questionCounter"),
    questionCategory: document.getElementById("questionCategory"),
    progressBar: document.getElementById("progressBar"),
    questionText: document.getElementById("questionText"),
    optionsContainer: document.getElementById("optionsContainer"),
    prevBtn: document.getElementById("prevBtn"),
    nextBtn: document.getElementById("nextBtn"),
    submitBtn: document.getElementById("submitBtn"),
    questionError: document.getElementById("questionError"),
    reportPanel: document.getElementById("reportPanel"),
    assessmentId: document.getElementById("assessmentId"),
    totalScore: document.getElementById("totalScore"),
    riskBadge: document.getElementById("riskBadge"),
    categoryScores: document.getElementById("categoryScores"),
    recommendationText: document.getElementById("recommendationText"),
    uiStatus: document.getElementById("uiStatus"),
  };

  const required = [
    "startBtn", "nextBtn", "prevBtn", "submitBtn", "optionsContainer", "questionnaireContent",
    "questionnaireState", "uiStatus", "questionError", "intakeError",
  ];
  for (const key of required) {
    if (!els[key]) {
      return;
    }
  }

  function setStatus(text) {
    if (els.uiStatus) {
      els.uiStatus.textContent = text;
    }
  }

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      return parts.pop().split(";").shift();
    }
    return "";
  }

  function showError(el, message) {
    el.textContent = message;
    el.classList.remove("hidden");
  }

  function hideError(el) {
    el.textContent = "";
    el.classList.add("hidden");
  }

  function getIntakePayload() {
    const parsedAge = els.childAgeMonths.value ? Number(els.childAgeMonths.value) : null;
    return {
      name: (els.name.value || "").trim() || "Child Screening",
      respondent_name: (els.respondentName.value || "").trim(),
      respondent_role: (els.respondentRole.value || "").trim(),
      respondent_email: (els.respondentEmail.value || "").trim(),
      child_age_months: Number.isFinite(parsedAge) ? parsedAge : null,
    };
  }

  function mapRiskClass(riskLevel) {
    const lower = (riskLevel || "").toLowerCase();
    if (lower === "low") return "risk-low";
    if (lower === "mild") return "risk-mild";
    if (lower === "moderate") return "risk-moderate";
    if (lower === "high") return "risk-high";
    return "";
  }

  function renderReport(report) {
    els.assessmentId.textContent = report.assessment_id;
    els.totalScore.textContent = report.score;
    els.riskBadge.textContent = report.risk_level;
    els.riskBadge.className = `risk-badge ${mapRiskClass(report.risk_level)}`;
    els.recommendationText.textContent = report.recommendation;

    const entries = Object.entries(report.category_scores || {});
    const maxScore = Math.max(1, ...entries.map(([, score]) => score));
    els.categoryScores.innerHTML = "";

    entries.forEach(([name, score]) => {
      const width = Math.round((score / maxScore) * 100);
      const item = document.createElement("div");
      item.className = "category-score-item";
      item.innerHTML = `
        <div class="category-score-meta">
          <span>${name}</span>
          <span>${score}</span>
        </div>
        <div class="category-track">
          <div class="category-fill" style="width: ${width}%"></div>
        </div>
      `;
      els.categoryScores.appendChild(item);
    });

    els.reportPanel.classList.remove("hidden");
    els.reportPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderQuestion() {
    hideError(els.questionError);
    const current = state.questions[state.currentIndex];
    if (!current) {
      showError(els.questionError, "No question available.");
      return;
    }

    const total = state.questions.length;
    els.questionCounter.textContent = `Question ${state.currentIndex + 1} / ${total}`;
    els.questionCategory.textContent = current.category;
    els.questionText.textContent = current.text;
    els.progressBar.style.width = `${((state.currentIndex + 1) / total) * 100}%`;

    els.optionsContainer.innerHTML = "";
    current.options.forEach((option) => {
      const label = document.createElement("label");
      label.className = "option-card";
      label.innerHTML = `
        <input type="radio" name="question-option" value="${option.id}">
        <span>${option.text} <strong>(score ${option.score})</strong></span>
      `;

      const radio = label.querySelector("input");
      if (state.responses[current.id] === option.id) {
        radio.checked = true;
      }
      radio.addEventListener("change", () => {
        state.responses[current.id] = option.id;
        hideError(els.questionError);
      });
      els.optionsContainer.appendChild(label);
    });

    const isFirst = state.currentIndex === 0;
    const isLast = state.currentIndex === total - 1;
    els.prevBtn.disabled = isFirst;
    els.nextBtn.classList.toggle("hidden", isLast);
    els.submitBtn.classList.toggle("hidden", !isLast);
  }

  function validateCurrentAnswer() {
    const current = state.questions[state.currentIndex];
    if (!current || !state.responses[current.id]) {
      showError(els.questionError, "Select an answer to continue.");
      return false;
    }
    return true;
  }

  async function loadQuestions() {
    hideError(els.intakeError);
    hideError(els.questionError);
    setStatus("Loading questions...");

    state.intake = getIntakePayload();
    let url = "/api/questions/";
    if (Number.isInteger(state.intake.child_age_months)) {
      url += `?child_age_months=${state.intake.child_age_months}`;
    }

    els.startBtn.disabled = true;
    els.startBtn.textContent = "Loading...";
    try {
      const response = await fetch(url, {
        method: "GET",
        headers: { "Accept": "application/json" },
      });

      const text = await response.text();
      let questions = [];
      try {
        questions = JSON.parse(text);
      } catch (_error) {
        throw new Error("Questions endpoint did not return JSON.");
      }

      if (!response.ok) {
        throw new Error(`Failed to load questions (${response.status}).`);
      }
      if (!Array.isArray(questions) || questions.length === 0) {
        throw new Error("No questions found. Seed questions or verify filters.");
      }

      state.questions = questions;
      state.responses = {};
      state.currentIndex = 0;

      els.questionnaireState.classList.add("hidden");
      els.questionnaireContent.classList.remove("hidden");
      els.reportPanel.classList.add("hidden");
      renderQuestion();
      setStatus(`Loaded ${questions.length} questions.`);
    } catch (error) {
      showError(els.intakeError, error.message || "Unable to load questionnaire.");
      setStatus("Question load failed.");
    } finally {
      els.startBtn.disabled = false;
      els.startBtn.textContent = "Start Questionnaire";
    }
  }

  async function submitAssessment() {
    if (!validateCurrentAnswer()) {
      return;
    }

    const responses = state.questions.map((q) => ({
      question_id: q.id,
      option_id: state.responses[q.id],
    }));
    if (responses.some((r) => !r.option_id)) {
      showError(els.questionError, "Answer all questions before submitting.");
      return;
    }

    const payload = {
      ...state.intake,
      metadata: {
        source: "web_gui",
        submitted_at: new Date().toISOString(),
      },
      responses,
    };

    els.submitBtn.disabled = true;
    els.submitBtn.textContent = "Submitting...";
    setStatus("Submitting assessment...");
    hideError(els.questionError);

    try {
      const response = await fetch("/api/submit-assessment/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify(payload),
      });

      const text = await response.text();
      let report = {};
      try {
        report = JSON.parse(text);
      } catch (_error) {
        throw new Error("Submit endpoint did not return JSON.");
      }

      if (!response.ok) {
        throw new Error(typeof report === "object" ? JSON.stringify(report) : "Submit failed.");
      }

      renderReport(report);
      setStatus(`Assessment submitted. ID #${report.assessment_id}`);
    } catch (error) {
      showError(els.questionError, error.message || "Submit failed.");
      setStatus("Submission failed.");
    } finally {
      els.submitBtn.disabled = false;
      els.submitBtn.textContent = "Submit Assessment";
    }
  }

  function goNext() {
    if (!validateCurrentAnswer()) {
      return;
    }
    if (state.currentIndex < state.questions.length - 1) {
      state.currentIndex += 1;
      renderQuestion();
      setStatus(`Moved to question ${state.currentIndex + 1}.`);
    }
  }

  function goPrev() {
    if (state.currentIndex > 0) {
      state.currentIndex -= 1;
      renderQuestion();
      setStatus(`Moved to question ${state.currentIndex + 1}.`);
    }
  }

  els.startBtn.addEventListener("click", loadQuestions);
  els.nextBtn.addEventListener("click", goNext);
  els.prevBtn.addEventListener("click", goPrev);
  els.submitBtn.addEventListener("click", submitAssessment);
  setStatus("Ready");
});
