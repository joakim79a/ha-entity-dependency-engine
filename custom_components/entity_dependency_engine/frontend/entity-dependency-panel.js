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
    this._graph = undefined;
    this._selectedEntityId = undefined;
    this._loading = false;
    this._error = undefined;
    this._initialized = false;
  }

  set hass(value) {
    this._hass = value;
    this._render();
    if (value && !this._initialized) {
      this._initialized = true;
      queueMicrotask(() => this._searchEntities());
    }
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
    this._render();
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
    this._loading = true;
    this._error = undefined;
    this._render();

    try {
      const result = await this._callWS({
        type: "entity_dependency_engine/search_entities",
        query: this._query.trim(),
        limit: 50,
        refresh,
      });
      this._entities = result.entities ?? [];
    } catch (error) {
      this._entities = [];
      this._error = error?.message ?? String(error);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _loadGraph(entityId, { refresh = false } = {}) {
    this._selectedEntityId = entityId;
    this._loading = true;
    this._error = undefined;
    this._render();

    try {
      this._graph = await this._callWS({
        type: "entity_dependency_engine/get_graph",
        entity_id: entityId,
        scope: "direct",
        max_nodes: 250,
        include_structural: false,
        refresh,
      });
    } catch (error) {
      this._graph = undefined;
      this._error = error?.message ?? String(error);
    } finally {
      this._loading = false;
      this._render();
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
  }

  _bindEvents() {
    const root = this.shadowRoot;
    if (!root) return;

    root.querySelector("#search-form")?.addEventListener("submit", (event) => {
      event.preventDefault();
      this._query = root.querySelector("#entity-search")?.value ?? "";
      this._searchEntities();
    });

    root.querySelector("#refresh-search")?.addEventListener("click", () => {
      this._query = root.querySelector("#entity-search")?.value ?? this._query;
      this._searchEntities({ refresh: true });
    });

    root.querySelector("#refresh-graph")?.addEventListener("click", () => {
      if (this._selectedEntityId) {
        this._loadGraph(this._selectedEntityId, { refresh: true });
      }
    });

    root.querySelectorAll("[data-select-entity]").forEach((element) => {
      element.addEventListener("click", () => {
        const entityId = element.getAttribute("data-select-entity");
        if (entityId) this._loadGraph(entityId);
      });
    });

    root.querySelectorAll("[data-more-info]").forEach((element) => {
      element.addEventListener("click", (event) => {
        event.stopPropagation();
        const entityId = element.getAttribute("data-more-info");
        if (entityId) this._openMoreInfo(entityId);
      });
    });

    root.querySelectorAll("[data-copy-entity]").forEach((element) => {
      element.addEventListener("click", (event) => {
        event.stopPropagation();
        const entityId = element.getAttribute("data-copy-entity");
        if (entityId) this._copyEntityId(entityId);
      });
    });
  }

  _renderEntityResults() {
    if (this._loading && !this._entities.length) {
      return '<div class="empty">Loading entities…</div>';
    }

    if (!this._entities.length) {
      return '<div class="empty">No matching entities.</div>';
    }

    return this._entities
      .map(
        (entity) => `
          <button
            class="entity-row ${
              entity.entity_id === this._selectedEntityId ? "selected" : ""
            }"
            type="button"
            data-select-entity="${escapeHtml(entity.entity_id)}"
          >
            <span class="entity-main">
              <strong>${escapeHtml(entity.display_name || entity.entity_id)}</strong>
              <span>${escapeHtml(entity.entity_id)}</span>
            </span>
            <span class="entity-counts" title="Parents / children">
              ↑ ${Number(entity.parent_count ?? 0)} · ↓ ${Number(
                entity.child_count ?? 0,
              )}
            </span>
          </button>
        `,
      )
      .join("");
  }

  _renderNode(node) {
    const state = node.runtime?.state_display ?? node.runtime?.state;
    return `
      <article class="node ${node.roles?.includes("root") ? "root" : ""} ${
        node.broken ? "broken" : ""
      }">
        <div class="node-heading">
          <span class="role">${escapeHtml(roleLabel(node.roles))}</span>
          ${node.in_cycle ? '<span class="warning">Cycle</span>' : ""}
          ${node.broken ? '<span class="warning">Broken</span>' : ""}
        </div>
        <strong>${escapeHtml(node.display_name || node.id)}</strong>
        <code>${escapeHtml(node.id)}</code>
        ${state != null ? `<span class="state">${escapeHtml(state)}</span>` : ""}
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

  _renderGraph() {
    if (!this._graph) {
      return `
        <section class="graph-empty">
          <div class="graph-placeholder">⌁</div>
          <h2>Select an entity</h2>
          <p>The first version shows its direct parents and children.</p>
        </section>
      `;
    }

    const nodes = this._graph.nodes ?? [];
    const parents = nodes.filter((node) => node.roles?.includes("parent"));
    const roots = nodes.filter((node) => node.roles?.includes("root"));
    const children = nodes.filter((node) => node.roles?.includes("child"));
    const statistics = this._graph.statistics ?? {};

    return `
      <section class="graph-section">
        <header class="graph-header">
          <div>
            <span class="eyebrow">Direct dependency graph</span>
            <h2>${escapeHtml(this._graph.root_id)}</h2>
          </div>
          <div class="graph-actions">
            <span>${Number(statistics.node_count ?? nodes.length)} nodes</span>
            <span>${Number(statistics.edge_count ?? 0)} edges</span>
            <button id="refresh-graph" type="button">Refresh graph</button>
          </div>
        </header>

        <div class="graph-grid">
          <section class="lane parents">
            <h3>Parents <span>${parents.length}</span></h3>
            <p>Things the selected entity depends on.</p>
            <div class="node-list">
              ${
                parents.length
                  ? parents.map((node) => this._renderNode(node)).join("")
                  : '<div class="empty compact">No direct parents.</div>'
              }
            </div>
          </section>

          <section class="lane root-lane">
            <h3>Selected <span>${roots.length}</span></h3>
            <p>The current centre of the graph.</p>
            <div class="node-list">
              ${roots.map((node) => this._renderNode(node)).join("")}
            </div>
          </section>

          <section class="lane children">
            <h3>Children <span>${children.length}</span></h3>
            <p>Things that depend on the selected entity.</p>
            <div class="node-list">
              ${
                children.length
                  ? children.map((node) => this._renderNode(node)).join("")
                  : '<div class="empty compact">No direct children.</div>'
              }
            </div>
          </section>
        </div>

        <footer class="alpha-note">
          Interactive zoom, pan, branch expansion and full graph layout arrive in
          the next frontend milestone.
        </footer>
      </section>
    `;
  }

  _render() {
    if (!this.shadowRoot) return;

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          min-height: 100%;
          color: var(--primary-text-color);
          background: var(--primary-background-color);
          font-family: var(--paper-font-body1_-_font-family, sans-serif);
          box-sizing: border-box;
        }

        * { box-sizing: border-box; }
        button, input { font: inherit; }

        .page {
          min-height: 100vh;
          padding: 20px;
        }

        .topbar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          margin-bottom: 16px;
        }

        .title-group {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        h1, h2, h3, p { margin: 0; }
        h1 { font-size: 24px; }
        h2 { font-size: 20px; }
        h3 { font-size: 16px; }

        .badge,
        .role,
        .warning,
        .graph-actions span,
        .lane h3 span {
          display: inline-flex;
          align-items: center;
          border-radius: 999px;
          padding: 3px 8px;
          font-size: 12px;
          font-weight: 600;
        }

        .badge,
        .role,
        .lane h3 span {
          color: var(--primary-color);
          background: color-mix(in srgb, var(--primary-color) 12%, transparent);
        }

        .warning {
          color: var(--warning-color, #f0a000);
          background: color-mix(
            in srgb,
            var(--warning-color, #f0a000) 14%,
            transparent
          );
        }

        .workspace {
          display: grid;
          grid-template-columns: minmax(260px, 340px) minmax(0, 1fr);
          gap: 16px;
          align-items: start;
        }

        .sidebar,
        .graph-section,
        .graph-empty {
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 12px);
          box-shadow: var(--ha-card-box-shadow, none);
        }

        .sidebar {
          position: sticky;
          top: 16px;
          overflow: hidden;
        }

        .search-wrap {
          padding: 16px;
          border-bottom: 1px solid var(--divider-color);
        }

        form {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 8px;
        }

        input {
          width: 100%;
          min-width: 0;
          padding: 10px 12px;
          color: var(--primary-text-color);
          background: var(--primary-background-color);
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          outline: none;
        }

        input:focus {
          border-color: var(--primary-color);
          box-shadow: 0 0 0 2px
            color-mix(in srgb, var(--primary-color) 18%, transparent);
        }

        button {
          cursor: pointer;
          color: var(--primary-text-color);
          background: transparent;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          padding: 9px 12px;
        }

        button:hover {
          background: color-mix(
            in srgb,
            var(--primary-text-color) 7%,
            transparent
          );
        }

        button.primary {
          color: var(--text-primary-color, white);
          background: var(--primary-color);
          border-color: var(--primary-color);
        }

        .sidebar-tools {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          margin-top: 10px;
          color: var(--secondary-text-color);
          font-size: 12px;
        }

        .entity-results {
          max-height: calc(100vh - 230px);
          overflow: auto;
          padding: 8px;
        }

        .entity-row {
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          margin: 0 0 6px;
          padding: 10px;
          text-align: left;
          border-color: transparent;
        }

        .entity-row.selected {
          border-color: var(--primary-color);
          background: color-mix(in srgb, var(--primary-color) 10%, transparent);
        }

        .entity-main {
          min-width: 0;
          display: grid;
          gap: 3px;
        }

        .entity-main strong,
        .entity-main span {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .entity-main span,
        .entity-counts,
        .state,
        .lane p,
        .alpha-note,
        .empty {
          color: var(--secondary-text-color);
        }

        .entity-main span,
        .entity-counts { font-size: 12px; }
        .entity-counts { white-space: nowrap; }

        .error {
          margin-bottom: 16px;
          padding: 12px 14px;
          color: var(--error-color, #db4437);
          background: color-mix(
            in srgb,
            var(--error-color, #db4437) 10%,
            var(--card-background-color)
          );
          border: 1px solid var(--error-color, #db4437);
          border-radius: 8px;
        }

        .graph-empty {
          min-height: 520px;
          display: grid;
          place-content: center;
          justify-items: center;
          gap: 8px;
          text-align: center;
          padding: 32px;
        }

        .graph-placeholder {
          font-size: 72px;
          color: var(--primary-color);
          line-height: 1;
        }

        .graph-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          padding: 16px 18px;
          border-bottom: 1px solid var(--divider-color);
        }

        .eyebrow {
          display: block;
          margin-bottom: 4px;
          color: var(--secondary-text-color);
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.06em;
        }

        .graph-actions {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          justify-content: flex-end;
          gap: 8px;
        }

        .graph-actions span {
          color: var(--secondary-text-color);
          background: var(--secondary-background-color);
        }

        .graph-grid {
          min-height: 480px;
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 14px;
          padding: 16px;
        }

        .lane {
          min-width: 0;
          padding: 14px;
          background: var(--secondary-background-color);
          border: 1px solid var(--divider-color);
          border-radius: 10px;
        }

        .lane h3 {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
        }

        .lane p {
          min-height: 36px;
          margin: 5px 0 12px;
          font-size: 13px;
        }

        .node-list {
          display: grid;
          gap: 10px;
        }

        .node {
          display: grid;
          gap: 7px;
          padding: 12px;
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: 10px;
        }

        .node.root {
          border-color: var(--primary-color);
          box-shadow: 0 0 0 1px var(--primary-color);
        }

        .node.broken {
          border-style: dashed;
          border-color: var(--warning-color, #f0a000);
        }

        .node-heading {
          display: flex;
          flex-wrap: wrap;
          gap: 5px;
        }

        .node code {
          overflow-wrap: anywhere;
          color: var(--secondary-text-color);
          font-size: 12px;
        }

        .state { font-size: 13px; }

        .node-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-top: 2px;
        }

        .node-actions button {
          padding: 6px 8px;
          font-size: 12px;
        }

        .alpha-note {
          padding: 12px 16px;
          border-top: 1px solid var(--divider-color);
          font-size: 12px;
        }

        .empty {
          padding: 20px 12px;
          text-align: center;
        }

        .empty.compact { padding: 12px 6px; }

        .loading-line {
          height: 3px;
          background: linear-gradient(
            90deg,
            transparent,
            var(--primary-color),
            transparent
          );
          background-size: 200% 100%;
          animation: loading 1s linear infinite;
        }

        @keyframes loading {
          from { background-position: 200% 0; }
          to { background-position: -200% 0; }
        }

        @media (max-width: 980px) {
          .page { padding: 12px; }
          .workspace { grid-template-columns: 1fr; }
          .sidebar { position: static; }
          .entity-results { max-height: 340px; }
          .graph-grid { grid-template-columns: 1fr; }
          .graph-header { align-items: flex-start; flex-direction: column; }
          .graph-actions { justify-content: flex-start; }
        }
      </style>

      <main class="page">
        <header class="topbar">
          <div class="title-group">
            <h1>Entity Dependency Engine</h1>
            <span class="badge">0.2.0 alpha</span>
          </div>
        </header>

        ${this._error ? `<div class="error">${escapeHtml(this._error)}</div>` : ""}

        <div class="workspace">
          <aside class="sidebar">
            <div class="search-wrap">
              <form id="search-form">
                <input
                  id="entity-search"
                  type="search"
                  placeholder="Search entity or friendly name"
                  value="${escapeHtml(this._query)}"
                  aria-label="Search entities"
                />
                <button class="primary" type="submit">Search</button>
              </form>
              <div class="sidebar-tools">
                <span>${this._entities.length} results</span>
                <button id="refresh-search" type="button">Rebuild index</button>
              </div>
            </div>
            ${this._loading ? '<div class="loading-line"></div>' : ""}
            <div class="entity-results">${this._renderEntityResults()}</div>
          </aside>

          ${this._renderGraph()}
        </div>
      </main>
    `;

    this._bindEvents();
  }
}

if (!customElements.get(PANEL_TAG)) {
  customElements.define(PANEL_TAG, EntityDependencyEnginePanel);
}
