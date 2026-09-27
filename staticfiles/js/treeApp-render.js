// treeApp-render.js
// Rendering methods for TreeApp
TreeApp.prototype.renderTreeNodes = function () {
  const visibleNodes = this.getVisibleNodes(this.treeLayout);
  const container = this.treeContainerEl;

  if (!container) return;

  // Set rendering flag to prevent mutation observer from triggering
  this.isRendering = true;

  // Clear existing nodes
  container.innerHTML = "";

  // Check if we're in table mode
  if (this.layoutMode === "table") {
    // Render table view
    this.renderTableView(container, visibleNodes);

    // Reset rendering flag after a short delay
    setTimeout(() => {
      this.isRendering = false;
    }, 100);
    return;
  }

  // Get rendered size for non-table modes
  const renderedSize = this.getRenderedSize();

  // Set container size for tree view
  container.style.width = renderedSize.width + "px";
  container.style.height = renderedSize.height + "px";
  container.style.position = "relative";

  // Render each node in tree view
  for (const node of visibleNodes) {
    const nodeEl = this.createNodeElement(node);
    container.appendChild(nodeEl);
  }

  // Reset rendering flag after a short delay
  setTimeout(() => {
    this.isRendering = false;
  }, 100);
};

TreeApp.prototype.createNodeElement = function (node) {
  const div = document.createElement("div");

  const depth = node.depth || 0;
  const parentActive = node.parentActive || false;
  const isSpecialNode = depth >= 8 || parentActive;

  let nodeWidth = isSpecialNode ? "auto" : 200;
  let nodeHeight = isSpecialNode ? "auto" : 160;

  if (node.type === "sensor") {
    nodeWidth = 200 * 3;
    nodeHeight = 160 * (1 / 3);
  }

  const isSpread = this.spreadNodeId === node.id;
  const isExpanded = this.expandedSet.has(node.id);
  const isActive = this.activeExpandedNode === node.id;
  const isDataMissing = node.name === "Data Missing";

  div.className = `tree-node ${isActive ? "selected" : ""} ${
    isSpecialNode ? "ninth-level" : ""
  } ${isDataMissing ? "data-missing" : ""}`;

  div.setAttribute("data-node-id", node.id);
  div.setAttribute("data-parent-active", parentActive.toString());
  div.setAttribute("data-depth", depth);
  div.setAttribute("data-is-special", isSpecialNode.toString());

  // Position node for horizontal mode (default tree view)
  div.style.left = node.x + "px";
  div.style.top = node.y + "px";

  if (typeof nodeWidth === "number") {
    div.style.width = nodeWidth + "px";
  } else {
    div.style.minWidth = "200px";
  }

  if (typeof nodeHeight === "number") {
    div.style.height = nodeHeight + "px";
    div.style.minHeight = nodeHeight + "px";
  } else {
    div.style.minHeight = "160px";
  }

  // Node content (without icon)
  div.innerHTML = `
    <div class="node-content">
      <div class="node-header">
        <div class="node-text-content">
          <div class="node-title">${this.escapeHtml(node.name)}</div>
          <div class="node-meta">
            ${node.type}${node.value ? ` · ${node.value}` : ""}
          </div>
        </div>
      </div>
      <div class="node-description">${this.escapeHtml(
        node.description || ""
      )}</div>
      
      <div class="spread-button" data-action="spread" title="${
        isSpread ? "Unspread (restore view)" : "Spread (focus here)"
      }">
        <img src="/static/images/${
          isSpread ? "restoreIcon" : "collapseIcon"
        }.png" 
             alt="${isSpread ? "Unspread" : "Spread"}" 
             style="width: 16px; height: 16px;">
      </div>
      
      ${
        node.children && Object.keys(node.children).length > 0
          ? `
        <div class="expand-button ${isExpanded ? "expanded" : ""}" 
             data-action="expand" 
             title="${isExpanded ? "Collapse" : "Expand"}">
          <i class="fas ${isExpanded ? "fa-minus" : "fa-plus"}"></i>
        </div>
      `
          : ""
      }

      <div class="note-button btn btn-sm btn-outline-secondary" 
           data-action="note" 
           title="Open note editor in a new tab"
           style="position: absolute; right: 8px; bottom: 8px;">
        <img src="/static/images/${
          node.note && node.note.trim() ? "ReadAddNotes" : "AddNotes"
        }.png" 
             alt="${
               node.note && node.note.trim() ? "Read/Edit Notes" : "Add Notes"
             }" 
             style="width: 16px; height: 16px;">
      </div>
    </div>
  `;

  // Event listeners
  const spreadBtn = div.querySelector('[data-action="spread"]');
  if (spreadBtn) {
    spreadBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.onSpreadToggle(node);
    });
  }

  const expandBtn = div.querySelector('[data-action="expand"]');
  if (expandBtn) {
    expandBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.onExpandToggle(node);
    });
  }

  const noteBtn = div.querySelector('[data-action="note"]');
  if (noteBtn) {
    noteBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      // Preserve slashes but encode each segment safely
      const safePath = (node.id || "")
        .split("/")
        .map(encodeURIComponent)
        .join("/");
      const url = `/api/notes/${safePath}/`;
      if (typeof window.openNoteEditorModal === "function") {
        window.openNoteEditorModal(url, node);
      } else {
        // Fallback to opening in a new tab if modal helper isn't present
        window.open(url, "_blank");
      }
    });
  }

  return div;
};

