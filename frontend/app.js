const state = {
  products: [],
  selectedId: null,
  autoRefresh: false,
  autoTimer: null,
};

const el = {
  productsList: document.getElementById("productsList"),
  productCount: document.getElementById("productCount"),
  refreshBtn: document.getElementById("refreshBtn"),
  autoBtn: document.getElementById("autoBtn"),
  apiStatus: document.getElementById("apiStatus"),
  statusDot: document.getElementById("statusDot"),
  focusTitle: document.getElementById("focusTitle"),
  focusId: document.getElementById("focusId"),
  focusCategory: document.getElementById("focusCategory"),
  focusBase: document.getElementById("focusBase"),
  focusCurrent: document.getElementById("focusCurrent"),
  focusDemand: document.getElementById("focusDemand"),
  focusReason: document.getElementById("focusReason"),
  eventLog: document.getElementById("eventLog"),
  recommendations: document.getElementById("recommendations"),
  toast: document.getElementById("toast"),
};

const money = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

function showToast(message, timeoutMs = 2200) {
  el.toast.textContent = message;
  el.toast.classList.add("show");
  window.setTimeout(() => el.toast.classList.remove("show"), timeoutMs);
}

function setApiStatus(isOk, text = "") {
  el.statusDot.classList.toggle("ok", Boolean(isOk));
  el.apiStatus.lastChild.textContent = text || (isOk ? "API connected" : "API disconnected");
}

function chipClass(reason) {
  const value = String(reason || "").toLowerCase();
  if (value.includes("high")) {
    return "chip chip-high";
  }
  if (value.includes("stable")) {
    return "chip chip-stable";
  }
  return "chip chip-low";
}

function cardTemplate(product, index) {
  const active = state.selectedId === product.product_id ? "active" : "";
  return `
    <article class="product-card ${active}" data-product-id="${product.product_id}" style="animation-delay:${Math.min(index * 30, 240)}ms;">
      <div class="line-1">
        <h3 class="name">${product.name}</h3>
        <span class="${chipClass(product.reason)}">${product.reason}</span>
      </div>
      <div class="meta">
        <div><b>Current</b>${money.format(product.current_price)}</div>
        <div><b>Base</b>${money.format(product.base_price)}</div>
        <div><b>Demand</b>${product.demand.toFixed(2)}</div>
        <div><b>Category</b>${product.category}</div>
      </div>
    </article>
  `;
}

function renderProducts() {
  el.productsList.innerHTML = state.products.map((p, i) => cardTemplate(p, i)).join("");
  el.productCount.textContent = `${state.products.length} items`;

  for (const card of el.productsList.querySelectorAll(".product-card")) {
    card.addEventListener("click", () => {
      const id = Number(card.dataset.productId);
      selectProduct(id);
    });
  }
}

function updateFocus(product) {
  if (!product) {
    el.focusTitle.textContent = "Select a product";
    el.focusId.textContent = "-";
    el.focusCategory.textContent = "-";
    el.focusBase.textContent = "-";
    el.focusCurrent.textContent = "-";
    el.focusDemand.textContent = "-";
    el.focusReason.textContent = "-";
    return;
  }

  el.focusTitle.textContent = product.name;
  el.focusId.textContent = String(product.product_id);
  el.focusCategory.textContent = product.category;
  el.focusBase.textContent = money.format(product.base_price);
  el.focusCurrent.textContent = money.format(product.current_price);
  el.focusDemand.textContent = product.demand.toFixed(2);
  el.focusReason.textContent = product.reason;
}

