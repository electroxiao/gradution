function buildAdjacency(nodeIds, edges) {
  const adjacency = new Map(nodeIds.map((id) => [id, new Set()]));

  for (const edge of edges) {
    const source = String(edge.source);
    const target = String(edge.target);
    if (adjacency.has(source)) {
      adjacency.get(source).add(target);
    }
    if (adjacency.has(target)) {
      adjacency.get(target).add(source);
    }
  }

  return adjacency;
}

function findComponents(nodeIds, adjacency) {
  const visited = new Set();
  const components = [];

  for (const nodeId of nodeIds) {
    if (visited.has(nodeId)) continue;
    const queue = [nodeId];
    const component = [];
    visited.add(nodeId);

    while (queue.length) {
      const current = queue.shift();
      component.push(current);

      for (const next of adjacency.get(current) || []) {
        if (visited.has(next)) continue;
        visited.add(next);
        queue.push(next);
      }
    }

    components.push(component);
  }

  return components;
}

function pickComponentRoot(component, adjacency) {
  return [...component].sort((left, right) => {
    const leftDegree = adjacency.get(left)?.size || 0;
    const rightDegree = adjacency.get(right)?.size || 0;
    if (rightDegree !== leftDegree) {
      return rightDegree - leftDegree;
    }
    return left.localeCompare(right);
  })[0];
}

function buildLayers(component, adjacency) {
  const root = pickComponentRoot(component, adjacency);
  const queue = [{ id: root, depth: 0 }];
  const visited = new Set([root]);
  const layers = [];

  while (queue.length) {
    const { id, depth } = queue.shift();
    if (!layers[depth]) {
      layers[depth] = [];
    }
    layers[depth].push(id);

    const neighbors = [...(adjacency.get(id) || [])].sort((left, right) => {
      const leftDegree = adjacency.get(left)?.size || 0;
      const rightDegree = adjacency.get(right)?.size || 0;
      if (rightDegree !== leftDegree) {
        return rightDegree - leftDegree;
      }
      return left.localeCompare(right);
    });

    for (const next of neighbors) {
      if (visited.has(next) || !component.includes(next)) continue;
      visited.add(next);
      queue.push({ id: next, depth: depth + 1 });
    }
  }

  for (const id of component) {
    if (visited.has(id)) continue;
    if (!layers[layers.length - 1]) {
      layers.push([]);
    }
    layers[layers.length - 1].push(id);
  }

  return layers;
}

function layoutConnectedComponent(component, adjacency, area) {
  const layers = buildLayers(component, adjacency);
  const positions = [];
  const usableWidth = Math.max(area.width - 80, 120);
  const usableHeight = Math.max(area.height - 80, 120);
  const columnGap = layers.length > 1 ? usableWidth / (layers.length - 1) : 0;

  layers.forEach((layer, layerIndex) => {
    const x = area.x + 40 + (layers.length > 1 ? columnGap * layerIndex : usableWidth / 2);
    const rowGap = layer.length > 1 ? usableHeight / (layer.length - 1) : 0;

    layer.forEach((nodeId, rowIndex) => {
      const y = area.y + 40 + (layer.length > 1 ? rowGap * rowIndex : usableHeight / 2);
      positions.push({ id: nodeId, x, y });
    });
  });

  return positions;
}

function layoutIsolatedNodes(nodeIds, area) {
  if (!nodeIds.length) return [];

  const usableWidth = Math.max(area.width - 48, 160);
  const usableHeight = Math.max(area.height - 48, 160);
  const columnCount = Math.max(1, Math.floor(usableWidth / 110));
  const rowCount = Math.ceil(nodeIds.length / columnCount);
  const xGap = columnCount > 1 ? usableWidth / (columnCount - 1) : 0;
  const yGap = rowCount > 1 ? usableHeight / (rowCount - 1) : 0;

  return nodeIds.map((nodeId, index) => {
    const column = index % columnCount;
    const row = Math.floor(index / columnCount);
    return {
      id: nodeId,
      x: area.x + 24 + (columnCount > 1 ? column * xGap : usableWidth / 2),
      y: area.y + 24 + (rowCount > 1 ? row * yGap : usableHeight / 2),
    };
  });
}

function splitArea(area, connectedCount, isolatedCount) {
  if (!connectedCount) {
    return {
      connectedArea: null,
      isolatedArea: area,
    };
  }
  if (!isolatedCount) {
    return {
      connectedArea: area,
      isolatedArea: null,
    };
  }

  const connectedWidth = Math.max(area.width * 0.68, 520);
  const gap = 28;

  return {
    connectedArea: {
      x: area.x,
      y: area.y,
      width: connectedWidth - gap / 2,
      height: area.height,
    },
    isolatedArea: {
      x: area.x + connectedWidth + gap / 2,
      y: area.y,
      width: Math.max(area.width - connectedWidth - gap, 240),
      height: area.height,
    },
  };
}

export function buildTeacherGraphLayout(nodes, edges, viewport = {}) {
  const width = Math.max(viewport.width || 1100, 840);
  const height = Math.max(viewport.height || 680, 560);
  const nodeIds = nodes.map((node) => String(node.id));

  if (!nodeIds.length) {
    return [];
  }

  const adjacency = buildAdjacency(nodeIds, edges);
  const components = findComponents(nodeIds, adjacency)
    .map((component) => ({
      nodeIds: component,
      size: component.length,
    }))
    .sort((left, right) => right.size - left.size);

  const connectedComponents = components.filter((component) => component.size > 1);
  const isolatedNodes = components.filter((component) => component.size === 1).map((component) => component.nodeIds[0]);

  const outerArea = {
    x: 40,
    y: 40,
    width: width - 80,
    height: height - 80,
  };

  const { connectedArea, isolatedArea } = splitArea(
    outerArea,
    connectedComponents.length,
    isolatedNodes.length,
  );

  const positions = [];

  if (connectedArea) {
    const sectionGap = 24;
    const sectionHeight = Math.max(
      (connectedArea.height - sectionGap * Math.max(connectedComponents.length - 1, 0)) / Math.max(connectedComponents.length, 1),
      180,
    );

    connectedComponents.forEach((component, index) => {
      positions.push(
        ...layoutConnectedComponent(component.nodeIds, adjacency, {
          x: connectedArea.x,
          y: connectedArea.y + index * (sectionHeight + sectionGap),
          width: connectedArea.width,
          height: sectionHeight,
        }),
      );
    });
  }

  if (isolatedArea) {
    positions.push(...layoutIsolatedNodes(isolatedNodes, isolatedArea));
  }

  return positions;
}
