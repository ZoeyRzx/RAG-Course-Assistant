import { appConfig } from "./config.js";
import { askQuestion, listDocuments, uploadDocument } from "./api/client.js";

const pipelineStages = [
  "Parse PDF",
  "Chunk Text",
  "Create Embeddings",
  "Index in Vector DB",
];

const state = {
  documents: [],
  currentResult: null,
  selectedCitationId: null,
  preferences: {
    answerLanguage: "auto",
    englishTerms: true,
  },
};

const els = {
  backendEndpoint: document.querySelector("#backend-endpoint"),
  askButton: document.querySelector("#ask-button"),
  questionInput: document.querySelector("#question-input"),
  answerLanguage: document.querySelector("#answer-language"),
  englishTerms: document.querySelector("#english-terms"),
  uploadForm: document.querySelector("#upload-form"),
  pdfInput: document.querySelector("#pdf-input"),
  pickFilesBtn: document.querySelector("#pick-files-btn"),
  fileSummary: document.querySelector("#file-summary"),
  pipelineList: document.querySelector("#pipeline-list"),
  ingestProgress: document.querySelector("#ingest-progress"),
  documentList: document.querySelector("#document-list"),
  docCount: document.querySelector("#doc-count"),
  directAnswer: document.querySelector("#direct-answer"),
  ragAnswer: document.querySelector("#rag-answer"),
  citationList: document.querySelector("#citation-list"),
  citationDetail: document.querySelector("#citation-detail"),
  directLatency: document.querySelector("#direct-latency"),
  ragLatency: document.querySelector("#rag-latency"),
  metricsGrid: document.querySelector("#metrics-grid"),
  questionId: document.querySelector("#question-id"),
};

function init() {
  bindEvents();
  updateFileSummary();
  renderRuntimeState();
  renderPipeline(0);
  renderMetrics(null);
  refreshDocuments();
}

function bindEvents() {
  els.answerLanguage.addEventListener("change", (event) => {
    state.preferences.answerLanguage = event.target.value;
  });

  els.englishTerms.addEventListener("change", (event) => {
    state.preferences.englishTerms = Boolean(event.target.checked);
  });

  els.askButton.addEventListener("click", askCurrentQuestion);

  els.uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const files = Array.from(els.pdfInput.files || []);
    if (!files.length) {
      return;
    }
    await handleBatchUpload(files);
  });

  els.pickFilesBtn.addEventListener("click", () => {
    els.pdfInput.click();
  });

  els.pdfInput.addEventListener("change", () => {
    updateFileSummary();
  });

  els.citationList.addEventListener("click", (event) => {
    const card = event.target.closest("[data-cite-id]");
    if (!card) {
      return;
    }
    selectCitation(Number(card.dataset.citeId));
  });

  els.ragAnswer.addEventListener("click", (event) => {
    const button = event.target.closest(".inline-cite");
    if (!button) {
      return;
    }
    selectCitation(Number(button.dataset.cite));
  });
}

function renderRuntimeState() {
  els.backendEndpoint.textContent = `Backend: ${appConfig.apiBaseUrl}`;
}

function renderPipeline(progress) {
  const stageCount = pipelineStages.length;
  const chunk = 100 / stageCount;
  const activeIndex = progress >= 100 ? stageCount : Math.floor(progress / chunk);

  els.pipelineList.innerHTML = pipelineStages
    .map((name, index) => {
      const className =
        index < activeIndex
          ? "done"
          : index === activeIndex && progress < 100
          ? "active"
          : "";
      return `<li class="${className}">${name}</li>`;
    })
    .join("");

  els.ingestProgress.style.width = `${Math.max(0, Math.min(100, progress))}%`;
}

async function refreshDocuments() {
  try {
    const docs = await listDocuments();
    state.documents = docs;
    renderDocuments();
  } catch (error) {
    els.documentList.innerHTML = `<li class="document-item">Failed to load documents: ${escapeHtml(
      error.message
    )}</li>`;
  }
}

function renderDocuments() {
  if (!state.documents.length) {
    els.docCount.textContent = "0 docs";
    els.documentList.innerHTML =
      '<li class="document-item">No documents yet. Upload course PDFs first.</li>';
    return;
  }

  els.docCount.textContent = `${state.documents.length} docs`;
  els.documentList.innerHTML = state.documents
    .map(
      (doc) => `<li class="document-item">
      <div class="document-name">${escapeHtml(doc.name)}</div>
      <div class="meta-row">Pages: ${doc.pages} | Chunks: ${doc.chunks}</div>
      <div class="meta-row">Status: ${escapeHtml(doc.status)} | Updated: ${escapeHtml(
        doc.createdAt || "-"
      )}</div>
    </li>`
    )
    .join("");
}

async function handleBatchUpload(files) {
  renderPipeline(0);
  els.uploadForm.classList.add("loading");
  try {
    const total = files.length;
    for (let index = 0; index < total; index += 1) {
      const file = files[index];
      await uploadDocument(file, (singleProgress) => {
        const overall = ((index + singleProgress / 100) / total) * 100;
        renderPipeline(overall);
      });
    }
    renderPipeline(100);
    els.pdfInput.value = "";
    updateFileSummary();
    await refreshDocuments();
  } catch (error) {
    renderPipeline(0);
    els.documentList.innerHTML =
      `<li class="document-item">Upload failed: ${escapeHtml(error.message)}</li>` +
      els.documentList.innerHTML;
  } finally {
    els.uploadForm.classList.remove("loading");
  }
}

function updateFileSummary() {
  const files = Array.from(els.pdfInput.files || []);
  if (!files.length) {
    els.fileSummary.textContent = "No files selected";
    return;
  }
  if (files.length === 1) {
    els.fileSummary.textContent = files[0].name;
    return;
  }
  els.fileSummary.textContent = `${files.length} files selected`;
}

