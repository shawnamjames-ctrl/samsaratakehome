const DATA_ROOT = "data";
const DATA_VERSION = "reliable_20260831_v3-final";
const TAB_NAMES = ["overview", "analysis", "monitor", "method"];

const sourceLabels = {
  apple_driver_us: "Driver · iOS",
  apple_fleet_us: "Fleet · iOS",
  google_driver_us: "Driver · Android",
  google_fleet_us: "Fleet · Android",
};

const themeSummaries = {
  fleet_mobile_stability: "Reviews describe crashes, slow loading, blank screens, and unavailable views that can prevent Fleet users from completing core work.",
  fleet_access_recovery: "Reviews describe forced logouts, failed sign-ins, restart loops, and recovery steps such as password resets, reinstalls, or clearing app data.",
  driver_hos_state_integrity: "Reviews describe duty-status, synchronization, or warning behavior that may leave drivers uncertain whether their HOS record is correct.",
  driver_workflow_friction: "Reviews describe repeated selections, extra steps, clutter, and changed navigation that slow vehicle, DVIR, HOS, and navigation tasks.",
  driver_app_stability: "Reviews describe crashes, freezing, lag, and unresponsive behavior across devices, versions, and Driver workflows.",
  fleet_map_stability: "Reviews describe maps failing to load, zoom, select assets, or remain stable. This is handled within the broader Fleet stability problem.",
  driver_safety_false_detection: "Reviews describe safety alerts or AI detections perceived as incorrect, creating trust and review-or-appeal concerns. Reviews cannot verify model error.",
  driver_control_and_simplification_requests: "Reviews ask for restored behavior, simpler workflows, more control, and clearer status visibility across several Driver tasks.",
  fleet_product_requests: "Three older reviews request dark mode, iPad landscape support, or video-download parity. The signal is too small for roadmap priority.",
};

const formatDate = (value) => new Intl.DateTimeFormat("en-US", {
  month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short"
}).format(new Date(value));

const fetchJson = async (path) => {
  const response = await fetch(`${DATA_ROOT}/${path}?v=${DATA_VERSION}`);
  if (!response.ok) throw new Error(`Unable to load ${path}`);
  return response.json();
};

const escapeHtml = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

function activateTab(name, { focus = false, updateHistory = false } = {}) {
  const activeName = TAB_NAMES.includes(name) ? name : "overview";
  document.querySelectorAll('[role="tab"]').forEach((tab) => {
    const selected = tab.dataset.tab === activeName;
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
    if (selected && focus) tab.focus();
  });
  document.querySelectorAll("[data-tab-panel]").forEach((panel) => {
    panel.hidden = panel.dataset.tabPanel !== activeName;
  });
  if (updateHistory) history.pushState({ tab: activeName }, "", `#${activeName}`);
}

function initTabs() {
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  const returnToTop = () => window.scrollTo({
    top: 0,
    behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
  });
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => {
      activateTab(tab.dataset.tab, { updateHistory: true });
      returnToTop();
    });
    tab.addEventListener("keydown", (event) => {
      let nextIndex;
      if (event.key === "ArrowRight") nextIndex = (index + 1) % tabs.length;
      if (event.key === "ArrowLeft") nextIndex = (index - 1 + tabs.length) % tabs.length;
      if (event.key === "Home") nextIndex = 0;
      if (event.key === "End") nextIndex = tabs.length - 1;
      if (nextIndex === undefined) return;
      event.preventDefault();
      activateTab(tabs[nextIndex].dataset.tab, { focus: true, updateHistory: true });
      returnToTop();
    });
  });

  const hashTab = window.location.hash.slice(1);
  activateTab(hashTab, { updateHistory: false });
  window.addEventListener("popstate", () => activateTab(window.location.hash.slice(1)));
}

function initMemoDialog() {
  const dialog = document.getElementById("memo-dialog");
  const openButton = document.getElementById("open-memo");
  const closeButtons = [document.getElementById("close-memo"), document.getElementById("close-memo-footer")];
  openButton.addEventListener("click", () => dialog.showModal());
  closeButtons.forEach((button) => button.addEventListener("click", () => dialog.close()));
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
}

