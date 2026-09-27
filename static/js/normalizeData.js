// normalizeData.js
// Robust normalizer for backend JSON -> UI tree mapping

const POSITIONS_FOR_SLASH = [4, 7, 10, 13, 16, 19, 22, 25];
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

/**
 * Split a path by '/' while treating content within brackets/parentheses as a single node.
 * Example: "A/B/(C/D)/E" -> ["A", "B", "(C/D)", "E"]
 * Supports: (), [], {}
 */
function splitPathPreservingBrackets(pathString) {
  if (!pathString || typeof pathString !== "string") return [];

  const parts = [];
  let current = "";
  let bracketDepth = 0;
  const bracketPairs = { "(": ")", "[": "]", "{": "}" };
  const openBrackets = Object.keys(bracketPairs);
  const closeBrackets = Object.values(bracketPairs);
  const bracketStack = [];

  for (let i = 0; i < pathString.length; i++) {
    const char = pathString[i];

    if (openBrackets.includes(char)) {
      bracketStack.push(bracketPairs[char]);
      bracketDepth++;
      current += char;
    } else if (closeBrackets.includes(char)) {
      current += char;
      if (
        bracketStack.length > 0 &&
        char === bracketStack[bracketStack.length - 1]
      ) {
        bracketStack.pop();
        bracketDepth--;
      }
    } else if (char === "/" && bracketDepth === 0) {
      if (current) {
        parts.push(current);
        current = "";
      }
    } else {
      current += char;
    }
  }

  if (current) {
    parts.push(current);
  }

  return parts;
}

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
    const normalizedPath = String(rawPath).replace(/\\/g, "/");
    const parts = splitPathPreservingBrackets(normalizedPath)
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
        if (!nodes[parentId]) {
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
  const map = JSON.parse(JSON.stringify(rawMap || {}));
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

  if (typeof map === "object") {
    for (const [k, v] of Object.entries(map)) {
      const nodeId = v && v.id ? v.id : k || slugify(String(v));
      const base = ensureNode(nodeId, v || {});
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
      if (!base.parentId) resultRoots[base.id] = base;
    }

    for (const id of Object.keys(created)) {
      const node = created[id];
      if (node.parentId) {
        if (!created[node.parentId]) {
          ensureNode(node.parentId, {
            name: node.parentId.split("/").pop(),
            parentId: null,
          });
        }
        created[node.parentId].children[node.id] = node;
        if (!created[node.parentId].parentId)
          resultRoots[created[node.parentId].id] = created[node.parentId];
      }
    }

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

  if (
    Array.isArray(raw) &&
    raw.length > 0 &&
    raw.every((r) => r && r.id && r.name && r.type && r.children)
  ) {
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

  if (typeof raw === "object" && !Array.isArray(raw)) {
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
    if (raw.id && raw.name) {
      const copy = JSON.parse(JSON.stringify(raw));
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

  if (Array.isArray(raw)) {
    if (raw.every((r) => typeof r === "string" && r.includes("/"))) {
      return buildFromPaths(raw);
    }

    if (raw.every((r) => typeof r === "string")) {
      const looksLikeCompactTag = raw.every(
        (r) => typeof r === "string" && !r.includes("/") && r.length >= 20
      );
      if (looksLikeCompactTag) {
        const paths = raw.map((s) => insertSlashesForIotTag(s));
        return buildFromPaths(paths);
      }
      const paths = raw.map((s) =>
        s.includes("/") ? s : insertSlashesForIotTag(s)
      );
      return buildFromPaths(paths);
    }

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
          return normalizeNodeMap(
            raw.reduce((acc, cur, i) => {
              const id = cur.id || `n${i}`;
              acc[id] = cur;
              return acc;
            }, {})
          );
        } else {
          const s = Object.values(item).find(
            (v) => typeof v === "string" && v.includes("/")
          );
          if (s) paths.push(s);
        }
      }
      if (paths.length) return buildFromPaths(paths);
      return normalizeNodeMap(
        raw.reduce((acc, cur, i) => {
          const id = cur.id || `node_${i}`;
          acc[id] = cur;
          return acc;
        }, {})
      );
    }
  }

  if (typeof raw === "string") {
    if (raw.includes("/")) {
      return buildFromPaths([raw]);
    }
    if (raw.length >= 20) {
      return buildFromPaths([insertSlashesForIotTag(raw)]);
    }
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

  return {};
}
