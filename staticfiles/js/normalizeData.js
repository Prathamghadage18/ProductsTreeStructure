// normalizeData.js
// Robust normalizer for backend JSON -> UI tree mapping

const POSITIONS_FOR_SLASH = [4, 7, 10, 13, 16, 19, 22, 25];
// level types (9 levels)
const LEVEL_TYPES = [
  "manufacturer",
  "segment",
  "site",
  "plant",
  "function",
  "system",
  "machine",
  "stage",
  "sensor",
];

function slugify(s) {
  return (
    String(s || "")
      .trim()
      .replace(/\s+/g, "_")
      .replace(/[^a-zA-Z0-9_\-]/g, "")
      .slice(0, 80) || "node"
  );
}

/**
 * Insert '/' into a compact IOTTAG string at fixed positions
 * Example: GRFLHITWAL... -> GRFL/HIT/WAL/...
 */
function insertSlashesForIotTag(tag) {
  if (!tag || typeof tag !== "string") return String(tag || "");
  const chars = [];
  const positions = new Set(POSITIONS_FOR_SLASH);
  for (let i = 0; i < tag.length; i++) {
    if (positions.has(i)) chars.push("/");
    chars.push(tag[i]);
  }
  return chars.join("");
}

/**
 * Build tree from array of path strings (each path like "A/B/C")
 * Returns mapping rootId -> nodeObject
 */
function buildFromPaths(paths) {
  const roots = {};
  const nodes = {}; // id -> node

  for (const rawPath of paths) {
    if (!rawPath) continue;
    // normalize separators, trim and split
    const parts = String(rawPath)
      .replace(/\\/g, "/")
      .split("/")
      .map((p) => (p === "" ? "###" : p.trim()))
      .filter(Boolean);
    let parentId = null;
    for (let idx = 0; idx < parts.length; idx++) {
      const name = parts[idx] || "###";
      const idPart = slugify(name);
      const id = parentId ? `${parentId}/${idPart}` : idPart;
      if (!nodes[id]) {
        nodes[id] = {
          id,
          name,
          type: LEVEL_TYPES[idx] || `level${idx}`,
          description: "",
          parentId: parentId,
          children: {},
        };
      }
      if (!parentId) {
        roots[nodes[id].id] = nodes[id];
      } else {
        // attach as child of parent
        if (!nodes[parentId]) {
          // defensive: ensure parent exists
          nodes[parentId] = {
            id: parentId,
            name: parentId.split("/").pop(),
            type: LEVEL_TYPES[Math.max(0, idx - 1)] || "level",
            description: "",
            parentId: parentId.includes("/")
              ? parentId.split("/").slice(0, -1).join("/")
              : null,
            children: {},
          };
          // ensure root mapping if parent has no parent
          if (!nodes[parentId].parentId)
            roots[nodes[parentId].id] = nodes[parentId];
        }
        nodes[parentId].children[nodes[id].id] = nodes[id];
      }
      parentId = id;
    }
  }

  return roots;
}

/**
 * Normalize node map (e.g. backend sends a mapping or single node objects)
 * Ensure children are object mapping and node shape is correct.
 */
