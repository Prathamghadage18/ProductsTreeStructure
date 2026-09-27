// treeApp-layout.js
// Layout computation methods for TreeApp

TreeApp.prototype.computeLayout = function () {
  if (!this.data) return;

  const rootsToLayout = this.spreadNodeId
    ? { [this.spreadNodeId]: findNodeById(this.data, this.spreadNodeId) }
    : this.data;

  const { tree, width, height } = this.computeEnhancedLayout(
    rootsToLayout,
    this.expandedSet,
    this.spreadNodeId
  );

  this.treeLayout = tree;
  this.contentSize = { width, height };

  // Render tree nodes
  this.renderTreeNodes();

  // Compute connector paths after layout is complete
  // Use requestAnimationFrame to ensure browser has painted
  requestAnimationFrame(() => {
    setTimeout(() => this.computePaths(), 100);
  });
};

TreeApp.prototype.computeEnhancedLayout = function (
  roots,
  expandedSet,
  spreadNodeId
) {
  const sizesWithDepth = this.computeSubtreeSizesWithDepth(roots, expandedSet);
  const { tree, width, height } = this.layoutTreeWithDepthAwareSpacing(
    roots,
    sizesWithDepth,
    expandedSet,
    {
      activeExpandedNode: this.activeExpandedNode,
      specialParents: this.specialParents,
    }
  );

  return { tree, width, height };
};

TreeApp.prototype.computeSubtreeSizesWithDepth = function (
  roots,
  expandedSet,
  depth = 0
) {
  const sizes = {};

  const dfs = (node, currentDepth) => {
    if (!node) return 1;

    node.depth = currentDepth;
    const hasChildren = node.children && Object.keys(node.children).length > 0;

    if (!hasChildren || !expandedSet.has(node.id)) {
      sizes[node.id] = { size: 1, depth: currentDepth };
      return 1;
    }

    let sum = 0;
    for (const child of Object.values(node.children)) {
      sum += dfs(child, currentDepth + 1);
    }
    sizes[node.id] = { size: Math.max(1, sum), depth: currentDepth };
    return sizes[node.id].size;
  };

  for (const r of Object.values(roots)) {
    dfs(r, depth);
  }
  return sizes;
};

TreeApp.prototype.layoutTreeWithDepthAwareSpacing = function (
  roots,
  sizesWithDepth,
  expandedSet,
  opts = {}
) {
  const ACTIVE_EXPANDED = opts.activeExpandedNode || null;
  const SPECIAL_PARENTS = opts.specialParents || new Set();

  const copy = JSON.parse(JSON.stringify(roots));
  let maxX = 0;
  let currentY = 0;

  const layoutNode = (
    node,
    depth,
    yStart,
    nodeTotalHeight,
    parentX = LEFT_MARGIN,
    parentIsActive = false
  ) => {
    node.parentActive =
      parentIsActive || (node.parentId && SPECIAL_PARENTS.has(node.parentId));

    const isNinthLevelOrDeeper = depth >= 8 || parentIsActive === true;
    const effectiveXSpacing = isNinthLevelOrDeeper
      ? NINTH_LEVEL_X_SPACING
      : X_SPACING;

    node.x = parentX + (depth > 0 ? effectiveXSpacing : 0);

    const hasChildren = node.children && Object.keys(node.children).length > 0;
    const isExpanded = expandedSet.has(node.id);

    if (!hasChildren || !isExpanded || nodeTotalHeight <= 0) {
      node.y = yStart + nodeTotalHeight / 2;
      maxX = Math.max(maxX, node.x);
      return [node.y];
    }

    const children = Object.values(node.children);
    const totalChildSize = children.reduce(
      (s, c) => s + (sizesWithDepth[c.id] || { size: 1 }).size,
      0
    );

    let childYs = [];
    let cursor = yStart;

    for (const child of children) {
      child.parentId = node.id;
      const childSize = (sizesWithDepth[child.id] || { size: 1 }).size;
      const childHeight = (nodeTotalHeight * childSize) / totalChildSize;

      const childParentIsActive =
        (ACTIVE_EXPANDED && node.id === ACTIVE_EXPANDED) ||
        SPECIAL_PARENTS.has(node.id);

      const childLayout = layoutNode(
        child,
        depth + 1,
        cursor,
        childHeight,
        node.x,
        childParentIsActive
      );
      childYs = childYs.concat(childLayout);
      cursor += childHeight;
    }

    if (childYs.length > 0) {
      node.y = childYs.reduce((a, b) => a + b, 0) / childYs.length;
    } else {
      node.y = yStart + nodeTotalHeight / 2;
    }

    maxX = Math.max(maxX, node.x);
    return [node.y];
  };

  const baseUnit = NODE_HEIGHT + V_GAP;
  let totalHeight = 0;
  const rootHeights = {};

  for (const r of Object.values(copy)) {
    const sz = (sizesWithDepth[r.id] || { size: 1 }).size;
    const compressionFactor = Math.max(0.3, 1 - (r.depth || 0) * 0.05);
    const h = Math.max(400, sz * baseUnit * compressionFactor);
    rootHeights[r.id] = h;
    totalHeight += h;
  }

  for (const r of Object.values(copy)) {
    const rootHeight = rootHeights[r.id];
    layoutNode(r, 0, currentY, rootHeight, LEFT_MARGIN, false);
    currentY += rootHeight;
  }

  const requiredWidth = maxX + 300 + RIGHT_PADDING;
  const requiredHeight = Math.max(600, currentY + V_GAP);

  return { tree: copy, width: requiredWidth, height: requiredHeight };
};

TreeApp.prototype.getVisibleNodes = function (roots) {
  const visibleNodes = [];
  const shouldShow = (node) => {
    if (!this.search) return true;
    const sq = this.search.toLowerCase();
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

  const recurse = (
    node,
    parentExpanded = true,
    depth = 0,
    parentActive = false
  ) => {
    if (!shouldShow(node)) return;

    node.depth = depth;
    node.parentActive = parentActive;
    if (node.parentId === null || parentExpanded) visibleNodes.push(node);

    if (node.children && this.expandedSet.has(node.id)) {
      for (const child of Object.values(node.children))
        recurse(
          child,
          this.expandedSet.has(node.id),
          depth + 1,
          node.id === this.activeExpandedNode ||
            (this.specialParents && this.specialParents.has(node.id))
        );
    } else {
      if (node.children) {
        for (const child of Object.values(node.children))
          recurse(
            child,
            false,
            depth + 1,
            node.id === this.activeExpandedNode ||
              (this.specialParents && this.specialParents.has(node.id))
          );
      }
    }
  };

  for (const r of Object.values(roots)) recurse(r);
  return visibleNodes;
};
