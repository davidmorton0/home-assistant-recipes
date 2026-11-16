// The Recipes sidebar page: the recipe-book-card, full width, under a toolbar.

import "./recipe-book-card.js";

class RecipeBookPanel extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (!this._built) this._build();
    this._menu.hass = hass;
    this._card.hass = hass;
  }

  set narrow(narrow) {
    this._narrow = narrow;
    if (this._menu) this._menu.narrow = narrow;
  }

  set panel(_panel) {}

  _build() {
    this._built = true;
    const root = this.attachShadow({ mode: "open" });
    root.innerHTML = `
      <style>
        :host { display: block; background: var(--primary-background-color); min-height: 100vh; }
        .toolbar { display: flex; align-items: center; height: var(--header-height, 56px); padding: 0 12px; gap: 12px;
          background: var(--app-header-background-color); color: var(--app-header-text-color, var(--text-primary-color));
          border-bottom: var(--app-header-border-bottom, none); font-size: 20px; }
        .content { max-width: 900px; margin: 0 auto; padding: 16px; box-sizing: border-box; }
      </style>
      <div class="toolbar"><span class="menu"></span><div class="title">Recipes</div></div>
      <div class="content"></div>`;

    this._menu = document.createElement("ha-menu-button");
    this._menu.narrow = this._narrow;
    root.querySelector(".menu").appendChild(this._menu);

    this._card = document.createElement("recipe-book-card");
    this._card.setConfig({});
    root.querySelector(".content").appendChild(this._card);
  }
}

customElements.get("recipe-book-panel") || customElements.define("recipe-book-panel", RecipeBookPanel);
