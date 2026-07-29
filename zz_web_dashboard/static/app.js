const logEl = document.querySelector("#log");
const supervisedRows = document.querySelector("#supervisedRows");
const unsupervisedRows = document.querySelector("#unsupervisedRows");
const liveRows = document.querySelector("#liveRows");
let livePollTimer = null;

function log(message, data = null) {
  const stamp = new Date().toLocaleTimeString();
  const detail = data ? `\n${JSON.stringify(data, null, 2)}` : "";
  logEl.textContent = `[${stamp}] ${message}${detail}\n\n${logEl.textContent}`;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

function setLoading(button, loading) {
  button.disabled = loading;
  button.dataset.originalText ||= button.textContent;
  button.textContent = loading ? "Working" : button.dataset.originalText;
}

function totalFiles(counts) {
  return Object.values(counts || {}).reduce((sum, value) => sum + Number(value), 0);
}

function valueOrDash(value) {
  return value === null || value === undefined || value === "" ? "-" : value;
}

function percent(value) {
  return value === null || value === undefined ? "-" : `${Math.round(Number(value) * 100)}%`;
}

function meters(value) {
  return value === null || value === undefined ? "-" : `${Number(value).toFixed(2)} m`;
}

function speed(value) {
  return value === null || value === undefined ? "-" : `${Number(value).toFixed(3)} m/s`;
}

function renderRows(target, rows, columns) {
  target.innerHTML = "";
  if (!rows || rows.length === 0) {
    target.innerHTML = `<tr><td colspan="${columns.length}">No results yet</td></tr>`;
    return;
  }
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = columns.map((column) => `<td>${formatCell(row[column])}</td>`).join("");
    target.appendChild(tr);
  }
}

function renderPlots(plots = {}) {
  const cacheBust = `?v=${Date.now()}`;
  const mapping = {
    accuracyPlot: plots.supervised_accuracy,
    f1Plot: plots.supervised_macro_f1,
    unsupervisedPlot: plots.unsupervised_ari,
    confusionPlot: plots.best_confusion_matrix,
  };
  for (const [id, path] of Object.entries(mapping)) {
    const image = document.querySelector(`#${id}`);
    if (path) {
      image.src = `/${path}${cacheBust}`;
      image.closest("figure").style.display = "block";
    } else {
      image.removeAttribute("src");
      image.closest("figure").style.display = "none";
    }
  }
}

function currentWithUltrasonicFallback(state) {
  const current = state.current || {};
  const ultrasonic = state.last_ultrasonic || {};
  return {
    ...current,
    distance_m: current.distance_m ?? ultrasonic.distance_m,
    ultrasonic_speed_mps: current.ultrasonic_speed_mps ?? ultrasonic.ultrasonic_speed_mps,
    motion: current.motion ?? ultrasonic.motion,
    presence: current.presence ?? ultrasonic.presence,
  };
}

function updatePresenceMap(current) {
  const scope = document.querySelector("#radarScope");
  const dot = document.querySelector("#objectDot");
  const mapState = document.querySelector("#mapState");
  const mapDetail = document.querySelector("#mapDetail");
  const present = Boolean(current.presence) || Number(current.distance_m) > 0;
  const distance = Number(current.distance_m || 0);
  const maxDistance = 3.5;
  const clamped = Math.max(0, Math.min(distance, maxDistance));
  const radius = 48 + (clamped / maxDistance) * 88;
  const motion = String(current.motion || "Unknown").toLowerCase();
  const angle = motion.includes("approach") ? -90 : motion.includes("reced") ? 45 : -20;
  const radians = (angle * Math.PI) / 180;
  const x = Math.cos(radians) * radius;
  const y = Math.sin(radians) * radius;

  scope.classList.toggle("has-object", present);
  scope.classList.toggle("no-object", !present);
  dot.style.transform = present ? `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))` : "translate(-50%, -50%)";
  mapState.textContent = present ? "Object present" : "No object";
  mapDetail.textContent = present
    ? `${meters(distance)} • ${valueOrDash(current.motion)}`
    : "Waiting for ultrasonic confirmation";
}