function renderThemeCards(themes, product = "All") {
  const filteredThemes = product === "All" ? themes : themes.filter((theme) => theme.product === product);
  const filterCopy = {
    All: {
      title: "All themes",
      heading: "The nine customer problems and needs that matter most",
      summary: "9 themes across Fleet and Driver. Rates retain their product-specific denominator.",
    },
    Fleet: {
      title: "Fleet themes",
      heading: "The four Fleet problems and needs that matter most",
      summary: "4 themes from 127 Fleet reviews across iOS and Android.",
    },
    Driver: {
      title: "Driver themes",
      heading: "The five Driver problems and needs that matter most",
      summary: "5 themes from 800 Driver reviews across iOS and Android.",
    },
  };
  document.getElementById("analysis-title").textContent = filterCopy[product].heading;
  document.getElementById("theme-filter-title").textContent = filterCopy[product].title;
  document.getElementById("theme-filter-summary").textContent = filterCopy[product].summary;
  document.querySelectorAll("[data-theme-filter]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.themeFilter === product));
  });
  const expandedThemes = filteredThemes.slice(0, 3);
  const additionalThemes = filteredThemes.slice(3);
  const expandedMarkup = expandedThemes.map((theme) => `<article class="theme-card theme-card-priority">
    <div>
      <header><span>#${theme.rank} · ${escapeHtml(theme.product)}</span><span>${escapeHtml(theme.confidence)}</span></header>
      <h3>${escapeHtml(theme.name)}</h3>
      <div class="theme-summary"><small>What this means</small><p>${escapeHtml(themeSummaries[theme.theme_id])}</p></div>
      <div class="theme-stat">${theme.rate_pct.toFixed(1)}% <small>${theme.count}/${theme.denominator}</small></div>
    </div>
    <footer>
      <span><small>Recommended action</small><strong>${escapeHtml(theme.executive_action)}</strong></span>
      <span><small>Priority</small><strong>${escapeHtml(theme.priority)}</strong></span>
      <span><small>Proposed owner</small><strong>${escapeHtml(theme.proposed_owner)}</strong></span>
    </footer>
    <button class="evidence-button" type="button" data-evidence-theme="${escapeHtml(theme.theme_id)}">Review evidence <span>${theme.count}</span><b aria-hidden="true">→</b></button>
  </article>`).join("");
  const additionalMarkup = additionalThemes.length ? `<details class="additional-themes">
    <summary><span><strong>${additionalThemes.length} additional ${product === "All" ? "themes" : `${product} themes`}</strong><small>Open the lower-priority findings and requests</small></span><b>Show themes</b></summary>
    <div class="additional-theme-list">
      ${additionalThemes.map((theme) => `<details class="theme-row">
        <summary>
          <span class="theme-row-rank">#${theme.rank}</span>
          <span class="theme-row-title"><strong>${escapeHtml(theme.name)}</strong><small>${escapeHtml(theme.product)} · ${escapeHtml(theme.confidence)} confidence</small></span>
          <span class="theme-row-stat"><strong>${theme.rate_pct.toFixed(1)}%</strong><small>${theme.count}/${theme.denominator}</small></span>
        </summary>
        <div class="theme-row-detail">
          <p>${escapeHtml(themeSummaries[theme.theme_id])}</p>
          <div><small>Recommended action</small><strong>${escapeHtml(theme.executive_action)}</strong></div>
          <div><small>${escapeHtml(theme.priority)} · proposed owner</small><strong>${escapeHtml(theme.proposed_owner)}</strong></div>
          <button class="evidence-button" type="button" data-evidence-theme="${escapeHtml(theme.theme_id)}">Review evidence <span>${theme.count}</span><b aria-hidden="true">→</b></button>
        </div>
      </details>`).join("")}
    </div>
  </details>` : "";
  document.getElementById("theme-grid").innerHTML = `<div class="theme-priority-grid">${expandedMarkup}</div>${additionalMarkup}`;
}

function initThemeFilters(themes) {
  document.querySelectorAll("[data-theme-filter]").forEach((button) => {
    button.addEventListener("click", () => renderThemeCards(themes, button.dataset.themeFilter));
  });
  renderThemeCards(themes);
}