// Removed getNodeIconClass() and getNodeIcon() completely

TreeApp.prototype.computePaths = function () {
  if (!this.containerEl || !this.svgEl || !this.treeContainerEl) return;
  if (!this.data || Object.keys(this.data).length === 0) return;

  // Skip path computation in table mode
  if (this.layoutMode === "table") {
    this.svgEl.innerHTML = "";
    this.svgEl.setAttribute("width", 0);
    this.svgEl.setAttribute("height", 0);
    return;
  }

  const renderedSize = this.getRenderedSize();

  this.treeContainerEl.style.width = renderedSize.width + "px";
  this.treeContainerEl.style.height = renderedSize.height + "px";

  const containerRect = this.containerEl.getBoundingClientRect();

  const rects = {};
  this.containerEl.querySelectorAll("[data-node-id]").forEach((el) => {
    const id = el.dataset.nodeId;
    const depth = parseInt(el.dataset.depth) || 0;
    const parentActive = el.dataset.parentActive === "true";

    const elRect = el.getBoundingClientRect();
    const x = elRect.left - containerRect.left + this.containerEl.scrollLeft;
    const y = elRect.top - containerRect.top + this.containerEl.scrollTop;

    const actualWidth = elRect.width;
    const actualHeight = elRect.height;

    rects[id] = {
      left: x,
      top: y,
      right: x + actualWidth,
      bottom: y + actualHeight,
      width: actualWidth,
      height: actualHeight,
      depth: depth,
      parentActive: parentActive,
    };
  });

  const contentWidth = this.treeContainerEl.offsetWidth;
  const contentHeight = this.treeContainerEl.offsetHeight;
  this.svgEl.setAttribute("width", contentWidth);
  this.svgEl.setAttribute("height", contentHeight);
  this.svgEl.setAttribute("viewBox", `0 0 ${contentWidth} ${contentHeight}`);
  this.svgEl.style.width = contentWidth + "px";
  this.svgEl.style.height = contentHeight + "px";

  const newPaths = [];
  const rootsToWalk = this.spreadNodeId
    ? { [this.spreadNodeId]: findNodeById(this.data, this.spreadNodeId) }
    : this.data;

  if (!rootsToWalk || Object.keys(rootsToWalk).length === 0) return;

  const walk = (node) => {
    if (!node) return;
    if (node.children) {
      for (const child of Object.values(node.children)) {
        const parentVisible = !!rects[node.id];
        const childVisible = !!rects[child.id];
        const parentExpanded = this.expandedSet.has(node.id);
        if (parentVisible && childVisible && parentExpanded) {
          const p1 = rects[node.id];
          const p2 = rects[child.id];

          const x1 = p1.right;
          const y1 = p1.top + p1.height / 2;
          const x2 = p2.left;
          const y2 = p2.top + p2.height / 2;

          const isSpecialConnector =
            p2.depth >= 8 ||
            node.id === this.activeExpandedNode ||
            (this.specialParents && this.specialParents.has(node.id)) ||
            p2.parentActive === true;

          newPaths.push({
            x1,
            y1,
            x2,
            y2,
            depth: p2.depth,
            special: isSpecialConnector,
          });
        }
        walk(child);
      }
    }
  };

  for (const r of Object.values(rootsToWalk)) walk(r);

  // Render paths
  this.svgEl.innerHTML = "";
  for (const p of newPaths) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    const depth = p.depth || 0;
    const isSpecial = !!p.special || depth >= 8;
    const curveFactor = isSpecial ? 0.15 : 0.25;

    const dx = Math.max(40, Math.abs(p.x2 - p.x1) * curveFactor);
    const c1x = p.x1 + dx;
    const c2x = p.x2 - dx;
    const d = `M ${p.x1} ${p.y1} C ${c1x} ${p.y1} ${c2x} ${p.y2} ${p.x2} ${p.y2}`;

    path.setAttribute("d", d);
    path.setAttribute(
      "class",
      `connector-path ${
        isSpecial ? "ninth-level-connector special-connector" : ""
      }`
    );

    this.svgEl.appendChild(path);
  }

  this.paths = newPaths;
};
