(function () {
  "use strict";

  let ws = null;
  let reconnectTimer = null;
  const RECONNECT_MS = 2000;

  let configDirty = false;
  let configSchema = null;

  const $id = (id) => document.getElementById(id);
  const $qa = (sel) => document.querySelectorAll(sel);

  /* ═══════════════════════════════════════════════════════════
     NAVIGATION
     ═══════════════════════════════════════════════════════════ */

  $qa(".nav-tab").forEach((tab) => {
    tab.addEventListener("click", (e) => {
      e.preventDefault();
      const page = tab.dataset.page;
      $qa(".nav-tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      $qa(".page").forEach((p) => p.classList.remove("active"));
      $id("page-" + page).classList.add("active");
      if (page === "config" && !configSchema) loadConfig();
      history.replaceState(null, "", page === "control" ? "/" : "/" + page);
    });
  });

  if (location.pathname === "/config") {
    document.querySelector('[data-page="config"]').click();
  }

  /* ═══════════════════════════════════════════════════════════
     WEBSOCKET
     ═══════════════════════════════════════════════════════════ */

  const connDot    = $id("conn-dot");
  const connLabel  = $id("conn-label");
  const btnConnect = $id("btn-connect");
  const btnDisconn = $id("btn-disconnect");

  function connectWS() {
    if (ws && ws.readyState <= WebSocket.OPEN) return;
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${proto}//${location.host}/ws`);
    ws.onopen = () => clearTimeout(reconnectTimer);
    ws.onclose = () => scheduleReconnect();
    ws.onerror = () => ws.close();
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "status") updateControlUI(msg);
      } catch (_) {}
    };
  }

  function scheduleReconnect() {
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(connectWS, RECONNECT_MS);
  }

  function send(obj) {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
  }

  /* ═══════════════════════════════════════════════════════════
     CONTROL PAGE — STATUS UPDATES
     ═══════════════════════════════════════════════════════════ */

  function updateControlUI(s) {
    $id("hotend-temp").textContent   = s.hotend_temp?.toFixed(1) ?? "--";
    $id("hotend-target").textContent = s.hotend_target?.toFixed(0) ?? "0";
    $id("pos-y").textContent         = s.y_pos?.toFixed(1) ?? "0";
    $id("pos-z").textContent         = s.z_pos?.toFixed(2) ?? "0";
    $id("pos-e").textContent         = s.e_pos?.toFixed(1) ?? "0";
    $id("vol-flow").textContent      = s.volumetric_flow?.toFixed(1) ?? "0";

    const online = s.connected === true;
    connDot.classList.toggle("online", online);
    connDot.classList.toggle("offline", !online);
    connLabel.textContent = online ? "Printer Online" : "Printer Offline";
    btnConnect.disabled  = online;
    btnDisconn.disabled  = !online;

    if (s.is_logging !== undefined) updateLoggingUI(s.is_logging);
  }

  async function loadMachineInfo() {
    try {
      const resp = await fetch("/api/machine");
      const m = await resp.json();
      $id("kin-gear").textContent     = m.bed_gear_ratio;
      $id("kin-nozzle").textContent   = m.nozzle_diameter;
      $id("kin-filament").textContent = m.filament_diameter;
      $id("kin-zmax").textContent     = m.z_max;
      $id("kin-max-vol").textContent  = m.max_volumetric_flow;
    } catch (_) {}
  }

  /* ═══════════════════════════════════════════════════════════
     CONTROL PAGE — EVENTS
     ═══════════════════════════════════════════════════════════ */

  $qa(".motion-btn").forEach((btn) => {
    const action = btn.dataset.action;
    function start(e) { e.preventDefault(); btn.classList.add("active"); send({ action, state: true }); }
    function stop(e)  { e.preventDefault(); btn.classList.remove("active"); send({ action, state: false }); }
    btn.addEventListener("mousedown",   start);
    btn.addEventListener("mouseup",     stop);
    btn.addEventListener("mouseleave",  stop);
    btn.addEventListener("touchstart",  start, { passive: false });
    btn.addEventListener("touchend",    stop,  { passive: false });
    btn.addEventListener("touchcancel", stop,  { passive: false });
  });

  $id("btn-set-hotend").addEventListener("click", () =>
    send({ action: "set_hotend_temp", value: parseFloat($id("input-hotend").value) || 0 }));
  $id("btn-set-fan").addEventListener("click", () =>
    send({ action: "set_fan", value: parseInt($id("input-fan").value, 10) || 0 }));

  $id("btn-set-yfeed").addEventListener("click", () =>
    send({ action: "set_feedrate", axis: "y", value: parseFloat($id("input-yfeed").value) || 2700 }));
  $id("btn-set-ystep").addEventListener("click", () =>
    send({ action: "set_step", axis: "y", value: parseFloat($id("input-ystep").value) || 1 }));
  $id("btn-set-efeed").addEventListener("click", () =>
    send({ action: "set_feedrate", axis: "e", value: parseFloat($id("input-efeed").value) || 300 }));
  $id("btn-set-estep").addEventListener("click", () =>
    send({ action: "set_step", axis: "e", value: parseFloat($id("input-estep").value) || 0.5 }));
  $id("btn-set-zfeed").addEventListener("click", () =>
    send({ action: "set_feedrate", axis: "z", value: parseFloat($id("input-zfeed").value) || 600 }));
  $id("btn-set-zstep").addEventListener("click", () =>
    send({ action: "set_step", axis: "z", value: parseFloat($id("input-zstep").value) || 0.1 }));

  $id("btn-home").addEventListener("click",  () => send({ action: "home" }));
  $id("btn-estop").addEventListener("click", () => send({ action: "emergency_stop" }));
  btnConnect.addEventListener("click", () => send({ action: "connect" }));
  btnDisconn.addEventListener("click", () => send({ action: "disconnect" }));

  const gcodeInput = $id("gcode-input");
  $id("btn-send-gcode").addEventListener("click", () => {
    const line = gcodeInput.value.trim();
    if (line) { send({ action: "gcode", value: line }); gcodeInput.value = ""; }
  });
  gcodeInput.addEventListener("keydown", (e) => { if (e.key === "Enter") $id("btn-send-gcode").click(); });

  /* ═══════════════════════════════════════════════════════════
     G-CODE LOGGER
     ═══════════════════════════════════════════════════════════ */

  const toggleLogging = $id("toggle-logging");
  const logStatus     = $id("log-status");
  const btnLogDownload = $id("btn-log-download");
  const btnLogBrowse  = $id("btn-log-browse");
  const logBrowser    = $id("log-browser");
  const logList       = $id("log-list");

  toggleLogging.addEventListener("change", () => {
    send({ action: "toggle_logging", state: toggleLogging.checked });
  });

  btnLogBrowse.addEventListener("click", async () => {
    const visible = logBrowser.style.display !== "none";
    if (visible) {
      logBrowser.style.display = "none";
      return;
    }
    try {
      const resp = await fetch("/api/logs");
      const data = await resp.json();
      logList.innerHTML = "";
      if (data.logs.length === 0) {
        logList.innerHTML = '<div class="log-empty">No log files yet</div>';
      } else {
        for (const name of data.logs) {
          const row = document.createElement("a");
          row.className = "log-entry";
          row.href = "/api/logs/" + encodeURIComponent(name);
          row.download = name;
          row.textContent = name;
          if (data.active && name === data.current) {
            const badge = document.createElement("span");
            badge.className = "log-recording-badge";
            badge.textContent = "recording";
            row.appendChild(badge);
          }
          logList.appendChild(row);
        }
      }
      logBrowser.style.display = "block";
    } catch (_) {}
  });

  function updateLoggingUI(isLogging) {
    toggleLogging.checked = isLogging;
    logStatus.textContent = isLogging ? "Recording..." : "Logging off";
    logStatus.classList.toggle("recording", isLogging);
    btnLogDownload.style.display = isLogging ? "none" : "none";
  }

  /* ═══════════════════════════════════════════════════════════
     CONFIG PAGE
     ═══════════════════════════════════════════════════════════ */

  $qa(".config-mode-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      $qa(".config-mode-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const mode = btn.dataset.mode;
      $id("config-form").classList.toggle("active", mode === "form");
      $id("config-raw").classList.toggle("active", mode === "raw");
      if (mode === "raw") syncFormToRaw();
    });
  });

  async function loadConfig() {
    try {
      const resp = await fetch("/api/config");
      const data = await resp.json();
      configSchema = data.schema;
      renderConfigForm(configSchema);
      $id("config-yaml-editor").value = data.raw;
      configDirty = false;
      $id("btn-config-save").disabled = true;
    } catch (e) {
      $id("config-form").innerHTML =
        `<div class="config-loading" style="color:var(--danger)">Failed to load config: ${e.message}</div>`;
    }
  }

  function renderConfigForm(schema) {
    const container = $id("config-form");
    container.innerHTML = "";
    for (const [sectionKey, section] of Object.entries(schema)) {
      const sec = document.createElement("div");
      sec.className = "cfg-section open";
      const header = document.createElement("div");
      header.className = "cfg-section-header";
      header.innerHTML = `<span class="cfg-section-title">${section.label}</span><span class="cfg-section-chevron">&#9660;</span>`;
      header.addEventListener("click", () => sec.classList.toggle("open"));
      const body = document.createElement("div");
      body.className = "cfg-section-body";
      for (const [fieldKey, field] of Object.entries(section.fields))
        body.appendChild(createFieldRow(sectionKey, fieldKey, field));
      sec.appendChild(header);
      sec.appendChild(body);
      container.appendChild(sec);
    }
  }

  function createFieldRow(section, key, field) {
    const row = document.createElement("div");
    row.className = "cfg-field";

    const label = document.createElement("div");
    label.className = "cfg-field-label";
    label.innerHTML = `${field.label}<span class="cfg-key">${key}</span>`;

    const inputWrap = document.createElement("div");
    inputWrap.className = "cfg-field-input";
    let input;

    if (field.type === "bool") {
      input = document.createElement("select");
      for (const v of ["true", "false"]) {
        const opt = document.createElement("option");
        opt.value = v; opt.textContent = v;
        if (String(field.value) === v) opt.selected = true;
        input.appendChild(opt);
      }
    } else if (field.options && field.type !== "text") {
      input = document.createElement("select");
      const hasCustom = field.options.indexOf(field.value) === -1 && field.value !== "";
      if (hasCustom) {
        const opt = document.createElement("option");
        opt.value = field.value; opt.textContent = String(field.value);
        input.appendChild(opt);
      }
      for (const o of field.options) {
        const opt = document.createElement("option");
        opt.value = o; opt.textContent = String(o);
        if (String(o) === String(field.value)) opt.selected = true;
        input.appendChild(opt);
      }
    } else if (field.type === "text") {
      input = document.createElement("textarea");
      input.value = field.value || "";
      input.rows = 4;
    } else {
      input = document.createElement("input");
      if (field.type === "int" || field.type === "float") {
        input.type = "number";
        if (field.type === "float") input.step = "any";
      } else {
        input.type = "text";
      }
      input.value = field.value ?? "";
    }

    input.dataset.section = section;
    input.dataset.key = key;
    input.addEventListener("input", markConfigDirty);
    inputWrap.appendChild(input);

    if (field.help) {
      const help = document.createElement("div");
      help.className = "cfg-field-help";
      help.textContent = field.help;
      inputWrap.appendChild(help);
    }

    row.appendChild(label);
    row.appendChild(inputWrap);
    return row;
  }

  function markConfigDirty() {
    configDirty = true;
    $id("btn-config-save").disabled = false;
  }

  function gatherFormValues() {
    const data = {};
    $qa(".cfg-field-input input, .cfg-field-input select, .cfg-field-input textarea").forEach((el) => {
      const s = el.dataset.section, k = el.dataset.key;
      if (!s || !k) return;
      if (!data[s]) data[s] = {};
      let val = el.value;
      const schema = configSchema?.[s]?.fields?.[k];
      if (schema) {
        if (schema.type === "int") val = parseInt(val, 10) || 0;
        else if (schema.type === "float") val = parseFloat(val) || 0;
        else if (schema.type === "bool") val = val === "true";
      }
      data[s][k] = val;
    });
    return data;
  }

  function formValuesToYaml(values) {
    const lines = [];
    for (const [sec, fields] of Object.entries(values)) {
      lines.push(`${sec}:`);
      for (const [k, v] of Object.entries(fields)) {
        if (typeof v === "string" && v.includes("\n")) {
          lines.push(`  ${k}: |`);
          for (const line of v.split("\n")) lines.push(`    ${line}`);
        } else if (typeof v === "string" && /^[!^]/.test(v)) {
          lines.push(`  ${k}: "${v}"`);
        } else if (typeof v === "boolean") {
          lines.push(`  ${k}: ${v}`);
        } else {
          lines.push(`  ${k}: ${v}`);
        }
      }
      lines.push("");
    }
    return lines.join("\n");
  }

  function syncFormToRaw() {
    $id("config-yaml-editor").value = formValuesToYaml(gatherFormValues());
  }

  $id("btn-config-save").addEventListener("click", () => saveConfig(false));
  $id("btn-config-restart").addEventListener("click", () => saveConfig(true));

  async function saveConfig(restart) {
    const rawView = $id("config-raw").classList.contains("active");
    try {
      const yamlText = rawView
        ? $id("config-yaml-editor").value
        : formValuesToYaml(gatherFormValues());

      let resp = await fetch("/api/config/raw", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ yaml: yamlText }),
      });
      const result = await resp.json();
      if (!result.ok) throw new Error(result.error || "Save failed");

      if (restart) {
        const r2 = await fetch("/api/config/restart", { method: "POST" });
        const r2j = await r2.json();
        if (!r2j.ok) showToast("Saved, but restart failed: " + (r2j.error || ""), true);
        else showToast("Saved & restarting...");
      } else {
        showToast("Configuration saved");
      }

      configDirty = false;
      $id("btn-config-save").disabled = true;
      await loadConfig();
      await loadMachineInfo();
    } catch (e) {
      showToast("Error: " + e.message, true);
    }
  }

  $id("btn-config-reset").addEventListener("click", async () => {
    if (!confirm("Reset all settings to factory defaults?")) return;
    try {
      const resp = await fetch("/api/config/reset", { method: "POST" });
      const result = await resp.json();
      if (result.ok) {
        showToast("Configuration reset to defaults");
        await loadConfig();
        await loadMachineInfo();
      }
    } catch (e) {
      showToast("Reset failed: " + e.message, true);
    }
  });

  $id("config-yaml-editor").addEventListener("input", markConfigDirty);

  function showToast(msg, isError) {
    const toast = $id("config-toast");
    toast.textContent = msg;
    toast.classList.toggle("error", !!isError);
    toast.classList.remove("hidden");
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => toast.classList.add("hidden"), 3500);
  }

  /* ═══════════════════════════════════════════════════════════
     BOOT
     ═══════════════════════════════════════════════════════════ */
  connectWS();
  loadMachineInfo();
})();