function renderEvidence(themeId, evidenceData) {
  const theme = evidenceData.themes.find((item) => item.theme_id === themeId);
  if (!theme) return;
  const dialog = document.getElementById("evidence-dialog");
  const platformCounts = theme.records.reduce((counts, record) => {
    counts[record.platform] = (counts[record.platform] || 0) + 1;
    return counts;
  }, {});
  const consequentialCount = theme.records.filter((record) => record.consequence.startsWith("Critical") || record.consequence.startsWith("High")).length;

  document.getElementById("evidence-title").textContent = `${theme.name} evidence`;
  document.getElementById("evidence-context").textContent = `${theme.evidence_count} review records support this theme. Each row represents one theme-linked review; a review may support more than one theme.`;
  document.getElementById("evidence-summary").innerHTML = `
    <div><strong>${theme.evidence_count}</strong><span>Theme-linked reviews</span></div>
    <div><strong>${platformCounts.Android || 0}</strong><span>Android records</span></div>
    <div><strong>${platformCounts.iOS || 0}</strong><span>iOS records</span></div>
    <div><strong>${consequentialCount}</strong><span>Critical/high potential consequence</span></div>`;
  document.getElementById("evidence-table").innerHTML = theme.records.map((record) => `<tr>
    <td><code>${record.evidence_key}</code></td>
    <td>${record.product} · ${record.platform}</td>
    <td>${record.time_band}</td>
    <td>${record.rating_band}</td>
    <td>${record.consequence}</td>
    <td>${record.workflow}</td>
    <td>${record.reported_experience}</td>
  </tr>`).join("");
  const recordDetails = dialog.querySelector(".evidence-records");
  recordDetails.open = false;
  if (!dialog.open) dialog.showModal();
}

function initThemeEvidence(evidenceData) {
  document.getElementById("theme-grid").addEventListener("click", (event) => {
    const button = event.target.closest("[data-evidence-theme]");
    if (button) renderEvidence(button.dataset.evidenceTheme, evidenceData);
  });
  const dialog = document.getElementById("evidence-dialog");
  document.getElementById("close-evidence").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
}

function renderFurtherRecommendations(data) {
  const container = document.getElementById("further-recommendations-grid");
  const statusLabels = {
    supported_finding: "Supported finding",
    new_data_required: "New data required",
    supported_diagnostic: "Supported diagnostic",
  };
  container.innerHTML = [...data.recommendations]
    .sort((a, b) => a.display_order - b.display_order)
    .map((item) => `<article class="further-recommendation-card">
      <header>
        <span class="further-recommendation-number">${String(item.display_order).padStart(2, "0")}</span>
        <span class="recommendation-status recommendation-status-${escapeHtml(item.evidence_status.code)}">${escapeHtml(statusLabels[item.evidence_status.code] || item.evidence_status.label)}</span>
      </header>
      <h3>${escapeHtml(item.recommendation_name)}</h3>
      <p class="recommendation-rationale">${escapeHtml(item.rationale)}</p>
      <div class="recommendation-evidence-summary">
        <small>What the current evidence says</small>
        <p>${escapeHtml(item.evidence_summary)}</p>
      </div>
      <div class="recommendation-metrics">
        ${item.evidence.map((metric) => `<div class="recommendation-metric recommendation-metric-${escapeHtml(metric.evidence_class)}">
          <strong>${escapeHtml(metric.metric_value)}</strong>
          <span>${escapeHtml(metric.metric_label)}</span>
          <small>${escapeHtml(metric.context)}</small>
        </div>`).join("")}
      </div>
      <div class="recommendation-action">
        <small>Recommended next move</small>
        <p>${escapeHtml(item.recommended_action)}</p>
      </div>
      <details class="recommendation-detail">
        <summary>Boundaries and data needed</summary>
        <div>
          <strong>What not to conclude</strong>
          <p>${escapeHtml(item.decision_boundary)}</p>
          <strong>What to add next</strong>
          <p>${escapeHtml(item.additional_data_needed)}</p>
        </div>
      </details>
    </article>`).join("");
}