function renderLive(state) {
  const current = currentWithUltrasonicFallback(state);
  const radarSpeed = current.radar_speed_mps ?? current.speed_mps;
  document.querySelector("#liveStatus").textContent = state.error || state.status || "Idle";
  document.querySelector("#livePresence").textContent = current.presence === undefined ? "-" : current.presence ? "Present" : "No object";
  document.querySelector("#liveClass").textContent = current.class || "-";
  document.querySelector("#liveConfidence").textContent = percent(current.confidence);
  document.querySelector("#liveDistance").textContent = meters(current.distance_m);
  document.querySelector("#liveUltrasonicSpeed").textContent = speed(current.ultrasonic_speed_mps);
  document.querySelector("#liveRadarSpeed").textContent = speed(radarSpeed);
  document.querySelector("#liveMotion").textContent = valueOrDash(current.motion);
  document.querySelector("#liveSamples").textContent = String(state.samples_seen || 0);
  updatePresenceMap(current);

  liveRows.innerHTML = "";
  const history = state.history || [];
  if (history.length === 0) {
    liveRows.innerHTML = `<tr><td colspan="9">No live results yet</td></tr>`;
    return;
  }
  for (const item of history) {
    const tr = document.createElement("tr");
    const itemRadarSpeed = item.radar_speed_mps ?? item.speed_mps;
    tr.innerHTML = `
      <td>${item.time || "-"}</td>
      <td>${item.presence === undefined ? "-" : item.presence ? "Present" : "No object"}</td>
      <td>${item.class || "-"}</td>
      <td>${percent(item.confidence)}</td>
      <td>${meters(item.distance_m)}</td>
      <td>${speed(item.ultrasonic_speed_mps)}</td>
      <td>${speed(itemRadarSpeed)}</td>
      <td>${valueOrDash(item.motion)}</td>
      <td>${item.source || item.mode || "-"}</td>
    `;
    liveRows.appendChild(tr);
  }
}

function formatCell(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  const number = Number(value);
  if (!Number.isNaN(number) && String(value).trim() !== "") return number.toFixed(3);
  return String(value);
}

async function refreshStatus() {
  const data = await api("/api/status");
  const envOk = Object.values(data.environment).every(Boolean);
  document.querySelector("#envStatus").textContent = envOk ? "Ready" : "Missing packages";
  document.querySelector("#modelStatus").textContent = data.model?.model_name || "No model";
  document.querySelector("#realCount").textContent = `${totalFiles(data.datasets.dataset)} files`;
  document.querySelector("#simCount").textContent = `${totalFiles(data.datasets.dataset_simulated)} files`;
  renderPlots(data.summary?.plots || {});
  log("Status refreshed", data.summary || {});
}

async function refreshLiveStatus() {
  const state = await api("/api/live/status");
  renderLive(state);
  if (!state.running && livePollTimer) {
    clearInterval(livePollTimer);
    livePollTimer = null;
  }
  return state;
}

function ensureLivePolling() {
  if (livePollTimer) return;
  livePollTimer = setInterval(() => refreshLiveStatus().catch((error) => log(error.message)), 1000);
}

async function loadResults() {
  const data = await api("/api/results");
  renderRows(supervisedRows, data.supervised, ["model", "cv_accuracy_mean", "test_accuracy", "macro_f1"]);
  renderRows(unsupervisedRows, data.unsupervised, ["model", "adjusted_rand", "normalized_mutual_info", "clusters_found"]);
  renderPlots(data.summary?.plots || {});
}

async function loadRecordings() {
  const dataset = document.querySelector("#recordingDataset").value;
  const data = await api(`/api/recordings?dataset=${encodeURIComponent(dataset)}`);
  const select = document.querySelector("#recordingSelect");
  select.innerHTML = "";
  for (const recording of data.recordings) {
    const option = document.createElement("option");
    option.value = recording.path;
    option.textContent = `${recording.label} / ${recording.name}`;
    select.appendChild(option);
  }
  if (data.recordings.length === 0) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No recordings found";
    select.appendChild(option);
  }
}

