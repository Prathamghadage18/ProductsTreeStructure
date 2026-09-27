// treeApp-events.js
// Event handlers for TreeApp

// Minimal cookie reader for CSRF token
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
  return null;
}

TreeApp.prototype.handleFileChange = function (e) {
  this.selectedFile = e.target.files[0];
  const uploadBtn = document.getElementById("upload-btn");
  uploadBtn.disabled = !this.selectedFile;
};

// Load tree from database (auto-called on page load for both superuser and normal users)
TreeApp.prototype.loadTreeFromDatabase = async function () {
  try {
    this.uploadLoading = true;
    this.uploadError = null;
    this.render();

    const res = await fetch("/api/tree/data/", {
      method: "GET",
      credentials: "same-origin",
    });

    if (!res.ok) {
      const t = await res.text().catch(() => res.statusText);
      throw new Error(`Status ${res.status} — ${t}`);
    }

    const rawText = await res.text();
    const safeText = rawText.replace(/\bNaN\b/g, "null");
    const json = JSON.parse(safeText);

    // Normalize the data (handles hierarchical tree structure)
    const normalized = normalizeData(json);

    if (!normalized || Object.keys(normalized).length === 0) {
      throw new Error(
        "No tree data in database. Superuser must upload Excel file first."
      );
    }

    // Set tree data and reset state
    this.data = normalized;
    this.expandedSet = new Set();
    this.activeExpandedNode = null;
    this.specialParents = new Set();
    this.search = "";
    this.spreadNodeId = null;
    this.layoutMode = "horizontal";

    this.uploadLoading = false;
    this.render();
    this.computeLayout();

    console.log("✅ Tree loaded from database successfully");
  } catch (err) {
    console.error("Failed to load tree from database:", err);
    this.uploadError =
      err.message ||
      "No data in database. Superuser must upload Excel file first.";
    this.uploadLoading = false;
    this.render();
  }
};

TreeApp.prototype.handleUpload = async function () {
  if (!this.selectedFile) return;

  // Check if user is superuser (read from template)
  const isSuperuser =
    document.querySelector("[data-is-superuser]")?.dataset?.isSuperuser ===
    "true";
  const endpoint = isSuperuser
    ? "/api/tree/upload-permanent/"
    : "/api/tree/upload/";

  // Show confirmation for superuser permanent upload
  if (isSuperuser) {
    if (
      !confirm(
        "⚠️ This will PERMANENTLY save data to the database.\n\nThis can only be done ONCE.\n\nContinue?"
      )
    ) {
      return;
    }
  }

  try {
    this.uploadLoading = true;
    this.uploadError = null;
    this.render();

    const formData = new FormData();
    formData.append("file", this.selectedFile);
    const csrftoken = getCookie("csrftoken");

    const res = await fetch(endpoint, {
      method: "POST",
      body: formData,
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": csrftoken || "",
      },
    });

    if (!res.ok) {
      const errorData = await res
        .json()
        .catch(() => ({ error: res.statusText }));
      throw new Error(errorData.error || `Status ${res.status}`);
    }

    const rawText = await res.text();
    const safeText = rawText.replace(/\bNaN\b/g, "null");
    const json = JSON.parse(safeText);

    // For superuser permanent upload, reload from database
    if (isSuperuser) {
      alert(
        "✅ Data saved to database successfully!\n\nTree will now reload from database."
      );
      await this.loadTreeFromDatabase();
      return;
    }

    // For normal users, show the uploaded tree temporarily (view-only)
    const normalized = normalizeData(json);

    if (!normalized || Object.keys(normalized).length === 0) {
      throw new Error("Empty tree data received from uploaded file");
    }

    // Reset states for new tree
    this.data = normalized;
    this.expandedSet = new Set();
    this.activeExpandedNode = null;
    this.specialParents = new Set();
    this.search = "";
    this.spreadNodeId = null;
    this.layoutMode = "horizontal";

    this.uploadLoading = false;
    this.render();
    this.computeLayout();

    console.log("✅ Tree uploaded for viewing (not saved to database)");
  } catch (err) {
    console.error("Failed to upload tree data:", err);
    this.uploadError = err.message || "Unknown error while uploading data";
    this.uploadLoading = false;
    this.render();
  }
};

TreeApp.prototype.onExpandNext = function () {
  const levels = buildVisibleLevels(this.data, this.expandedSet, this.search);
  if (!levels || levels.length === 0) return;

  const lastLevel = levels[levels.length - 1];
  const idsToExpand = lastLevel
    .filter((n) => n.children && Object.keys(n.children).length > 0)
    .map((n) => n.id);

  if (idsToExpand.length === 0) return;

  idsToExpand.forEach((id) => this.expandedSet.add(id));
  this.specialParents = new Set(idsToExpand);
  this.activeExpandedNode = null;

  this.render();
  this.computeLayout();
};