function renderMethodologyProcess(data) {
  document.getElementById("methodology-title").textContent = data.heading;
  document.getElementById("methodology-lede").textContent = data.lede;
  document.getElementById("method-scope").innerHTML = data.scope_metrics.map((item) => `<div><strong>${escapeHtml(item.value)}</strong><span>${escapeHtml(item.label)}</span></div>`).join("");

  const buttons = document.getElementById("method-layer-buttons");
  const detail = document.getElementById("method-layer-detail");
  const showLayer = (layer) => {
    buttons.querySelectorAll("button").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.layerId === layer.layer_id)));
    detail.innerHTML = `<header><span>Layer ${String(layer.display_order).padStart(2, "0")} · ${escapeHtml(layer.path_type)}</span><h3>${escapeHtml(layer.heading)}</h3></header>
      <div><section><small>Input</small><p>${escapeHtml(layer.input_summary)}</p></section><section><small>Decision</small><p>${escapeHtml(layer.decision_summary)}</p></section><section><small>Output</small><p>${escapeHtml(layer.output_summary)}</p></section><section class="method-gate"><small>Gate</small><p>${escapeHtml(layer.gate_summary)}</p></section></div>`;
  };
  buttons.innerHTML = data.layers.map((layer) => `<button type="button" data-layer-id="${escapeHtml(layer.layer_id)}" aria-pressed="false"><span>${String(layer.display_order).padStart(2, "0")}</span>${escapeHtml(layer.short_label)}</button>`).join("");
  buttons.addEventListener("click", (event) => {
    const button = event.target.closest("[data-layer-id]");
    if (!button) return;
    showLayer(data.layers.find((layer) => layer.layer_id === button.dataset.layerId));
  });
  showLayer(data.layers[0]);

  document.getElementById("method-phase-list").innerHTML = data.phases.map((phase, index) => `<details class="method-phase" ${index === 0 ? "open" : ""}>
    <summary><span>${String(phase.display_order).padStart(2, "0")}</span><div><small>${escapeHtml(phase.objective)}</small><strong>${escapeHtml(phase.heading)}</strong></div></summary>
    <div class="method-phase-body"><section><small>What we did</small><p>${escapeHtml(phase.work_completed)}</p></section><section><small>Decision</small><p>${escapeHtml(phase.decision_made)}</p></section><section><small>Why</small><p>${escapeHtml(phase.rationale)}</p></section><section><small>Evidence produced</small><p>${escapeHtml(phase.evidence_produced)}</p></section><section class="phase-boundary"><small>Boundary or gate</small><p>${escapeHtml(phase.boundary_or_gate)}</p></section></div>
  </details>`).join("");

  document.getElementById("method-decision-grid").innerHTML = data.decision_moments.map((item) => `<details>
    <summary><span>${String(item.display_order).padStart(2, "0")}</span><h3>${escapeHtml(item.heading)}</h3></summary>
    <div><p>${escapeHtml(item.situation)}</p><strong>Action taken</strong><p>${escapeHtml(item.action_taken)}</p><strong>Why it matters</strong><p>${escapeHtml(item.why_it_matters)}</p></div>
  </details>`).join("");
  document.getElementById("method-publication-policy").textContent = data.publication_policy;
  document.getElementById("method-automated-list").innerHTML = data.operating_model.automated.map((item) => `<li>${escapeHtml(item.responsibility)}</li>`).join("");
  document.getElementById("method-human-list").innerHTML = data.operating_model.human.map((item) => `<li>${escapeHtml(item.responsibility)}</li>`).join("");
  const practiceLabels = {
    ai_use: "How AI was used",
    access_limits: "Access limits",
    next_week: "With another week",
    production_boundary: "Production boundary",
  };
  document.getElementById("method-practice-grid").innerHTML = Object.entries(data.practice_notes)
    .map(([key, value]) => `<article><span>${escapeHtml(practiceLabels[key])}</span><p>${escapeHtml(value)}</p></article>`)
    .join("");
}

const monitorStatusLabels = {
  alert: "Alert candidate",
  watch: "Watch",
  stable: "Stable",
  insufficient_data: "Limited data",
};

