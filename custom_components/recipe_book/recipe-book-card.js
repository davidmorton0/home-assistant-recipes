// The Recipe Book card: pick a category and a recipe, read it, mark it
// Attempted or Approved, edit or delete it, or add a new one.
//
//   type: custom:recipe-book-card
//
// Recipes come from the websocket command recipe_book/recipes. The card fetches
// them again whenever sensor.recipe_book is written, which the integration does
// after every save, status change, delete and reload. Changes go through the
// recipe_book services.

const SENSOR = "sensor.recipe_book";
const ALL = "All";
const UNCATEGORISED = "Uncategorised";
const STATUSES = ["Untested", "Attempted", "Approved"];
const DEFAULT_SERVES = 2;
const NEW_CATEGORY = "__new__";

const escape = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const byName = (a, b) => String(a).toLowerCase().localeCompare(String(b).toLowerCase());

class RecipeBookCard extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._recipes = [];
    this._loaded = false;
    this._category = ALL;
    this._uuid = null; // the recipe shown in Cook
    this._form = null; // { uuid: null for a new recipe, values: {...}, error, busy }
    this._message = null; // { kind: "success" | "error", text }
    this._confirmDelete = false;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    const state = hass.states[SENSOR];
    const stamp = state ? state.last_updated : null;
    if (stamp !== this._stamp) {
      this._stamp = stamp;
      this._fetch();
    }
    if (!this._rendered) this._render();
  }

  getCardSize() {
    return 10;
  }

  static getStubConfig() {
    return {};
  }

  // Data ----------------------------------------------------------------

  async _fetch() {
    try {
      const result = await this._hass.callWS({ type: "recipe_book/recipes" });
      this._recipes = result.recipes || [];
      this._loaded = true;
      this._loadError = null;
    } catch (err) {
      this._loadError = err?.message || String(err);
    }
    // A form being typed in is not redrawn, so its cursor stays put.
    if (!this._form) this._render();
  }

  _categories() {
    return [...new Set(this._recipes.map((r) => r.category))].sort(byName);
  }

  _inCategory() {
    return this._recipes
      .filter((r) => this._category === ALL || r.category === this._category)
      .sort((a, b) => byName(a.name, b.name));
  }

  _current() {
    const list = this._inCategory();
    return list.find((r) => r.uuid === this._uuid) || list[0] || null;
  }

  // Actions -------------------------------------------------------------

  _startAdd() {
    this._form = {
      uuid: null,
      values: { name: "", category: UNCATEGORISED, newCategory: "", serves: DEFAULT_SERVES, status: STATUSES[0], ingredients: "", steps: "" },
    };
    this._message = null;
    this._render();
  }

  _startEdit() {
    const r = this._current();
    if (!r) return;
    this._form = {
      uuid: r.uuid,
      values: {
        name: r.name,
        category: r.category,
        newCategory: "",
        serves: r.serves ?? DEFAULT_SERVES,
        status: r.status,
        ingredients: (r.ingredients || []).join("\n"),
        steps: (r.steps || []).join("\n"),
      },
    };
    this._message = null;
    this._confirmDelete = false;
    this._render();
  }

  _clearForm() {
    if (this._form.uuid) this._startEdit();
    else this._startAdd();
  }

  _closeForm() {
    this._form = null;
    this._render();
  }

  async _call(service, data) {
    await this._hass.callService("recipe_book", service, data);
  }

  async _save() {
    const form = this._form;
    const v = form.values;
    const category = v.category === NEW_CATEGORY ? v.newCategory.trim() : v.category;
    const data = {
      name: v.name.trim(),
      category: category || UNCATEGORISED,
      serves: Number(v.serves) || 0,
      status: v.status,
      ingredients: v.ingredients,
      steps: v.steps,
    };
    form.busy = true;
    form.error = null;
    this._render();
    try {
      if (form.uuid) await this._call("update_recipe", { uuid: form.uuid, ...data });
      else await this._call("add_recipe", data);
      this._form = null;
      this._message = { kind: "success", text: `Saved '${data.name}'.` };
      this._category = ALL;
      this._pendingName = data.name;
      await this._fetch();
      this._selectPending();
    } catch (err) {
      form.busy = false;
      form.error = err?.message || String(err);
    }
    this._render();
  }

  // After a save, show the saved recipe in Cook.
  _selectPending() {
    if (!this._pendingName) return;
    const found = this._recipes.find((r) => r.name === this._pendingName);
    if (found) this._uuid = found.uuid;
    this._pendingName = null;
  }

  async _setStatus(status) {
    const r = this._current();
    if (!r) return;
    try {
      await this._call("set_status", { uuid: r.uuid, status });
      this._message = null;
    } catch (err) {
      this._message = { kind: "error", text: err?.message || String(err) };
      this._render();
    }
  }

  async _delete() {
    const r = this._current();
    if (!r) return;
    this._confirmDelete = false;
    try {
      await this._call("delete_recipe", { uuid: r.uuid });
      this._uuid = null;
      this._message = { kind: "success", text: `Deleted '${r.name}'.` };
    } catch (err) {
      this._message = { kind: "error", text: err?.message || String(err) };
    }
    this._render();
  }

  // Rendering -----------------------------------------------------------

  _render() {
    if (!this.shadowRoot || !this._config) return;
    this._rendered = true;
    let body;
    if (this._loadError) body = `<div class="message error">${escape(this._loadError)}</div>`;
    else if (!this._loaded) body = `<div class="muted">Loading…</div>`;
    else if (this._form) body = this._formHtml();
    else body = this._cookHtml();
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card>${body}</ha-card>`;
    this._bind();
  }

  _messageHtml() {
    const m = this._message;
    return m ? `<div class="message ${m.kind}">${escape(m.text)}</div>` : "";
  }

  _cookHtml() {
    const list = this._inCategory();
    const r = this._current();
    if (r) this._uuid = r.uuid;
    const categories = [ALL, ...this._categories()];

    const pickers = `
      <div class="pickers">
        <label>Category<select data-pick="category">
          ${categories.map((c) => `<option value="${escape(c)}" ${c === this._category ? "selected" : ""}>${escape(c)}</option>`).join("")}
        </select></label>
        <label>Recipe<select data-pick="recipe" ${list.length ? "" : "disabled"}>
          ${list.length
            ? list.map((x) => `<option value="${escape(x.uuid)}" ${r && x.uuid === r.uuid ? "selected" : ""}>${escape(x.name)}</option>`).join("")
            : `<option>No recipes found</option>`}
        </select></label>
      </div>`;

    const recipe = r
      ? `
        <div class="recipe">
          <h1>${escape(r.name)}</h1>
          <div class="facts">
            <span><b>Category:</b> ${escape(r.category)}</span>
            ${r.serves !== undefined && r.serves !== null ? `<span><b>Serves:</b> ${escape(r.serves)}</span>` : ""}
            <span><b>Status:</b> <span class="status s-${escape(String(r.status).toLowerCase())}">${escape(r.status)}</span></span>
          </div>
          <h2>Ingredients</h2>
          <ul>${(r.ingredients || []).map((i) => `<li>${escape(i)}</li>`).join("")}</ul>
          <h2>Steps</h2>
          <ol>${(r.steps || []).map((s) => `<li>${escape(s)}</li>`).join("")}</ol>
        </div>`
      : `<div class="muted">No recipe selected.</div>`;

    const actions = r
      ? this._confirmDelete
        ? `
          <div class="confirm">
            <span>Delete <b>${escape(r.name)}</b>?</span>
            <span class="buttons">
              <button data-action="cancel-delete">Cancel</button>
              <button class="danger" data-action="confirm-delete">Delete</button>
            </span>
          </div>`
        : `
          <div class="actions">
            <button data-action="status" data-status="Attempted"><ha-icon icon="mdi:silverware-fork-knife"></ha-icon>Attempted</button>
            <button data-action="status" data-status="Approved"><ha-icon icon="mdi:check-circle"></ha-icon>Approved</button>
            <button data-action="edit"><ha-icon icon="mdi:pencil"></ha-icon>Edit</button>
            <button data-action="delete"><ha-icon icon="mdi:trash-can"></ha-icon>Delete</button>
          </div>`
      : "";

    return `
      <div class="head">
        ${pickers}
        <button class="primary" data-action="add"><ha-icon icon="mdi:plus"></ha-icon>Add recipe</button>
      </div>
      ${this._messageHtml()}
      ${recipe}
      ${actions}`;
  }

  _formHtml() {
    const { values: v, error, busy, uuid } = this._form;
    const categories = this._categories();
    if (!categories.includes(UNCATEGORISED)) categories.push(UNCATEGORISED);
    if (v.category !== NEW_CATEGORY && !categories.includes(v.category)) categories.push(v.category);
    categories.sort(byName);

    return `
      <form>
        <div class="form-title">${uuid ? "Edit recipe" : "New recipe"}</div>
        <label>Name<input name="name" value="${escape(v.name)}" maxlength="100" required></label>
        <div class="pair">
          <label>Category<select name="category">
            ${categories.map((c) => `<option value="${escape(c)}" ${c === v.category ? "selected" : ""}>${escape(c)}</option>`).join("")}
            <option value="${NEW_CATEGORY}" ${v.category === NEW_CATEGORY ? "selected" : ""}>New category…</option>
          </select></label>
          <label class="new-category" ${v.category === NEW_CATEGORY ? "" : "hidden"}>New category<input name="newCategory" value="${escape(v.newCategory)}" maxlength="100"></label>
        </div>
        <div class="pair">
          <label>Serves<input name="serves" type="number" min="0" max="100" step="1" inputmode="numeric" value="${escape(v.serves)}"></label>
          <label>Status<select name="status">
            ${STATUSES.map((s) => `<option value="${s}" ${s === v.status ? "selected" : ""}>${s}</option>`).join("")}
          </select></label>
        </div>
        <label>Ingredients<textarea name="ingredients" rows="6" placeholder="One ingredient per line">${escape(v.ingredients)}</textarea></label>
        <label>Steps<textarea name="steps" rows="8" placeholder="One step per line">${escape(v.steps)}</textarea></label>
        ${error ? `<div class="message error">${escape(error)}</div>` : ""}
        <div class="form-actions">
          <button type="button" data-action="clear-form" ${busy ? "disabled" : ""}>${uuid ? "Undo changes" : "Clear"}</button>
          <button type="button" data-action="close-form" ${busy ? "disabled" : ""}>Cancel</button>
          <button type="submit" class="primary" ${busy ? "disabled" : ""}>${busy ? "Saving…" : uuid ? "Save changes" : "Save recipe"}</button>
        </div>
      </form>`;
  }

  _bind() {
    const root = this.shadowRoot;
    root.querySelectorAll("[data-action]").forEach((el) =>
      el.addEventListener("click", (event) => {
        event.preventDefault();
        const { action } = el.dataset;
        if (action === "add") this._startAdd();
        else if (action === "edit") this._startEdit();
        else if (action === "status") this._setStatus(el.dataset.status);
        else if (action === "delete") { this._confirmDelete = true; this._render(); }
        else if (action === "cancel-delete") { this._confirmDelete = false; this._render(); }
        else if (action === "confirm-delete") this._delete();
        else if (action === "clear-form") this._clearForm();
        else if (action === "close-form") this._closeForm();
      })
    );
    root.querySelectorAll("select[data-pick]").forEach((select) =>
      select.addEventListener("change", () => {
        if (select.dataset.pick === "category") {
          this._category = select.value;
          this._uuid = null;
        } else {
          this._uuid = select.value;
        }
        this._message = null;
        this._confirmDelete = false;
        this._render();
      })
    );
    const form = root.querySelector("form");
    if (form) {
      // Typing only stores the value; nothing is redrawn, so the cursor stays put.
      form.addEventListener("input", (event) => {
        this._form.values[event.target.name] = event.target.value;
      });
      form.querySelector("select[name=category]").addEventListener("change", (event) => {
        this._form.values.category = event.target.value;
        form.querySelector(".new-category").hidden = event.target.value !== NEW_CATEGORY;
      });
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        this._save();
      });
    }
  }
}

const STYLE = `
  ha-card { padding: 16px; }
  .head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-end; gap: 12px; }
  .pickers { display: flex; flex-wrap: wrap; gap: 12px; flex: 1 1 20em; }
  .pickers label { flex: 1 1 10em; }
  .recipe h1 { font-size: 1.6em; font-weight: 500; margin: 16px 0 8px; }
  .recipe h2 { font-size: 1.15em; font-weight: 500; margin: 16px 0 4px; }
  .recipe ul, .recipe ol { margin: 0; padding-left: 1.4em; line-height: 1.5; }
  .recipe li { margin: 4px 0; }
  .facts { display: flex; flex-wrap: wrap; gap: 4px 16px; color: var(--secondary-text-color); }
  .facts b { color: var(--primary-text-color); font-weight: 500; }
  .status.s-approved { color: var(--success-color); }
  .status.s-attempted { color: var(--warning-color); }
  .actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
  .confirm { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px; margin-top: 16px; padding: 8px; border-radius: 6px; background: color-mix(in srgb, var(--error-color) 10%, transparent); }
  .buttons { display: flex; gap: 8px; }
  .muted { color: var(--secondary-text-color); font-style: italic; padding: 8px 0; }
  .message { padding: 8px 0; font-weight: 500; }
  .message.error { color: var(--error-color); }
  .message.success { color: var(--success-color); }
  button { font: inherit; cursor: pointer; border: 1px solid var(--divider-color); background: none; color: var(--primary-text-color); border-radius: 6px; padding: 8px 14px; display: inline-flex; align-items: center; gap: 6px; }
  button:disabled { opacity: 0.5; cursor: default; }
  button.primary { background: var(--primary-color); border-color: var(--primary-color); color: var(--text-primary-color, #fff); }
  button.danger { background: var(--error-color); border-color: var(--error-color); color: #fff; }
  ha-icon { --mdc-icon-size: 20px; }
  form { display: grid; gap: 10px; }
  .form-title { font-size: 1.2em; font-weight: 500; }
  label { display: flex; flex-direction: column; font-size: 0.85em; color: var(--secondary-text-color); gap: 2px; }
  label[hidden] { display: none; }
  input, select, textarea { font: inherit; font-size: 1rem; padding: 8px; border: 1px solid var(--divider-color); border-radius: 6px; background: var(--card-background-color); color: var(--primary-text-color); min-width: 0; }
  textarea { resize: vertical; line-height: 1.4; }
  .pair { display: grid; grid-template-columns: repeat(auto-fit, minmax(10em, 1fr)); gap: 10px; }
  .form-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
`;

customElements.get("recipe-book-card") || customElements.define("recipe-book-card", RecipeBookCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "recipe-book-card", name: "Recipe Book", description: "Browse, add, edit and delete recipes." });
