// layout.js
// Reusable layout helpers

/* -------------------------
   Basic subtree size computation (generic)
   ------------------------- */
function computeSubtreeSizes(roots, expandedSet) {
  const sizes = {};
  const dfs = (node) => {
    if (!node) return 1;
    const hasChildren = node.children && Object.keys(node.children).length > 0;
    if (!hasChildren || !expandedSet.has(node.id)) {
      sizes[node.id] = 1;
      return 1;
    }
    let sum = 0;
    for (const child of Object.values(node.children)) {
      sum += dfs(child);
    }
    sizes[node.id] = Math.max(1, sum);
    return sizes[node.id];
  };

  for (const r of Object.values(roots || {})) dfs(r);
  return sizes;
}

/* -------------------------
   Find path to a node (array of nodes from root..target)
   ------------------------- */
function findPathToNode(roots, targetId) {
  for (const root of Object.values(roots || {})) {
    const r = dfs(root, targetId);
    if (r) return r;
  }
  return [];
}

function dfs(node, target) {
  if (!node) return null;
  if (node.id === target) return [node];
  if (!node.children) return null;
  for (const child of Object.values(node.children)) {
    const res = dfs(child, target);
    if (res) return [node, ...res];
  }
  return null;
}

/* -------------------------
   Count sensors (robust to various keys)
   ------------------------- */
function countSensors(roots) {
  let total = 0,
    dataMissing = 0,
    warning = 0,
    offline = 0;

  const recurse = (n) => {
    if (!n) return;
    // Check if node name is exactly "Data missing"
    if (n.name === "Data Missing") {
      dataMissing++;
    }
    // determine "is sensor" by type string (case-insensitive)
    const t = (n.type || "").toString().toLowerCase();
    const isSensor = t === "sensor" || t.endsWith("sensor");
    // Some backends might mark sensors with itemType etc. fallback: check presence of `status` or `value` with no children
    const maybeSensor = !n.children && (n.status || n.value);
    if (isSensor || maybeSensor) {
      total++;
      const status = (n.status || n.status_code || "").toString().toLowerCase();
      if (status === "warning" || status === "warn") warning++;
      else offline++;
    }
    if (n.children) for (const c of Object.values(n.children)) recurse(c);
  };

  for (const r of Object.values(roots || {})) recurse(r);
  return { total, dataMissing, warning, offline };
}

/* -------------------------
   Build visible levels (used by Sidebar)
   ------------------------- */
function buildVisibleLevels(roots, expandedSet, search = "") {
  const levels = [];

  const shouldShow = (node) => {
    if (!search) return true;
    const sq = String(search).toLowerCase();
    if (
      (node.name && node.name.toLowerCase().includes(sq)) ||
      (node.description && node.description.toLowerCase().includes(sq)) ||
      (node.value && node.value.toString().toLowerCase().includes(sq))
    )
      return true;
    if (node.children) {
      return Object.values(node.children).some((child) => shouldShow(child));
    }
    return false;
  };

  const recurse = (node, level = 0, parentExpanded = true) => {
    if (!shouldShow(node)) return;
    levels[level] = levels[level] || [];
    if (level === 0 || parentExpanded) levels[level].push(node);

    if (node.children && expandedSet.has(node.id)) {
      for (const child of Object.values(node.children)) {
        recurse(child, level + 1, expandedSet.has(node.id));
      }
    } else {
      if (node.children) {
        for (const child of Object.values(node.children)) {
          recurse(child, level + 1, false);
        }
      }
    }
  };

  for (const r of Object.values(roots || {})) recurse(r, 0, true);

  return levels.filter((l) => l && l.length > 0);
}

/* -------------------------
   Find node by id (reference, not deep copy)
   ------------------------- */
function findNodeById(roots, targetId) {
  const dfsFind = (node) => {
    if (!node) return null;
    if (node.id === targetId) return node;
    if (!node.children) return null;
    for (const child of Object.values(node.children)) {
      const r = dfsFind(child);
      if (r) return r;
    }
    return null;
  };

  for (const root of Object.values(roots || {})) {
    const r = dfsFind(root);
    if (r) return r;
  }
  return null;
}

/* -------------------------
   Collapse children recursively (mutates Set in place)
   ------------------------- */
function collapseChildrenRecursivelyInData(roots, nodeId, expandedSetInPlace) {
  const node = findNodeById(roots, nodeId);
  if (!node || !node.children) return expandedSetInPlace;

  for (const child of Object.values(node.children)) {
    expandedSetInPlace.delete(child.id);
    collapseChildrenRecursivelyInData(roots, child.id, expandedSetInPlace);
  }
  return expandedSetInPlace;
}