async function getJson(path, options) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed (${response.status})`);
  }

  return response.json();
}

async function loadProducts(keepSelection = true) {
  try {
    el.refreshBtn.disabled = true;
    const data = await getJson("/products");
    state.products = data.products || [];
    setApiStatus(true);

    if (!state.products.length) {
      state.selectedId = null;
      renderProducts();
      updateFocus(null);
      el.recommendations.textContent = "No products available.";
      return;
    }

    const hasSelection = keepSelection && state.products.some((p) => p.product_id === state.selectedId);
    state.selectedId = hasSelection ? state.selectedId : state.products[0].product_id;

    renderProducts();
    await selectProduct(state.selectedId, { silent: true });
  } catch (error) {
    setApiStatus(false, "API disconnected");
    showToast("Cannot load products. Is backend running?");
    console.error(error);
  } finally {
    el.refreshBtn.disabled = false;
  }
}

async function loadRecommendations(productId) {
  try {
    const data = await getJson(`/recommendations/${productId}?top_n=5`);
    const recs = data.recommendations || [];

    if (!recs.length) {
      el.recommendations.innerHTML = '<div class="muted">No recommendations in this category.</div>';
      return;
    }

    el.recommendations.innerHTML = recs
      .map(
        (rec) => `
          <article class="rec" data-product-id="${rec.product_id}">
            <strong>${rec.name}</strong><br />
            <span class="muted">Demand ${rec.demand.toFixed(2)} · ${money.format(rec.current_price)}</span>
          </article>
        `
      )
      .join("");

    for (const recEl of el.recommendations.querySelectorAll(".rec")) {
      recEl.addEventListener("click", () => {
        const nextId = Number(recEl.dataset.productId);
        selectProduct(nextId);
      });
    }
  } catch (error) {
    el.recommendations.innerHTML = '<div class="muted">Failed to load recommendations.</div>';
    console.error(error);
  }
}

async function selectProduct(productId, { silent = false } = {}) {
  state.selectedId = Number(productId);
  renderProducts();

  try {
    const data = await getJson(`/price/${state.selectedId}`);
    updateFocus(data);

    const index = state.products.findIndex((p) => p.product_id === state.selectedId);
    if (index !== -1) {
      state.products[index] = {
        ...state.products[index],
        ...data,
      };
      renderProducts();
    }

    await loadRecommendations(state.selectedId);

    if (!silent) {
      showToast(`Selected #${state.selectedId}`);
    }
  } catch (error) {
    showToast("Could not fetch product details.");
    console.error(error);
  }
}

function randomDemoUserId() {
  return Math.floor(Math.random() * 9000) + 1000;
}

async function sendEvent(action) {
  if (!state.selectedId) {
    showToast("Pick a product first.");
    return;
  }

  const payload = {
    product_id: state.selectedId,
    action,
    user_id: randomDemoUserId(),
  };

  const buttons = document.querySelectorAll(".event-btn");
  for (const button of buttons) {
    button.disabled = true;
  }

  try {
    const res = await getJson("/event", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    el.eventLog.textContent = [
      `Status: ${res.status}`,
      `Product: ${res.product_id}`,
      `Action: ${res.action}`,
      `Demand -> ${res.updated_demand}`,
      `Price -> ${money.format(res.updated_price)}`,
      `Reason -> ${res.reason}`,
      `At -> ${new Date(res.timestamp).toLocaleTimeString()}`,
    ].join("\n");

    showToast(`Event '${action}' recorded`);
    await loadProducts(true);
  } catch (error) {
    el.eventLog.textContent = "Failed to post event.";
    showToast("Event request failed.");
    console.error(error);
  } finally {
    for (const button of buttons) {
      button.disabled = false;
    }
  }
}

function toggleAutoRefresh() {
  state.autoRefresh = !state.autoRefresh;
  el.autoBtn.textContent = `Auto Refresh: ${state.autoRefresh ? "On" : "Off"}`;
  el.autoBtn.setAttribute("aria-pressed", String(state.autoRefresh));

  if (state.autoRefresh) {
    state.autoTimer = window.setInterval(() => {
      loadProducts(true);
    }, 8000);
  } else if (state.autoTimer) {
    window.clearInterval(state.autoTimer);
    state.autoTimer = null;
  }
}

function bindEvents() {
  el.refreshBtn.addEventListener("click", () => loadProducts(true));
  el.autoBtn.addEventListener("click", toggleAutoRefresh);

  for (const button of document.querySelectorAll(".event-btn")) {
    button.addEventListener("click", () => {
      sendEvent(button.dataset.action);
    });
  }
}

bindEvents();
loadProducts(false);