async function askCurrentQuestion() {
  if (els.askButton.disabled) {
    return;
  }
  const question = els.questionInput.value.trim();
  if (!question) {
    return;
  }

  els.askButton.disabled = true;
  els.askButton.textContent = "Generating...";
  els.directAnswer.classList.add("loading");
  els.ragAnswer.classList.add("loading");
  els.directAnswer.classList.remove("empty");
  els.ragAnswer.classList.remove("empty");
  els.directAnswer.textContent = "Direct LLM is generating...";
  els.ragAnswer.textContent = "RAG is retrieving and generating...";
  els.citationList.innerHTML = "";
  els.citationDetail.textContent = "Waiting for retrieval...";
  els.citationDetail.classList.add("empty");

  try {
    const result = await askQuestion(question, state.preferences);
    state.currentResult = result;
    const citations = result.citations || [];
    state.selectedCitationId = citations[0]?.id || null;

    await Promise.all([
      typeText(els.directAnswer, result.directAnswer || ""),
      typeText(els.ragAnswer, result.ragAnswer || ""),
    ]);

    renderRagAnswerWithCitations(result.ragAnswer || "");
    renderCitationList();
    renderCitationDetail();
    renderMetrics(result.metrics);

    els.questionId.textContent = result.questionId || "-";
    const directMs = result.runtime?.directMs ?? "-";
    const ragMs = result.runtime?.ragMs ?? "-";
    els.directLatency.textContent = `${directMs}ms`;
    els.ragLatency.textContent = `${ragMs}ms`;
  } catch (error) {
    const message = `Request failed: ${error.message}`;
    els.directAnswer.textContent = message;
    els.ragAnswer.textContent = message;
  } finally {
    els.askButton.disabled = false;
    els.askButton.textContent = "Run Comparison";
    els.directAnswer.classList.remove("loading");
    els.ragAnswer.classList.remove("loading");
  }
}

function typeText(target, text) {
  return new Promise((resolve) => {
    target.textContent = "";
    let index = 0;
    const timer = setInterval(() => {
      index += 2;
      target.textContent = text.slice(0, index);
      if (index >= text.length) {
        clearInterval(timer);
        resolve();
      }
    }, 8);
  });
}

function renderRagAnswerWithCitations(answer) {
  const html = escapeHtml(answer).replace(/\[(\d+)\]/g, (_, id) => {
    return `<button type="button" class="inline-cite" data-cite="${id}">[${id}]</button>`;
  });
  els.ragAnswer.innerHTML = html;
  highlightSelectedCitation();
}

function renderCitationList() {
  const citations = state.currentResult?.citations || [];
  if (!citations.length) {
    els.citationList.innerHTML = '<li class="citation-item">No citations returned.</li>';
    return;
  }

  els.citationList.innerHTML = citations
    .map((item) => {
      const active = state.selectedCitationId === item.id ? "active" : "";
      return `<li class="citation-item ${active}" data-cite-id="${item.id}">
          <div>${item.id}. ${escapeHtml(item.title)} (p.${item.page})</div>
          <div class="meta-row">Similarity <span class="citation-score">${(
            item.score * 100
          ).toFixed(0)}%</span></div>
        </li>`;
    })
    .join("");
}

function renderCitationDetail() {
  const citations = state.currentResult?.citations || [];
  if (!citations.length) {
    els.citationDetail.textContent = "No citation evidence for the current answer.";
    els.citationDetail.classList.add("empty");
    return;
  }

  const selected =
    citations.find((item) => item.id === state.selectedCitationId) || citations[0];
  els.citationDetail.classList.remove("empty");
  els.citationDetail.innerHTML = `<strong>${selected.id}. ${escapeHtml(
    selected.title
  )} - Page ${selected.page}</strong><br/>${escapeHtml(selected.text)}`;
}

function highlightSelectedCitation() {
  const buttons = els.ragAnswer.querySelectorAll(".inline-cite");
  buttons.forEach((button) => {
    const active = Number(button.dataset.cite) === state.selectedCitationId;
    button.classList.toggle("active", active);
  });
}

function selectCitation(id) {
  state.selectedCitationId = id;
  renderCitationList();
  renderCitationDetail();
  highlightSelectedCitation();
}

function renderMetrics(metrics) {
  const safeMetrics = metrics || {
    correctness: { direct: 0, rag: 0 },
    citationHitRate: { direct: 0, rag: 0 },
  };

  const cards = [
    {
      title: "Answer Correctness",
      key: "correctness",
      max: 1,
      formatter: (value) => `${Math.round(value * 100)}%`,
    },
    {
      title: "Citation Hit Rate",
      key: "citationHitRate",
      max: 1,
      formatter: (value) => `${Math.round(value * 100)}%`,
    },
  ];

  els.metricsGrid.innerHTML = cards
    .map((card) => {
      const metric = safeMetrics[card.key] || { direct: 0, rag: 0 };
      const directWidth = Math.max(0, Math.min(100, (metric.direct / card.max) * 100));
      const ragWidth = Math.max(0, Math.min(100, (metric.rag / card.max) * 100));
      return `<article class="metric-card">
        <div class="metric-title">${card.title}</div>
        <div class="bar-group">
          <div class="bar-row">
            <span>Direct</span>
            <div class="bar-track"><div class="bar-fill direct" style="width:${directWidth}%"></div></div>
            <span>${card.formatter(metric.direct)}</span>
          </div>
          <div class="bar-row">
            <span>RAG</span>
            <div class="bar-track"><div class="bar-fill rag" style="width:${ragWidth}%"></div></div>
            <span>${card.formatter(metric.rag)}</span>
          </div>
        </div>
      </article>`;
    })
    .join("");
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

init();
