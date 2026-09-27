// treeApp-vertical.js
// Table layout computation for TreeApp (replaces vertical layout)

// Compute table data from visible nodes
TreeApp.prototype.computeTableData = function (visibleNodes) {
  if (!visibleNodes || this.layoutMode !== "table") return null;

  const tableRows = [];

  for (const node of visibleNodes) {
    const childrenCount = node.children ? Object.keys(node.children).length : 0;

    tableRows.push({
      id: node.id || "",
      name: node.name || "",
      type: node.type || "",
      depth: node.depth || 0,
      parentId: node.parentId || "",
      childrenCount: childrenCount,
      note: node.note || "",
    });
  }

  return tableRows;
};

// Render table view in container
TreeApp.prototype.renderTableView = function (container, visibleNodes) {
  if (!container) return;

  container.innerHTML = "";
  container.style.width = "100%";
  container.style.height = "auto";
  container.style.position = "relative";

  const tableData = this.computeTableData(visibleNodes);

  if (!tableData || tableData.length === 0) {
    container.innerHTML =
      '<div class="table-empty-state">No data to display</div>';
    return;
  }

  const tableWrapper = document.createElement("div");
  tableWrapper.className = "table-wrapper";

  const table = document.createElement("table");
  table.className = "tree-table";

  const thead = document.createElement("thead");
  thead.innerHTML = `
    <tr>
      <th>ID</th>
      <th>Name</th>
      <th>Type</th>
      <th>Depth</th>
      <th>Parent ID</th>
      <th>Children</th>
      <th>Actions</th>
    </tr>
  `;
  table.appendChild(thead);

  const tbody = document.createElement("tbody");

  for (const row of tableData) {
    const tr = document.createElement("tr");
    tr.setAttribute("data-node-id", row.id);
    tr.setAttribute("data-depth", row.depth);

    const depthClass = row.depth >= 8 ? "depth-special" : "";
    if (depthClass) tr.classList.add(depthClass);

    if (row.name === "Data Missing") {
      tr.classList.add("data-missing");
    }

    const tdId = document.createElement("td");
    tdId.className = "cell-id";
    tdId.textContent = row.id;
    tdId.title = row.id;
    tr.appendChild(tdId);

    const tdName = document.createElement("td");
    tdName.className = "cell-name";
    const indent = "  ".repeat(row.depth);
    tdName.textContent = indent + row.name;
    tdName.title = row.name;
    tdName.style.paddingLeft = 10 + row.depth * 20 + "px";
    tr.appendChild(tdName);

    const tdType = document.createElement("td");
    tdType.className = "cell-type";
    tdType.textContent = row.type;
    tr.appendChild(tdType);

    const tdDepth = document.createElement("td");
    tdDepth.className = "cell-depth";
    tdDepth.textContent = row.depth;
    tr.appendChild(tdDepth);

    const tdParentId = document.createElement("td");
    tdParentId.className = "cell-parent-id";
    tdParentId.textContent = row.parentId;
    tdParentId.title = row.parentId;
    tr.appendChild(tdParentId);

    const tdChildren = document.createElement("td");
    tdChildren.className = "cell-children";
    tdChildren.textContent = row.childrenCount;
    tr.appendChild(tdChildren);

    const tdActions = document.createElement("td");
    tdActions.className = "cell-actions";

    const actionsDiv = document.createElement("div");
    actionsDiv.className = "table-actions";

    const noteBtn = document.createElement("button");
    noteBtn.className = "table-action-btn";
    noteBtn.title =
      row.note && row.note.trim() ? "Read/Edit Notes" : "Add Notes";
    noteBtn.innerHTML = `<img src="/static/images/${
      row.note && row.note.trim() ? "ReadAddNotes" : "AddNotes"
    }.png" alt="Notes" style="width: 16px; height: 16px;">`;
    noteBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const safePath = (row.id || "")
        .split("/")
        .map(encodeURIComponent)
        .join("/");
      const url = `/api/notes/${safePath}/`;
      if (typeof window.openNoteEditorModal === "function") {
        window.openNoteEditorModal(url, { id: row.id, name: row.name });
      } else {
        window.open(url, "_blank");
      }
    });

    actionsDiv.appendChild(noteBtn);
    tdActions.appendChild(actionsDiv);
    tr.appendChild(tdActions);

    tbody.appendChild(tr);
  }

  table.appendChild(tbody);
  tableWrapper.appendChild(table);
  container.appendChild(tableWrapper);
};

// Keep getRenderedSize for backward compatibility but simplified
TreeApp.prototype.getRenderedSize = function () {
  return this.contentSize;
};