TreeApp.prototype.onCollapsePrev = function () {
  const levels = buildVisibleLevels(this.data, this.expandedSet, this.search);
  if (!levels || levels.length <= 1) return;

  const parentLevelIndex = levels.length - 2;
  const parentLevel = levels[parentLevelIndex];

  for (const node of parentLevel) {
    this.expandedSet.delete(node.id);
    collapseChildrenRecursivelyInData(this.data, node.id, this.expandedSet);
  }

  // Determine parents of these parent-level nodes (one level up)
  const parents = new Set();
  for (const node of parentLevel) {
    const path = findPathToNode(this.data, node.id) || [];
    if (path && path.length >= 2) {
      const parentNode = path[path.length - 2];
      if (parentNode && parentNode.id) parents.add(parentNode.id);
    }
  }

  this.specialParents = parents;

  const firstParent = parents.values().next();
  if (!firstParent.done) {
    this.activeExpandedNode = firstParent.value;
  } else {
    this.activeExpandedNode = null;
  }

  this.render();
  this.computeLayout();
};

TreeApp.prototype.onExpandToggle = function (node) {
  const nodeId = node.id;
  const wasExpanded = this.expandedSet.has(nodeId);

  if (wasExpanded) {
    // Store previously expanded descendants for restore later
    const allDesc = this.collectDescendantIds(nodeId);
    const expandedDesc = allDesc.filter((id) => this.expandedSet.has(id));
    if (expandedDesc.length > 0) {
      this.prevExpandedByNode.set(nodeId, new Set(expandedDesc));
    }

    // Collapse node and all descendants
    this.expandedSet.delete(nodeId);
    this.collapseChildrenRecursively(nodeId);

    // Update active highlight to parent if any
    const path = findPathToNode(this.data, nodeId) || [];
    if (path && path.length >= 2) {
      const parentNode = path[path.length - 2];
      this.activeExpandedNode = parentNode ? parentNode.id : null;
    } else if (this.activeExpandedNode === nodeId) {
      this.activeExpandedNode = null;
    }
  } else {
    // Expand node and restore previously expanded descendants if present
    this.expandedSet.add(nodeId);
    const saved = this.prevExpandedByNode.get(nodeId);
    if (saved && saved.size > 0) {
      for (const id of saved) this.expandedSet.add(id);
      this.prevExpandedByNode.delete(nodeId);
    }
    this.activeExpandedNode = nodeId;
  }

  this.render();
  this.computeLayout();
};

TreeApp.prototype.onSpreadToggle = function (node) {
  if (this.spreadNodeId === node.id) {
    this.spreadNodeId = null;
    setTimeout(() => {
      const prev = this.prevScroll || { left: 0, top: 0 };
      this.containerEl.scrollTo({
        left: prev.left,
        top: prev.top,
        behavior: "smooth",
      });
    }, 120);
  } else {
    this.prevScroll = {
      left: this.containerEl.scrollLeft,
      top: this.containerEl.scrollTop,
    };
    this.spreadNodeId = node.id;

    // Focus on spread node after layout
    setTimeout(() => this.focusOnSpreadNode(), 120);
  }

  this.render();
  this.computeLayout();
};

TreeApp.prototype.focusOnSpreadNode = function () {
  if (!this.spreadNodeId || !this.containerEl) return;

  const nodeEl = this.containerEl.querySelector(
    `[data-node-id="${this.spreadNodeId}"]`
  );
  if (!nodeEl) return;

  const containerRect = this.containerEl.getBoundingClientRect();
  const elRect = nodeEl.getBoundingClientRect();

  const elLeftWithinContent =
    elRect.left - containerRect.left + this.containerEl.scrollLeft;
  const elTopWithinContent =
    elRect.top - containerRect.top + this.containerEl.scrollTop;

  const desiredLeftWithinContent = LEFT_MARGIN;
  const desiredTopWithinContent = Math.max(
    0,
    elTopWithinContent - this.containerEl.clientHeight / 2 + elRect.height / 2
  );

  const newScrollLeft = Math.max(
    0,
    Math.round(elLeftWithinContent - desiredLeftWithinContent)
  );
  const newScrollTop = Math.max(0, Math.round(desiredTopWithinContent));

  this.containerEl.scrollTo({
    left: newScrollLeft,
    top: newScrollTop,
    behavior: "smooth",
  });
};

// -------------------------
// Problem-based search helpers
// -------------------------