document.querySelector("#refreshStatus").addEventListener("click", () => refreshStatus().catch((error) => log(error.message)));

document.querySelector("#simulateBtn").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  setLoading(button, true);
  try {
    const data = await api("/api/simulate", {
      method: "POST",
      body: JSON.stringify({
        recordings_per_class: Number(document.querySelector("#simRecordings").value),
        seconds: Number(document.querySelector("#simSeconds").value),
        seed: Number(document.querySelector("#simSeed").value),
        out_dir: document.querySelector("#simOut").value,
      }),
    });
    log("Simulation complete", data);
    await refreshStatus();
    await loadRecordings();
  } catch (error) {
    log(error.message);
  } finally {
    setLoading(button, false);
  }
});

document.querySelector("#compareBtn").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  setLoading(button, true);
  try {
    const data = await api("/api/compare", {
      method: "POST",
      body: JSON.stringify({
        dataset: document.querySelector("#compareDataset").value,
        test_size: Number(document.querySelector("#testSize").value),
      }),
    });
    renderRows(supervisedRows, data.supervised, ["model", "cv_accuracy_mean", "test_accuracy", "macro_f1"]);
    renderRows(unsupervisedRows, data.unsupervised, ["model", "adjusted_rand", "normalized_mutual_info", "clusters_found"]);
    renderPlots(data.plots || {});
    log("Model comparison complete", data.summary);
    await refreshStatus();
  } catch (error) {
    log(error.message);
  } finally {
    setLoading(button, false);
  }
});

document.querySelector("#recordingDataset").addEventListener("change", () => loadRecordings().catch((error) => log(error.message)));

document.querySelector("#analyzeBtn").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  const path = document.querySelector("#recordingSelect").value;
  if (!path) return;
  setLoading(button, true);
  try {
    const data = await api("/api/analyze", { method: "POST", body: JSON.stringify({ path }) });
    document.querySelector("#analysisOutput").textContent = JSON.stringify(data, null, 2);
    log("Recording analyzed", { path: data.path, dominant_hz: data.dominant_hz, speed_mps: data.speed_mps });
  } catch (error) {
    log(error.message);
  } finally {
    setLoading(button, false);
  }
});

document.querySelector("#startLiveBtn").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  setLoading(button, true);
  try {
    const state = await api("/api/live/start", {
      method: "POST",
      body: JSON.stringify({
        mode: document.querySelector("#liveMode").value,
        port: document.querySelector("#livePort").value,
        dataset: document.querySelector("#liveDataset").value,
        window_seconds: Number(document.querySelector("#liveWindow").value),
      }),
    });
    renderLive(state);
    ensureLivePolling();
    log("Live detection started", { mode: state.mode, status: state.status });
  } catch (error) {
    log(error.message);
  } finally {
    setLoading(button, false);
  }
});

document.querySelector("#stopLiveBtn").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  setLoading(button, true);
  try {
    const state = await api("/api/live/stop", { method: "POST", body: JSON.stringify({}) });
    renderLive(state);
    log("Live detection stopped");
  } catch (error) {
    log(error.message);
  } finally {
    setLoading(button, false);
  }
});

document.querySelector("#recordBtn").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  setLoading(button, true);
  try {
    const data = await api("/api/record", {
      method: "POST",
      body: JSON.stringify({
        port: document.querySelector("#serialPort").value,
        label: document.querySelector("#recordLabel").value,
        seconds: Number(document.querySelector("#recordSeconds").value),
        out_dir: document.querySelector("#recordOut").value,
      }),
    });
    log("Serial recording complete", data);
    await refreshStatus();
  } catch (error) {
    log(error.message);
  } finally {
    setLoading(button, false);
  }
});

document.querySelector("#clearLog").addEventListener("click", () => {
  logEl.textContent = "Ready.";
});

Promise.all([refreshStatus(), loadResults(), loadRecordings(), refreshLiveStatus()]).catch((error) => log(error.message));