function renderExistingThemeMonitor(data) {
  const metrics = data.existing_theme_metrics;
  const order = {alert: 0, watch: 1, stable: 2, insufficient_data: 3};
  const sorted = [...metrics].sort((a, b) => order[a.status] - order[b.status] || Math.abs(b.rate_change_pp) - Math.abs(a.rate_change_pp));
  const attentionThemes = sorted.filter((item) => item.status === "alert" || item.status === "watch");
  document.getElementById("monitor-attention-list").innerHTML = attentionThemes.length
    ? attentionThemes.map((theme) => `<article class="monitor-attention-card status-${theme.status}">
        <header><div><span>${escapeHtml(theme.product)}</span><h3>${escapeHtml(theme.name)}</h3></div><b class="monitor-status status-${theme.status}">${monitorStatusLabels[theme.status]}</b></header>
        <div class="monitor-attention-metrics"><strong>${theme.rate_pct.toFixed(1)}%</strong><span>${theme.count}/${theme.denominator} latest 30 days</span><b>${theme.rate_change_pp > 0 ? "+" : ""}${theme.rate_change_pp.toFixed(1)} pp</b></div>
        <p>${escapeHtml(theme.recommended_action)}</p>
      </article>`).join("")
    : `<div class="emerging-empty"><span>0 themes need attention</span><h3>No established theme crossed a watch or alert threshold.</h3></div>`;

  const detail = document.getElementById("monitor-theme-detail");
  const table = document.getElementById("monitor-theme-table");
  const renderDetail = (theme) => {
    table.querySelectorAll("button").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.monitorTheme === theme.theme_id)));
    const interpretation = theme.status === "insufficient_data"
      ? `The recent sample is too small for a quantitative alert. One additional review would move the rate by ${theme.one_review_sensitivity_pp.toFixed(1)} percentage points.`
      : theme.status === "alert"
        ? "The increase crossed the automated alert threshold. A person must review the evidence before the finding or recommendation changes."
        : theme.status === "watch"
          ? "The recent rate is elevated enough to watch, but this is an investigation trigger, not evidence of root cause."
          : "The recent pattern did not cross the configured watch or alert threshold.";
    detail.innerHTML = `<header><div><span>${escapeHtml(theme.product)} · Latest 30 vs prior 60</span><h3>${escapeHtml(theme.name)}</h3></div><b class="monitor-status status-${theme.status}">${monitorStatusLabels[theme.status]}</b></header>
      <div class="monitor-detail-metrics"><div><strong>${theme.count}/${theme.denominator}</strong><span>Latest 30 days · ${theme.rate_pct.toFixed(1)}%</span></div><div><strong>${theme.prior_count}/${theme.prior_denominator}</strong><span>Prior 60 days · ${theme.prior_rate_pct.toFixed(1)}%</span></div><div><strong>${theme.rate_change_pp > 0 ? "+" : ""}${theme.rate_change_pp.toFixed(1)} pp</strong><span>Rate change</span></div></div>
      <div class="monitor-interpretation"><small>How to interpret this</small><p>${escapeHtml(interpretation)}</p></div>
      <div class="monitor-action"><small>Recommended action</small><p>${escapeHtml(theme.recommended_action)}</p></div>
      <footer><span>${theme.provisional_count} provisional assignments in the latest window</span><span>One-review sensitivity: ${theme.one_review_sensitivity_pp.toFixed(1)} pp</span></footer>`;
  };
  table.innerHTML = sorted.map((theme) => `<tr>
    <td><button type="button" data-monitor-theme="${escapeHtml(theme.theme_id)}" aria-pressed="false"><strong>${escapeHtml(theme.name)}</strong><span>${escapeHtml(theme.product)}</span></button></td>
    <td><strong>${theme.rate_pct.toFixed(1)}%</strong><span>${theme.count}/${theme.denominator}</span></td>
    <td><strong>${theme.prior_rate_pct.toFixed(1)}%</strong><span>${theme.prior_count}/${theme.prior_denominator}</span></td>
    <td class="monitor-delta ${theme.rate_change_pp > 0 ? "up" : theme.rate_change_pp < 0 ? "down" : ""}">${theme.rate_change_pp > 0 ? "+" : ""}${theme.rate_change_pp.toFixed(1)} pp</td>
    <td><span class="monitor-status status-${theme.status}">${monitorStatusLabels[theme.status]}</span></td>
  </tr>`).join("");
  table.addEventListener("click", (event) => {
    const button = event.target.closest("[data-monitor-theme]");
    if (!button) return;
    renderDetail(metrics.find((item) => item.theme_id === button.dataset.monitorTheme));
  });
  renderDetail(sorted.find((item) => item.status === "alert") || sorted.find((item) => item.status === "watch") || sorted[0]);
}