TreeApp.prototype.initProblemSearch = async function () {
  try {
    const catSel = document.getElementById("fault-category");
    const subSel = document.getElementById("fault-subcategory");
    const btn = document.getElementById("fault-search-btn");
    if (!catSel || !subSel || !btn) return;

    // Fetch schema
    const res = await fetch("/api/faults/schema/");
    if (!res.ok) throw new Error("Failed to load fault schema");
    const data = await res.json();
    const cats = data.categories || [];
    this._faultSchema = cats;

    // Populate categories
    cats.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.name;
      opt.textContent = c.name;
      catSel.appendChild(opt);
    });

    catSel.addEventListener("change", () => {
      subSel.innerHTML = '<option value="">Select a sub-category...</option>';
      const cat = catSel.value;
      if (!cat) {
        subSel.disabled = true;
        btn.disabled = true;
        return;
      }
      const found = cats.find((c) => c.name === cat);
      (found?.subcategories || []).forEach((s) => {
        const opt = document.createElement("option");
        opt.value = s.name;
        opt.textContent = s.name;
        subSel.appendChild(opt);
      });
      subSel.disabled = false;
      btn.disabled = !subSel.value;
    });

    subSel.addEventListener("change", () => {
      btn.disabled = !(catSel.value && subSel.value);
    });

    const doSearch = async (page = 1) => {
      const category = catSel.value;
      const sub = subSel.value;
      if (!category || !sub) return;
      const url = new URL("/api/search/problems/", window.location.origin);
      url.searchParams.set("category", category);
      url.searchParams.set("sub", sub);
      url.searchParams.set("page", String(page));
      url.searchParams.set("page_size", "10");
      const resp = await fetch(url.toString());
      if (!resp.ok) throw new Error("Search failed");
      const json = await resp.json();
      this._faultSearch = {
        category,
        sub,
        page: json.page || 1,
        pages: json.num_pages || 1,
        count: json.count || 0,
        results: json.results || [],
      };
      this.renderFaultResults();
    };

    btn.addEventListener("click", async () => {
      try {
        await doSearch(1);
      } catch (e) {
        console.error(e);
      }
    });

    const prevBtn = document.getElementById("fault-prev");
    const nextBtn = document.getElementById("fault-next");
    prevBtn?.addEventListener("click", async () => {
      const cur = this._faultSearch?.page || 1;
      if (cur > 1) {
        try {
          await doSearch(cur - 1);
        } catch (e) {
          console.error(e);
        }
      }
    });
    nextBtn?.addEventListener("click", async () => {
      const cur = this._faultSearch?.page || 1;
      const max = this._faultSearch?.pages || 1;
      if (cur < max) {
        try {
          await doSearch(cur + 1);
        } catch (e) {
          console.error(e);
        }
      }
    });
  } catch (err) {
    console.warn("Problem search init failed:", err);
  }
};

TreeApp.prototype.renderFaultResults = function () {
  const box = document.getElementById("fault-results");
  const pager = document.getElementById("fault-pagination");
  const pageEl = document.getElementById("fault-page");
  const pagesEl = document.getElementById("fault-pages");
  const countEl = document.getElementById("fault-count");
  if (!box || !pager) return;
  const state = this._faultSearch || {
    results: [],
    page: 1,
    pages: 1,
    count: 0,
  };
  box.style.display = "block";
  pager.style.display = "flex";
  pageEl.textContent = String(state.page || 1);
  pagesEl.textContent = String(state.pages || 1);
  countEl.textContent = String(state.count || 0);

  if (!state.results || state.results.length === 0) {
    box.innerHTML = '<div class="text-muted">No matches found.</div>';
    return;
  }

  const mkItem = (r) => {
    const div = document.createElement("div");
    div.className = "p-2 border rounded mb-2 bg-white";
    const safeId = (r.node_id || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    const safeEx = (r.note_excerpt || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    div.innerHTML = `
      <div class="d-flex justify-content-between align-items-start">
        <div>
          <div class="fw-semibold">${safeId}</div>
          <div class="text-muted small" style="max-height:48px; overflow:hidden">${safeEx}</div>
        </div>
        <div class="ms-2 d-flex flex-column gap-1">
          <button class="btn btn-sm btn-outline-primary" data-action="focus">Focus</button>
          <button class="btn btn-sm btn-outline-secondary" data-action="note">Note</button>
        </div>
      </div>`;

    const focusBtn = div.querySelector('[data-action="focus"]');
    focusBtn.addEventListener("click", () => {
      this.focusNodeById(r.node_id);
    });
    const noteBtn = div.querySelector('[data-action="note"]');
    noteBtn.addEventListener("click", () => {
      const safePath = (r.node_id || "")
        .split("/")
        .map(encodeURIComponent)
        .join("/");
      const url = `/api/notes/${safePath}/`;
      if (typeof window.openNoteEditorModal === "function") {
        window.openNoteEditorModal(url, { id: r.node_id });
      } else {
        window.open(url, "_blank");
      }
    });
    return div;
  };

  box.innerHTML = "";
  state.results.forEach((r) => box.appendChild(mkItem(r)));
};

TreeApp.prototype.focusNodeById = function (nodeId) {
  if (!this.data || !nodeId) return;
  const path = findPathToNode(this.data, nodeId);
  if (!path || path.length === 0) {
    // Try to progressively slugify segments if raw id not found
    // but keep it simple: just warn and return
    console.warn("Node not found:", nodeId);
    return;
  }
  // Expand along the path
  path.forEach((n) => {
    if (n && n.id) this.expandedSet.add(n.id);
  });
  this.spreadNodeId = nodeId;
  this.render();
  this.computeLayout();
  setTimeout(() => this.focusOnSpreadNode(), 150);
};
