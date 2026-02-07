function $(id) {
  return document.getElementById(id);
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "request_failed");
  }
  return data;
}

function initForm() {
  const form = $("load-form");
  if (!form) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const directory = $("directory-input").value.trim();
    const recursive = form.querySelector("input[name='recursive']").checked;
    const maxWorkers = parseInt($("max-workers").value, 10);

    const errorEl = $("form-error");
    errorEl.classList.add("hidden");

    try {
      const data = await postJson("/api/load", {
        directory,
        recursive,
        max_workers: maxWorkers,
      });
      window.location.href = `/loading/${data.task_id}`;
    } catch (error) {
      errorEl.textContent = `Error: ${error.message}`;
      errorEl.classList.remove("hidden");
    }
  });
}

function renderActivity(list) {
  const activity = $("activity-list");
  if (!activity) return;
  activity.innerHTML = "";
  if (!list || list.length === 0) {
    const empty = document.createElement("li");
    empty.textContent = "No activity yet.";
    activity.appendChild(empty);
    return;
  }

  list.slice().reverse().forEach((item) => {
    const li = document.createElement("li");
    const eventLabel = item.event === "loaded" ? "[ok]" : "[warn]";
    const message = item.message ? ` (${item.message})` : "";
    li.textContent = `${eventLabel} ${item.path}${message}`;
    activity.appendChild(li);
  });
}

async function pollStatus(taskId) {
  const progressFill = $("progress-fill");
  const progressMeta = $("progress-meta");
  const currentFile = $("current-file");
  const loadedCount = $("loaded-count");
  const failedCount = $("failed-count");
  const errorEl = $("loading-error");

  async function tick() {
    try {
      const response = await fetch(`/api/status/${taskId}`);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "status_failed");
      }

      const current = data.progress?.current ?? 0;
      const total = data.progress?.total ?? 0;
      const percent = total > 0 ? Math.round((current / total) * 100) : 0;

      if (progressFill) {
        progressFill.style.width = `${percent}%`;
      }
      if (progressMeta) {
        progressMeta.textContent = `${current} / ${total} files`;
      }
      if (currentFile) {
        currentFile.textContent = data.current_file || "--";
      }
      if (loadedCount) {
        loadedCount.textContent = data.loaded ?? 0;
      }
      if (failedCount) {
        failedCount.textContent = data.failed ?? 0;
      }

      renderActivity(data.recent || []);

      if (data.status === "complete") {
        window.location.href = `/results/${taskId}`;
        return;
      }
      if (data.status === "failed") {
        errorEl.textContent = "Loading failed. Check logs for details.";
        errorEl.classList.remove("hidden");
        return;
      }

      setTimeout(tick, 1000);
    } catch (error) {
      if (errorEl) {
        errorEl.textContent = `Error: ${error.message}`;
        errorEl.classList.remove("hidden");
      }
      setTimeout(tick, 1500);
    }
  }

  tick();
}

function renderResults(taskId) {
  const summaryBlock = $("summary-block");
  const documentsList = $("documents-list");
  const errorsList = $("errors-list");
  const downloadLink = $("download-json");
  const showAllButton = $("show-all");

  async function loadResults() {
    const response = await fetch(`/api/results/${taskId}`);
    const data = await response.json();
    if (!response.ok) {
      return;
    }

    const stats = data.stats || {};
    const total = stats.total_files ?? 0;
    const loaded = stats.loaded ?? 0;
    const failed = stats.failed ?? 0;
    const duration = stats.duration_seconds ?? 0;

    if (summaryBlock) {
      summaryBlock.innerHTML = `
        <div class="status-grid">
          <div><p class="label">Total Files Found</p><p class="value">${total}</p></div>
          <div><p class="label">Successfully Loaded</p><p class="value">${loaded}</p></div>
          <div><p class="label">Failed/Skipped</p><p class="value">${failed}</p></div>
          <div><p class="label">Processing Time</p><p class="value">${duration}s</p></div>
        </div>
      `;
    }

    if (downloadLink) {
      downloadLink.href = `/api/download/${taskId}`;
    }

    const previews = data.previews || [];
    let limit = 10;

    function renderDocs() {
      if (!documentsList) return;
      documentsList.innerHTML = "";
      const display = previews.slice(0, limit);
      display.forEach((doc, index) => {
        const card = document.createElement("div");
        card.className = "document-card";
        card.innerHTML = `
          <h3>${index + 1}. ${doc.source || "unknown"}</h3>
          <p class="document-meta">Size: ${doc.size_bytes || 0} bytes | Modified: ${doc.modified_at || ""}</p>
          <p class="document-preview">${doc.preview || ""}</p>
        `;
        documentsList.appendChild(card);
      });
    }

    renderDocs();

    if (showAllButton) {
      showAllButton.addEventListener("click", () => {
        limit = previews.length;
        renderDocs();
        showAllButton.disabled = true;
      });
    }

    if (errorsList) {
      errorsList.innerHTML = "";
      const errors = data.errors || [];
      if (errors.length === 0) {
        const li = document.createElement("li");
        li.textContent = "No errors reported.";
        errorsList.appendChild(li);
      } else {
        errors.forEach((error) => {
          const li = document.createElement("li");
          const reason = error.reason ? ` - ${error.reason}` : "";
          const message = error.error ? ` (${error.error})` : "";
          li.textContent = `${error.path}${reason}${message}`;
          errorsList.appendChild(li);
        });
      }
    }
  }

  loadResults();
}

function initPage() {
  initForm();

  const taskId = document.body.dataset.taskId;
  if (!taskId) return;

  if (window.location.pathname.startsWith("/loading")) {
    pollStatus(taskId);
  }

  if (window.location.pathname.startsWith("/results")) {
    renderResults(taskId);
  }
}

window.addEventListener("DOMContentLoaded", initPage);