function normalizeNodeMap(rawMap) {
  const map = JSON.parse(JSON.stringify(rawMap || {})); // clone
  const resultRoots = {};
  const created = {};

  function ensureNode(id, partial = {}) {
    if (created[id]) return created[id];
    const node = {
      id,
      name: partial.name || partial.id || id.split("/").pop() || id,
      type: partial.type || "level",
      description: partial.description || "",
      parentId:
        partial.parentId !== undefined
          ? partial.parentId
          : partial.parent || null,
      children: {},
      // copy over any other primitive safe fields (status/value/note), but avoid NaN
      ...(partial.status ? { status: partial.status } : {}),
      ...(partial.value !== undefined
        ? { value: partial.value === "NaN" ? null : partial.value }
        : {}),
      ...(partial.lastUpdate ? { lastUpdate: partial.lastUpdate } : {}),
      ...(partial.note !== undefined ? { note: partial.note } : {}),
    };
    created[id] = node;
    return node;
  }

  // If top-level appears to be mapping of nodes (id -> node)
  if (typeof map === "object") {
    for (const [k, v] of Object.entries(map)) {
      // If v is string, treat as name
      const nodeId = v && v.id ? v.id : k || slugify(String(v));
      const base = ensureNode(nodeId, v || {});
      // attach children if present
      if (v && v.children) {
        if (Array.isArray(v.children)) {
          v.children.forEach((child, i) => {
            if (typeof child === "string") {
              const cid = `${nodeId}/${slugify(child)}`;
              const childNode = ensureNode(cid, {
                name: child,
                parentId: nodeId,
              });
              base.children[childNode.id] = childNode;
            } else if (child && child.id) {
              const childNode = ensureNode(child.id, {
                ...child,
                parentId: nodeId,
              });
              base.children[childNode.id] = childNode;
            } else {
              // object without id
              const cid = `${nodeId}/c${i}`;
              const childNode = ensureNode(cid, { ...child, parentId: nodeId });
              base.children[childNode.id] = childNode;
            }
          });
        } else if (typeof v.children === "object") {
          for (const [ck, cv] of Object.entries(v.children)) {
            const childNode = ensureNode(cv.id || ck, {
              ...(cv || {}),
              parentId: nodeId,
            });
            base.children[childNode.id] = childNode;
          }
        }
      }
      // mark root if no parent
      if (!base.parentId) resultRoots[base.id] = base;
    }

    // post-process: ensure parent->child links for items that specify parentId without parent node
    for (const id of Object.keys(created)) {
      const node = created[id];
      if (node.parentId) {
        if (!created[node.parentId]) {
          // create parent placeholder
          ensureNode(node.parentId, {
            name: node.parentId.split("/").pop(),
            parentId: null,
          });
        }
        created[node.parentId].children[node.id] = node;
        // ensure root presence
        if (!created[node.parentId].parentId)
          resultRoots[created[node.parentId].id] = created[node.parentId];
      }
    }

    // If still no roots (rare), pick top-level nodes with no parents
    if (Object.keys(resultRoots).length === 0) {
      for (const id of Object.keys(created)) {
        if (!created[id].parentId) resultRoots[id] = created[id];
      }
    }

    return resultRoots;
  }

  return {};
}

/**
 * Helper: Recursively convert children arrays to objects
 */
function convertChildrenToObject(node) {
  if (!node) return node;

  const result = JSON.parse(JSON.stringify(node)); // Deep clone

  if (Array.isArray(result.children)) {
    const childrenObj = {};
    result.children.forEach((child) => {
      if (child && child.id) {
        childrenObj[child.id] = convertChildrenToObject(child);
      }
    });
    result.children = childrenObj;
  } else if (result.children && typeof result.children === "object") {
    // Already an object, but recursively process each child
    const childrenObj = {};
    Object.entries(result.children).forEach(([k, child]) => {
      childrenObj[k] = convertChildrenToObject(child);
    });
    result.children = childrenObj;
  }
  return result;
}

/**
 * The exported normalizeData function.
 * Accepts many backend shapes and outputs root mapping.
 */