function renderEmergingSignals(data) {
  const container = document.getElementById("emerging-signal-grid");
  if (!data.emerging_signals.length) {
    container.innerHTML = `<div class="emerging-empty"><span>0 candidate patterns</span><h3>No repeated unmatched pattern crossed the candidate threshold.</h3><p>${data.unclassified_review_count} unmatched reviews currently require classification review. Confirmed no-theme reviews remain outside the candidate queue.</p></div>`;
    return;
  }
  container.innerHTML = data.emerging_signals.map((item) => `<article class="emerging-card"><header><span>${escapeHtml(item.product)} · ${escapeHtml(item.platform)}</span><b>${item.support_count} reviews</b></header><h3>${escapeHtml(item.label)}</h3><dl><div><dt>First seen</dt><dd>${formatDate(item.first_review_at)}</dd></div><div><dt>Latest</dt><dd>${formatDate(item.latest_review_at)}</dd></div><div><dt>Average rating</dt><dd>${item.average_rating.toFixed(1)}</dd></div></dl><p>Human review is required before this pattern can be named, added to the taxonomy, or used as an executive finding.</p></article>`).join("");
}

async function start() {
  try {
    const [summary, deltas, themes, pipeline, staticContent, themeEvidence, furtherRecommendations, methodologyProcess] = await Promise.all([
      fetchJson("dashboard/dashboard-summary.json"),
      fetchJson("dashboard/dashboard-deltas.json"),
      fetchJson("dashboard/dashboard-themes.json"),
      fetchJson("dashboard/pipeline-status.json"),
      fetchJson("releases/reliable_20260831_v3/static-content.json"),
      fetchJson("releases/reliable_20260831_v3/theme-evidence.json"),
      fetchJson("releases/reliable_20260831_v3/further-recommendations.json"),
      fetchJson("releases/reliable_20260831_v3/methodology-process.json"),
    ]);

    document.getElementById("new-review-count").textContent = summary.new_reviews_since_prior_success;
    document.getElementById("changed-review-count").textContent = summary.changed_reviews_since_prior_success;
    document.getElementById("queue-count").textContent = summary.human_review_queue_count;
    document.getElementById("source-count").textContent = `${summary.source_status.filter((row) => row.status === "succeeded").length}/4`;
    document.getElementById("freshness-label").textContent = `Data observed through ${formatDate(summary.data_through)}`;
    const attentionCount = themes.existing_theme_metrics.filter((item) => item.status === "alert" || item.status === "watch").length;
    document.getElementById("freshness-detail").textContent = `${attentionCount} theme signals and ${themes.emerging_signals.length} emerging candidates need attention`;
    document.getElementById("attention-count").textContent = attentionCount;
    document.getElementById("pipeline-summary").textContent = `${summary.source_status.filter((row) => row.status === "succeeded").length}/4 sources healthy`;
    document.getElementById("release-id").textContent = `Approved release: ${summary.analysis_release_id}`;

    renderExistingThemeMonitor(themes);
    renderEmergingSignals(themes);

    const changeLabels = {
      new_review: "New review",
      text_edited: "Text edited",
      rating_changed: "Rating changed",
      app_version_changed: "Version changed",
      developer_reply_changed: "Reply changed",
      helpfulness_changed: "Helpfulness changed",
      visibility_changed: "Visibility changed",
    };
    document.getElementById("delta-list").innerHTML = Object.entries(deltas.delta_counts)
      .sort((a, b) => b[1] - a[1])
      .map(([key, count]) => `<div class="delta-item"><div><strong>${changeLabels[key] || key}</strong><br><span>Verified against the prior last-good state</span></div><b>${count}</b></div>`)
      .join("");

    document.getElementById("source-table").innerHTML = summary.source_status.map((row) => `<tr>
      <td><strong>${sourceLabels[row.app_key] || row.app_key}</strong></td>
      <td class="source-ok">${row.status}</td>
      <td>${row.records_received.toLocaleString()}</td>
      <td>${row.newest_review_at ? formatDate(row.newest_review_at) : "No dated review"}</td>
    </tr>`).join("");

    const pipelineBadge = document.getElementById("pipeline-badge");
    pipelineBadge.textContent = pipeline.status === "withheld" ? "Local preview · publication gated" : pipeline.status;
    document.querySelector(".status-dot").style.background = summary.source_status.every((row) => row.status === "succeeded") ? "var(--success)" : "var(--amber)";
    document.querySelector(".monitor-header .lede").textContent = "Track movement in the nine approved themes and route repeated unmatched feedback into human review. Daily signals do not silently rewrite executive conclusions.";

    document.getElementById("executive-decision").textContent = staticContent.surfaces.executive_overview.decision;
    document.getElementById("executive-change").textContent = staticContent.surfaces.executive_overview.recent_signal;
    const recommendationByTheme = new Map(staticContent.surfaces.recommendations.map((item) => [item.theme_id, item]));
    const themesByRank = [...staticContent.surfaces.thematic_analysis.themes]
      .map((theme) => {
        const recommendation = recommendationByTheme.get(theme.theme_id);
        return {
          ...theme,
          executive_action: recommendation.recommendation,
          priority: recommendation.priority,
          proposed_owner: recommendation.proposed_owner,
        };
      })
      .sort((a, b) => a.rank - b.rank);
    const themeById = new Map(themesByRank.map((theme) => [theme.theme_id, theme]));
    const fleetStability = themeById.get("fleet_mobile_stability");
    const fleetAccess = themeById.get("fleet_access_recovery");
    const driverHos = themeById.get("driver_hos_state_integrity");
    const driverWorkflow = themeById.get("driver_workflow_friction");
    const driverStability = themeById.get("driver_app_stability");
    document.getElementById("priority-strip").innerHTML = `
      <article class="priority-item executive-signal urgent">
        <span>Most urgent</span>
        <strong>Fleet reliability is the clearest failure cluster</strong>
        <p><b>${fleetStability.count}/${fleetStability.denominator} · ${fleetStability.rate_pct.toFixed(1)}%</b> mention mobile stability. Access and recovery follows at ${fleetAccess.rate_pct.toFixed(1)}%.</p>
      </article>
      <article class="priority-item executive-signal consequence">
        <span>Highest consequence</span>
        <strong>Driver HOS integrity deserves executive protection</strong>
        <p><b>${driverHos.count}/${driverHos.denominator} · ${driverHos.rate_pct.toFixed(1)}%</b> report state-integrity problems involving a compliance-critical workflow.</p>
      </article>
      <article class="priority-item executive-signal control">
        <span>Shared control point</span>
        <strong>Release quality can reduce the broader burden</strong>
        <p>Driver app stability is ${driverStability.rate_pct.toFixed(1)}%; workflow friction is ${driverWorkflow.rate_pct.toFixed(1)}%. Both point to release experience as a leadership lever.</p>
      </article>`;

    initThemeFilters(themesByRank);
    initThemeEvidence(themeEvidence);
    renderFurtherRecommendations(furtherRecommendations);
    renderMethodologyProcess(methodologyProcess);

    const method = staticContent.surfaces.methodology;
  } catch (error) {
    console.error(error);
    document.getElementById("freshness-label").textContent = "Monitoring data unavailable";
    document.getElementById("freshness-detail").textContent = error.message;
    document.getElementById("pipeline-badge").textContent = "Load failed";
  }
}

if (window.location.protocol === "file:") {
  const activeHash = TAB_NAMES.includes(window.location.hash.slice(1)) ? window.location.hash : "#overview";
  window.location.replace(`http://127.0.0.1:8765/${activeHash}`);
} else {
  initTabs();
  initMemoDialog();
  start();
}
