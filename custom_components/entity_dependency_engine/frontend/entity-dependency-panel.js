const PANEL_TAG = "ha-panel-entity-dependency-engine";

const escapeHtml = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

const roleLabel = (roles) => {
  if (roles?.includes("root")) return "Root";
  if (roles?.includes("parent")) return "Parent";
  if (roles?.includes("child")) return "Child";
  if (roles?.includes("ancestor")) return "Ancestor";
  if (roles?.includes("descendant")) return "Descendant";
  return "Node";
};

class EntityDependencyEnginePanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });

    this._hass = undefined;
    this._panel = undefined;
    this._route = undefined;
    this._narrow = false;

    this._query = "";
    this._entities = [];
    this._entityTotal = 0;
    this._graph = undefined;
    this._selectedEntityId = undefined;

    this._loadingSearch = false;
    this._loadingGraph = false;
    this._error = undefined;

    this._searchTimer = undefined;
    this._searchRequestId = 0;
    this._graphRequestId = 0;

    this._rendered = false;
    this._initialized = false;
  }

  set hass(value) {
    this._hass = value;
    this._initializeWhenReady();
  }

  get hass() {
    return this._hass;
  }

  set panel(value) {
    this._panel = value;
  }

  set route(value) {
    this._route = value;
  }

  set narrow(value) {
    this._narrow = Boolean(value);
    this.toggleAttribute("narrow", this._narrow);
  }

  connectedCallback() {
    if (!this._rendered) {
      this._renderShell();
      this._bindEvents();
      this._rendered = true;
    }

    this._initializeWhenReady();
  }

  disconnectedCallback() {
    window.clearTimeout(this._searchTimer);
  }

  _initializeWhenReady() {
    if (
      !this._initialized &&
      this._hass &&
      this.isConnected &&
      this._rendered
    ) {
      this._initialized = true;
      queueMicrotask(() => this._searchEntities());
    }
  }

  async _callWS(message) {
    if (!this._hass) {
      throw new Error("Home Assistant is not connected yet.");
    }

    if (typeof this._hass.callWS === "function") {
      return this._hass.callWS(message);
    }

    return this._hass.connection.sendMessagePromise(message);
  }

  async _searchEntities({ refresh = false } = {}) {
    const requestId = ++this._searchRequestId;
    this._loadingSearch = true;
    this._error = undefined;
    this._renderStatus();

    try {
      const result = await this._callWS({
        type: "entity_dependency_engine/search_entities",
        query: this._query.trim(),
        limit: 50,
        refresh,
      });

      if (requestId !== this._searchRequestId) return;

      this._entities = result.entities ?? [];
      this._entityTotal = Number(result.total ?? this._entities.length);
    } catch (error) {
      if (requestId !== this._searchRequestId) return;

      this._entities = [];
      this._entityTotal = 0;
      this._error = error?.message ?? String(error);
    } finally {
      if (requestId === this._searchRequestId) {
        this._loadingSearch = false;
        this._renderResults();
        this._renderStatus();
      }
    }
  }

  async _loadGraph(entityId, { refresh = false } = {}) {
    const requestId = ++this._graphRequestId;
    this._selectedEntityId = entityId;
    this._loadingGraph = true;
    this._error = undefined;

    this._renderResults();
    this._renderGraph();
    this._renderStatus();

    try {
      const graph = await this._callWS({
        type: "entity_dependency_engine/get_graph",
        entity_id: entityId,
        scope: "direct",
        max_nodes: 250,
        include_structural: false,
        refresh,
      });

      if (requestId !== this._graphRequestId) return;
      this._graph = graph;
    } catch (error) {
      if (requestId !== this._graphRequestId) return;

      this._graph = undefined;
      this._error = error?.message ?? String(error);
    } finally {
      if (requestId === this._graphRequestId) {
        this._loadingGraph = false;
        this._renderGraph();
        this._renderStatus();
      }
    }
  }

  _openMoreInfo(entityId) {
    this.dispatchEvent(
      new CustomEvent("hass-more-info", {
        detail: { entityId },
        bubbles: true,
        composed: true,
      }),
    );
  }

  async _copyEntityId(entityId) {
    try {
      await navigator.clipboard.writeText(entityId);
    } catch (_error) {
      const textarea = document.createElement("textarea");
      textarea.value = entityId;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      textarea.remove();
    }

    const message = this.shadowRoot?.querySelector("#copy-message");
    if (message) {
      message.textContent = `Copied ${entityId}`;
      window.setTimeout(() => {
        if (message.textContent === `Copied ${entityId}`) {
          message.textContent = "";
        }
      }, 1800);
    }
  }

  _bindEvents() {
    const root = this.shadowRoot;
    if (!root) return;

    const input = root.querySelector("#entity-search");
    const results = root.querySelector("#entity-results");
    const graph = root.querySelector("#graph-content");

    input?.addEventListener("input", (event) => {
      this._query = event.currentTarget.value;
      window.clearTimeout(this._searchTimer);

      this._searchTimer = window.setTimeout(() => {
        this._searchEntities();
      }, 300);
    });

    root.querySelector("#search-form")?.addEventListener("submit", (event) => {
      event.preventDefault();
      window.clearTimeout(this._searchTimer);
      this._query = input?.value ?? "";
      this._searchEntities();
    });

    root.querySelector("#refresh-search")?.addEventListener("click", () => {
      window.clearTimeout(this._searchTimer);
      this._query = input?.value ?? this._query;
      this._searchEntities({ refresh: true });
    });

    root.querySelector("#refresh-graph")?.addEventListener("click", () => {
      if (this._selectedEntityId) {
        this._loadGraph(this._selectedEntityId, { refresh: true });
      }
    });

    results?.addEventListener("click", (event) => {
      const target = event.target.closest("[data-select-entity]");
      const entityId = target?.getAttribute("data-select-entity");

      if (entityId) {
        this._loadGraph(entityId);
      }
    });

    graph?.addEventListener("click", (event) => {
      const moreInfo = event.target.closest("[data-more-info]");
      if (moreInfo) {
        const entityId = moreInfo.getAttribute("data-more-info");
        if (entityId) this._openMoreInfo(entityId);
        return;
      }

      const copy = event.target.closest("[data-copy-entity]");
      if (copy) {
        const entityId = copy.getAttribute("data-copy-entity");
        if (entityId) this._copyEntityId(entityId);
      }
    });
  }

  _resultSummary() {
    const shown = this._entities.length;
    const total = this._entityTotal;

    if (this._query.trim()) {
      return shown < total
        ? `Showing ${shown} of ${total} matches`
        : `${total} ${total === 1 ? "match" : "matches"}`;
    }

    return shown < total
      ? `Showing ${shown} of ${total} entities`
      : `${total} ${total === 1 ? "entity" : "entities"}`;
  }

  _renderStatus() {
    const error = this.shadowRoot?.querySelector("#error");
    const searchProgress = this.shadowRoot?.querySelector("#search-progress");
    const graphProgress = this.shadowRoot?.querySelector("#graph-progress");

    if (error) {
      error.hidden = !this._error;
      error.textContent = this._error ?? "";
    }

    if (searchProgress) {
      searchProgress.hidden = !this._loadingSearch;
    }

    if (graphProgress) {
      graphProgress.hidden = !this._loadingGraph;
    }
  }

  _renderResults() {
    const summary = this.shadowRoot?.querySelector("#result-summary");
    const results = this.shadowRoot?.querySelector("#entity-results");
    if (!summary || !results) return;

    summary.textContent = this._resultSummary();

    if (this._loadingSearch && !this._entities.length) {
      results.innerHTML = `
        <div class="empty small">Loading entities…</div>
      `;
      return;
    }

    if (!this._entities.length) {
      results.innerHTML = `
        <div class="empty small">No matching entities.</div>
      `;
      return;
    }

    results.innerHTML = this._entities
      .map((entity) => {
        const selected =
          entity.entity_id === this._selectedEntityId ? " selected" : "";
        const displayName = entity.display_name || entity.entity_id;
        const state = entity.state_display ?? entity.state;
        const stateText =
          state == null ? "" : `<span class="entity-state">${escapeHtml(state)}</span>`;

        return `
          <button
            class="entity-result${selected}"
            type="button"
            data-select-entity="${escapeHtml(entity.entity_id)}"
            title="${escapeHtml(entity.entity_id)}"
          >
            <span class="entity-result-main">
              <strong>${escapeHtml(displayName)}</strong>
              <span class="entity-id">${escapeHtml(entity.entity_id)}</span>
              ${stateText}
            </span>

            <span class="relation-counts" aria-label="Relationship counts">
              ↑ ${Number(entity.parent_count ?? 0)}
              ·
              ↓ ${Number(entity.child_count ?? 0)}
            </span>
          </button>
        `;
      })
      .join("");
  }

  _renderNode(node) {
    const state = node.runtime?.state_display ?? node.runtime?.state;
    const role = escapeHtml(roleLabel(node.roles));

    return `
      <article class="node-card ${node.broken ? "broken" : ""}">
        <div class="node-labels">
          <span class="badge">${role}</span>
          ${node.in_cycle ? '<span class="badge warning">Cycle</span>' : ""}
          ${node.broken ? '<span class="badge danger">Broken</span>' : ""}
        </div>

        <strong>${escapeHtml(node.display_name || node.id)}</strong>
        <code>${escapeHtml(node.id)}</code>
        ${state != null ? `<span class="node-state">${escapeHtml(state)}</span>` : ""}

        <div class="node-actions">
          <button type="button" data-more-info="${escapeHtml(node.id)}">
            More info
          </button>
          <button type="button" data-copy-entity="${escapeHtml(node.id)}">
            Copy ID
          </button>
        </div>
      </article>
    `;
  }

  _renderNodeColumn(title, description, nodes, emptyText) {
    return `
      <section class="graph-column">
        <div class="column-heading">
          <div>
            <h3>${escapeHtml(title)}</h3>
            <p>${escapeHtml(description)}</p>
          </div>
          <span class="count-badge">${nodes.length}</span>
        </div>

        <div class="node-list">
          ${
            nodes.length
              ? nodes.map((node) => this._renderNode(node)).join("")
              : `<div class="empty">${escapeHtml(emptyText)}</div>`
          }
        </div>
      </section>
    `;
  }

  _renderGraph() {
    const content = this.shadowRoot?.querySelector("#graph-content");
    const graphTitle = this.shadowRoot?.querySelector("#graph-title");
    const graphStats = this.shadowRoot?.querySelector("#graph-stats");
    const refreshButton = this.shadowRoot?.querySelector("#refresh-graph");

    if (!content || !graphTitle || !graphStats || !refreshButton) return;

    refreshButton.disabled = !this._selectedEntityId || this._loadingGraph;

    if (this._loadingGraph && !this._graph) {
      graphTitle.textContent = this._selectedEntityId ?? "Dependency graph";
      graphStats.textContent = "Loading graph…";
      content.innerHTML = `
        <div class="graph-empty">
          <div class="graph-symbol">⌁</div>
          <h2>Loading dependency graph</h2>
        </div>
      `;
      return;
    }

    if (!this._graph) {
      graphTitle.textContent = "Select an entity";
      graphStats.textContent = "";
      content.innerHTML = `
        <div class="graph-empty">
          <div class="graph-symbol">⌁</div>
          <h2>Select an entity</h2>
          <p>The first version shows its direct parents and children.</p>
        </div>
      `;
      return;
    }

    const nodes = this._graph.nodes ?? [];
    const parents = nodes.filter((node) => node.roles?.includes("parent"));
    const roots = nodes.filter((node) => node.roles?.includes("root"));
    const children = nodes.filter((node) => node.roles?.includes("child"));
    const statistics = this._graph.statistics ?? {};

    graphTitle.textContent = this._graph.root_id;
    graphStats.textContent =
      `${Number(statistics.node_count ?? nodes.length)} nodes · ` +
      `${Number(statistics.edge_count ?? 0)} edges`;

    content.innerHTML = `
      <div class="graph-columns">
        ${this._renderNodeColumn(
          "Parents",
          "Things the selected entity depends on.",
          parents,
          "No direct parents.",
        )}

        ${this._renderNodeColumn(
          "Selected",
          "The current centre of the graph.",
          roots,
          "Selected entity was not returned.",
        )}

        ${this._renderNodeColumn(
          "Children",
          "Things that depend on the selected entity.",
          children,
          "No direct children.",
        )}
      </div>

      <div class="milestone-note">
        Interactive zoom, pan, branch expansion, and full graph layout arrive
        in the next frontend milestone.
      </div>
    `;
  }

  _renderShell() {
    if (!this.shadowRoot) return;

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          box-sizing: border-box;
          min-height: 100%;
          color: var(--primary-text-color);
          background: var(--primary-background-color);
          font-family: var(--paper-font-body1_-_font-family, sans-serif);
        }

        *,
        *::before,
        *::after {
          box-sizing: border-box;
        }

        button,
        input {
          font: inherit;
        }

        button {
          color: var(--primary-text-color);
        }

        .page {
          min-height: 100vh;
          padding: 16px;
        }

        .page-header {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 14px;
        }

        .page-header h1 {
          margin: 0;
          font-size: 24px;
          line-height: 1.2;
        }

        .layout {
          display: grid;
          grid-template-columns: minmax(280px, 320px) minmax(0, 1fr);
          gap: 14px;
          height: calc(100vh - 88px);
          min-height: 520px;
        }

        .card {
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          background: var(--card-background-color);
          box-shadow: var(--ha-card-box-shadow, none);
        }

        .sidebar {
          display: flex;
          flex-direction: column;
          min-height: 0;
          overflow: hidden;
        }

        .search-section {
          flex: 0 0 auto;
          padding: 14px;
          border-bottom: 1px solid var(--divider-color);
        }

        #search-form {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 8px;
        }

        #entity-search {
          min-width: 0;
          height: 40px;
          padding: 0 12px;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          outline: none;
          color: var(--primary-text-color);
          background: var(--card-background-color);
        }

        #entity-search:focus {
          border-color: var(--primary-color);
          box-shadow: 0 0 0 2px color-mix(
            in srgb,
            var(--primary-color) 20%,
            transparent
          );
        }

        .primary-button {
          border: 0;
          border-radius: 8px;
          padding: 0 16px;
          color: var(--text-primary-color, white);
          background: var(--primary-color);
          cursor: pointer;
        }

        .search-meta {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          min-height: 38px;
          margin-top: 8px;
          color: var(--secondary-text-color);
          font-size: 13px;
        }

        .text-button,
        .node-actions button,
        #refresh-graph {
          min-height: 32px;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          padding: 4px 10px;
          background: transparent;
          cursor: pointer;
        }

        .text-button:hover,
        .node-actions button:hover,
        #refresh-graph:hover {
          background: var(--secondary-background-color);
        }

        .progress {
          height: 3px;
          overflow: hidden;
          background: color-mix(
            in srgb,
            var(--primary-color) 20%,
            transparent
          );
        }

        .progress::after {
          display: block;
          width: 35%;
          height: 100%;
          content: "";
          background: var(--primary-color);
          animation: progress 1s infinite ease-in-out;
        }

        .progress[hidden] {
          display: none;
        }

        @keyframes progress {
          from { transform: translateX(-100%); }
          to { transform: translateX(390%); }
        }

        .entity-results {
          flex: 1 1 auto;
          min-height: 0;
          overflow-x: hidden;
          overflow-y: auto;
          overscroll-behavior: contain;
          scrollbar-gutter: stable;
          touch-action: pan-y;
          padding: 8px;
        }

        .entity-result {
          display: flex;
          width: 100%;
          align-items: flex-start;
          justify-content: space-between;
          gap: 8px;
          margin: 0 0 5px;
          border: 1px solid transparent;
          border-radius: 8px;
          padding: 9px;
          text-align: left;
          background: transparent;
          cursor: pointer;
        }

        .entity-result:hover {
          background: var(--secondary-background-color);
        }

        .entity-result.selected {
          border-color: var(--primary-color);
          background: color-mix(
            in srgb,
            var(--primary-color) 8%,
            var(--card-background-color)
          );
        }

        .entity-result-main {
          display: flex;
          min-width: 0;
          flex-direction: column;
          gap: 2px;
        }

        .entity-result-main strong,
        .entity-id,
        .entity-state {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .entity-id,
        .entity-state,
        .relation-counts {
          color: var(--secondary-text-color);
          font-size: 12px;
        }

        .relation-counts {
          flex: 0 0 auto;
          white-space: nowrap;
        }

        .main-card {
          display: flex;
          min-width: 0;
          flex-direction: column;
          overflow: hidden;
        }

        .graph-header {
          display: flex;
          flex: 0 0 auto;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          min-height: 64px;
          padding: 12px 16px;
          border-bottom: 1px solid var(--divider-color);
        }

        .eyebrow {
          margin-bottom: 3px;
          color: var(--secondary-text-color);
          font-size: 11px;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }

        #graph-title {
          margin: 0;
          overflow-wrap: anywhere;
          font-size: 18px;
        }

        .graph-header-actions {
          display: flex;
          align-items: center;
          gap: 10px;
          white-space: nowrap;
        }

        #graph-stats {
          color: var(--secondary-text-color);
          font-size: 13px;
        }

        #graph-content {
          flex: 1 1 auto;
          min-height: 0;
          overflow: auto;
          padding: 14px;
        }

        .graph-columns {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 12px;
          min-height: 385px;
        }

        .graph-column {
          min-width: 0;
          border: 1px solid var(--divider-color);
          border-radius: 10px;
          padding: 12px;
          background: var(--secondary-background-color);
        }

        .column-heading {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 10px;
          margin-bottom: 12px;
        }

        .column-heading h3 {
          margin: 0 0 4px;
          font-size: 16px;
        }

        .column-heading p {
          margin: 0;
          color: var(--secondary-text-color);
          font-size: 13px;
        }

        .count-badge,
        .badge {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          border-radius: 999px;
          padding: 2px 8px;
          color: var(--primary-color);
          background: color-mix(
            in srgb,
            var(--primary-color) 12%,
            transparent
          );
          font-size: 12px;
        }

        .badge.warning {
          color: var(--warning-color, #b26a00);
        }

        .badge.danger {
          color: var(--error-color);
        }

        .node-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .node-card {
          display: flex;
          min-width: 0;
          flex-direction: column;
          gap: 7px;
          border: 1px solid var(--divider-color);
          border-radius: 9px;
          padding: 11px;
          background: var(--card-background-color);
        }

        .node-card.broken {
          border-color: var(--error-color);
        }

        .node-labels {
          display: flex;
          flex-wrap: wrap;
          gap: 5px;
        }

        .node-card strong,
        .node-card code,
        .node-state {
          overflow-wrap: anywhere;
        }

        .node-card code,
        .node-state {
          color: var(--secondary-text-color);
          font-size: 12px;
        }

        .node-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-top: 3px;
        }

        .empty,
        .graph-empty {
          display: flex;
          min-height: 150px;
          align-items: center;
          justify-content: center;
          flex-direction: column;
          color: var(--secondary-text-color);
          text-align: center;
        }

        .empty.small {
          min-height: 90px;
        }

        .graph-empty {
          min-height: 420px;
        }

        .graph-symbol {
          font-size: 48px;
        }

        .milestone-note {
          margin-top: 12px;
          border-top: 1px solid var(--divider-color);
          padding: 12px 0 0;
          color: var(--secondary-text-color);
          font-size: 12px;
        }

        #error {
          margin-bottom: 12px;
          border: 1px solid var(--error-color);
          border-radius: 8px;
          padding: 10px 12px;
          color: var(--error-color);
          background: color-mix(
            in srgb,
            var(--error-color) 8%,
            transparent
          );
        }

        #error[hidden] {
          display: none;
        }

        #copy-message {
          min-height: 20px;
          color: var(--secondary-text-color);
          font-size: 12px;
        }

        @media (max-width: 900px) {
          .page {
            padding: 10px;
          }

          .layout {
            display: flex;
            height: auto;
            min-height: 0;
            flex-direction: column;
          }

          .sidebar {
            min-height: 360px;
            max-height: 520px;
          }

          .main-card {
            min-height: 600px;
          }

          .graph-columns {
            grid-template-columns: 1fr;
          }

          .graph-header {
            align-items: flex-start;
            flex-direction: column;
          }
        }
      </style>

      <main class="page">
        <header class="page-header">
          <h1>Entity Dependency Engine</h1>
          <span class="badge">0.2.0 alpha.4</span>
        </header>

        <div id="error" hidden></div>

        <div class="layout">
          <aside class="card sidebar">
            <section class="search-section">
              <form id="search-form">
                <input
                  id="entity-search"
                  type="search"
                  placeholder="Search entity or friendly name"
                  autocomplete="off"
                  spellcheck="false"
                  aria-label="Search entity or friendly name"
                />
                <button class="primary-button" type="submit">Search</button>
              </form>

              <div class="search-meta">
                <span id="result-summary">0 entities</span>
                <button id="refresh-search" class="text-button" type="button">
                  Rebuild index
                </button>
              </div>

              <div id="search-progress" class="progress" hidden></div>
            </section>

            <div
              id="entity-results"
              class="entity-results"
              tabindex="0"
              aria-label="Entity search results"
            ></div>
          </aside>

          <section class="card main-card">
            <header class="graph-header">
              <div>
                <div class="eyebrow">Direct dependency graph</div>
                <h2 id="graph-title">Select an entity</h2>
              </div>

              <div class="graph-header-actions">
                <span id="graph-stats"></span>
                <button id="refresh-graph" type="button" disabled>
                  Refresh graph
                </button>
              </div>
            </header>

            <div id="graph-progress" class="progress" hidden></div>
            <div id="graph-content"></div>
          </section>
        </div>

        <div id="copy-message" aria-live="polite"></div>
      </main>
    `;

    this._renderResults();
    this._renderGraph();
    this._renderStatus();
  }
}

if (!customElements.get(PANEL_TAG)) {
  customElements.define(PANEL_TAG, EntityDependencyEnginePanel);
}