function normalizeData(raw) {
  if (raw == null) return {};

  // Handle array of manufacturer nodes (direct roots, no wrapper)
  // Backend now returns: [{id: "Sisai", name: "Sisai", type: "manufacturer", children: [...]}, ...]
  if (
    Array.isArray(raw) &&
    raw.length > 0 &&
    raw.every((r) => r && r.id && r.name && r.type && r.children)
  ) {
    // Convert array to map and process
    const manufacturerMap = {};
    raw.forEach((mfr) => {
      if (mfr.id) {
        // Convert children arrays to objects recursively
        const processedMfr = convertChildrenToObject(mfr);
        processedMfr.parentId = null; // Manufacturers are root nodes
        manufacturerMap[processedMfr.id] = processedMfr;
      }
    });
    return manufacturerMap;
  }

  // If already a mapping with node-like objects keyed by id
  if (typeof raw === "object" && !Array.isArray(raw)) {
    // If it looks like a node (has id & name)
    const values = Object.values(raw);
    if (
      values.length &&
      values.every((v) => v && (v.id || v.name || v.children))
    ) {
      try {
        return normalizeNodeMap(raw);
      } catch (e) {
        // fallback to single root wrapper
      }
    }
    // If raw is a single node object (not keyed)
    if (raw.id && raw.name) {
      const copy = JSON.parse(JSON.stringify(raw));
      // ensure children mapping
      if (Array.isArray(copy.children)) {
        const childrenMap = {};
        copy.children.forEach((c) => {
          if (c && c.id) childrenMap[c.id] = c;
        });
        copy.children = childrenMap;
      }

      // Special-case: some backends wrap the entire tree under a synthetic root
      // with id/name/type === 'root'. In that case, unwrap and return its
      // children as top-level roots so the UI shows the actual first parents
      // instead of a generic "root" node.
      if (
        String(copy.id).toLowerCase() === "root" ||
        String(copy.name).toLowerCase() === "root" ||
        String(copy.type || "").toLowerCase() === "root"
      ) {
        // Convert children array to object if needed
        let childrenObj = {};
        if (Array.isArray(copy.children)) {
          copy.children.forEach((child) => {
            if (child && child.id) {
              // Recursively convert child's children array to object
              const processedChild = convertChildrenToObject(child);
              processedChild.parentId = null; // Top-level node has no parent
              childrenObj[processedChild.id] = processedChild;
            }
          });
        } else if (copy.children && typeof copy.children === "object") {
          Object.entries(copy.children).forEach(([k, child]) => {
            if (child && (child.id || k)) {
              const processedChild = convertChildrenToObject(child);
              processedChild.parentId = null;
              childrenObj[child.id || k] = processedChild;
            }
          });
        }
        return childrenObj;
      }

      return { [copy.id]: copy };
    }
  }

  // If raw is an array
  if (Array.isArray(raw)) {
    // array of simple path strings: ["A/B/C", ...]
    if (raw.every((r) => typeof r === "string" && r.includes("/"))) {
      return buildFromPaths(raw);
    }

    // array of IOTTAG compact strings (no slashes, fixed length) OR mix of both
    if (raw.every((r) => typeof r === "string")) {
      // Detect if strings look like compact tags (length >= 20 and no '/')
      const looksLikeCompactTag = raw.every(
        (r) => typeof r === "string" && !r.includes("/") && r.length >= 20
      );
      if (looksLikeCompactTag) {
        const paths = raw.map((s) => insertSlashesForIotTag(s));
        return buildFromPaths(paths);
      }
      // array of path strings (some may be) - normalize: convert any compact tags to paths, keep path-like as-is
      const paths = raw.map((s) =>
        s.includes("/") ? s : insertSlashesForIotTag(s)
      );
      return buildFromPaths(paths);
    }

    // array of objects: possibly [{ IOTPATH: "A/B/C" }, { IOTTAG: "GRFL...." }, ...]
    if (raw.every((r) => typeof r === "object" && r !== null)) {
      const paths = [];
      for (const item of raw) {
        if (item.IOTPATH) paths.push(item.IOTPATH);
        else if (item.path) paths.push(item.path);
        else if (item.pathString) paths.push(item.pathString);
        else if (item.IOTTAG) {
          const t = String(item.IOTTAG);
          paths.push(t.includes("/") ? t : insertSlashesForIotTag(t));
        } else if (typeof item === "object" && item.name && item.children) {
          // fallback to node map normalization
          return normalizeNodeMap(
            raw.reduce((acc, cur, i) => {
              const id = cur.id || `n${i}`;
              acc[id] = cur;
              return acc;
            }, {})
          );
        } else {
          // try to stringify something reasonable
          const s = Object.values(item).find(
            (v) => typeof v === "string" && v.includes("/")
          );
          if (s) paths.push(s);
        }
      }
      if (paths.length) return buildFromPaths(paths);
      // fallback: normalize array of objects as node map
      return normalizeNodeMap(
        raw.reduce((acc, cur, i) => {
          const id = cur.id || `node_${i}`;
          acc[id] = cur;
          return acc;
        }, {})
      );
    }
  }

  // If raw is a string
  if (typeof raw === "string") {
    // if it contains '/', treat as path
    if (raw.includes("/")) {
      return buildFromPaths([raw]);
    }
    // if long compact tag
    if (raw.length >= 20) {
      return buildFromPaths([insertSlashesForIotTag(raw)]);
    }
    // fallback single root
    const id = slugify(raw);
    return {
      [id]: {
        id,
        name: raw,
        type: "root",
        description: "",
        parentId: null,
        children: {},
      },
    };
  }

  // default fallback empty
  return {};
}
