const DEFAULTS = Object.freeze({
  nodeWidth: 286,
  nodeHeight: 220,
  horizontalGap: 40,
  verticalGap: 116,
  horizontalPadding: 120,
  verticalPadding: 110,
  minimumWidth: 980,
});

const stableLabel = (node) =>
  String(node?.display_name || node?.id || "").toLocaleLowerCase();

const finiteDepth = (value) => {
  const depth = Number(value);
  return Number.isFinite(depth) && depth >= 0 ? depth : undefined;
};

const buildAdjacency = (nodes, edges) => {
  const ids = new Set(nodes.map((node) => node.id));
  const incoming = new Map();
  const outgoing = new Map();

  for (const id of ids) {
    incoming.set(id, []);
    outgoing.set(id, []);
  }

  for (const edge of edges) {
    if (!ids.has(edge.source) || !ids.has(edge.target)) continue;
    outgoing.get(edge.source).push(edge.target);
    incoming.get(edge.target).push(edge.source);
  }

  for (const values of incoming.values()) values.sort();
  for (const values of outgoing.values()) values.sort();

  return { incoming, outgoing };
};

const breadthFirstDistances = (rootId, adjacency) => {
  const distances = new Map([[rootId, 0]]);
  const queue = [rootId];

  for (let index = 0; index < queue.length; index += 1) {
    const current = queue[index];
    const nextDistance = distances.get(current) + 1;

    for (const next of adjacency.get(current) ?? []) {
      if (distances.has(next)) continue;
      distances.set(next, nextDistance);
      queue.push(next);
    }
  }

  return distances;
};

const inferLevel = (node, upstreamDistance, downstreamDistance) => {
  if (upstreamDistance === 0 || downstreamDistance === 0) return 0;

  const roles = new Set(node.roles ?? []);
  const upstreamRole =
    roles.has("parent") || roles.has("ancestor");
  const downstreamRole =
    roles.has("child") || roles.has("descendant");

  const declaredUpstream = finiteDepth(node.upstream_depth);
  const declaredDownstream = finiteDepth(node.downstream_depth);

  if (upstreamDistance != null && downstreamDistance == null) {
    return -upstreamDistance;
  }

  if (downstreamDistance != null && upstreamDistance == null) {
    return downstreamDistance;
  }

  if (upstreamDistance != null && downstreamDistance != null) {
    if (upstreamRole && !downstreamRole) return -upstreamDistance;
    if (downstreamRole && !upstreamRole) return downstreamDistance;

    if (
      declaredUpstream != null &&
      declaredDownstream == null
    ) {
      return -Math.max(1, declaredUpstream);
    }

    if (
      declaredDownstream != null &&
      declaredUpstream == null
    ) {
      return Math.max(1, declaredDownstream);
    }

    return upstreamDistance <= downstreamDistance
      ? -upstreamDistance
      : downstreamDistance;
  }

  if (declaredUpstream != null && declaredUpstream > 0) {
    return -declaredUpstream;
  }

  if (declaredDownstream != null && declaredDownstream > 0) {
    return declaredDownstream;
  }

  if (upstreamRole && !downstreamRole) return -1;
  if (downstreamRole && !upstreamRole) return 1;

  return 1;
};

const average = (values) => {
  if (!values.length) return undefined;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
};

const reorderLayer = (
  layer,
  neighborIds,
  orderById,
  nodeById,
) =>
  [...layer].sort((left, right) => {
    const leftAverage = average(
      (neighborIds.get(left.id) ?? [])
        .map((id) => orderById.get(id))
        .filter((value) => value != null),
    );
    const rightAverage = average(
      (neighborIds.get(right.id) ?? [])
        .map((id) => orderById.get(id))
        .filter((value) => value != null),
    );

    if (leftAverage != null && rightAverage != null) {
      const difference = leftAverage - rightAverage;
      if (Math.abs(difference) > 0.0001) return difference;
    } else if (leftAverage != null) {
      return -1;
    } else if (rightAverage != null) {
      return 1;
    }

    const labelDifference = stableLabel(left).localeCompare(
      stableLabel(right),
    );
    if (labelDifference) return labelDifference;

    return String(left.id).localeCompare(String(right.id));
  });

const optimizeLayerOrder = (
  layers,
  levels,
  incoming,
  outgoing,
  nodeById,
) => {
  const ordered = new Map(
    [...layers.entries()].map(([level, nodes]) => [
      level,
      [...nodes].sort((left, right) =>
        stableLabel(left).localeCompare(stableLabel(right)) ||
        String(left.id).localeCompare(String(right.id)),
      ),
    ]),
  );

  const updateOrderMap = () => {
    const orderById = new Map();

    for (const level of levels) {
      (ordered.get(level) ?? []).forEach((node, index) => {
        orderById.set(node.id, index);
      });
    }

    return orderById;
  };

  for (let pass = 0; pass < 3; pass += 1) {
    let orderById = updateOrderMap();

    for (const level of levels.filter((value) => value > 0)) {
      ordered.set(
        level,
        reorderLayer(
          ordered.get(level) ?? [],
          incoming,
          orderById,
          nodeById,
        ),
      );
      orderById = updateOrderMap();
    }

    for (
      const level of levels
        .filter((value) => value < 0)
        .sort((left, right) => right - left)
    ) {
      ordered.set(
        level,
        reorderLayer(
          ordered.get(level) ?? [],
          outgoing,
          orderById,
          nodeById,
        ),
      );
      orderById = updateOrderMap();
    }
  }

  return ordered;
};

export const buildLayeredLayout = (
  graph,
  overrides = {},
) => {
  const options = { ...DEFAULTS, ...overrides };
  const nodes = graph?.nodes ?? [];
  const edges = graph?.edges ?? [];
  const rootId = graph?.root_id;

  if (!rootId || !nodes.length) {
    return {
      rootId,
      nodes: [],
      edges: [],
      levels: [],
      canvasWidth: options.minimumWidth,
      canvasHeight: 560,
      nodeWidth: options.nodeWidth,
      nodeHeight: options.nodeHeight,
    };
  }

  const nodeById = new Map(
    nodes.map((node) => [node.id, node]),
  );
  const { incoming, outgoing } = buildAdjacency(nodes, edges);

  const upstreamDistances = breadthFirstDistances(
    rootId,
    incoming,
  );
  const downstreamDistances = breadthFirstDistances(
    rootId,
    outgoing,
  );

  const layers = new Map();
  const levelById = new Map();

  for (const node of nodes) {
    const level =
      node.id === rootId
        ? 0
        : inferLevel(
            node,
            upstreamDistances.get(node.id),
            downstreamDistances.get(node.id),
          );

    levelById.set(node.id, level);

    if (!layers.has(level)) layers.set(level, []);
    layers.get(level).push(node);
  }

  const levels = [...layers.keys()].sort(
    (left, right) => left - right,
  );
  const orderedLayers = optimizeLayerOrder(
    layers,
    levels,
    incoming,
    outgoing,
    nodeById,
  );

  const widestLayer = Math.max(
    1,
    ...[...orderedLayers.values()].map((layer) => layer.length),
  );
  const layerWidth =
    widestLayer * options.nodeWidth +
    Math.max(0, widestLayer - 1) * options.horizontalGap;

  const canvasWidth = Math.max(
    options.minimumWidth,
    layerWidth + options.horizontalPadding * 2,
  );

  const minimumLevel = Math.min(...levels);
  const maximumLevel = Math.max(...levels);
  const rowPitch = options.nodeHeight + options.verticalGap;
  const canvasHeight =
    (maximumLevel - minimumLevel) * rowPitch +
    options.nodeHeight +
    options.verticalPadding * 2;

  const positionedNodes = [];

  for (const level of levels) {
    const layer = orderedLayers.get(level) ?? [];
    const width =
      layer.length * options.nodeWidth +
      Math.max(0, layer.length - 1) * options.horizontalGap;
    const startX = (canvasWidth - width) / 2;
    const y =
      options.verticalPadding +
      (level - minimumLevel) * rowPitch;

    layer.forEach((node, index) => {
      positionedNodes.push({
        ...node,
        level,
        x:
          startX +
          index * (options.nodeWidth + options.horizontalGap),
        y,
      });
    });
  }

  return {
    rootId,
    nodes: positionedNodes,
    edges: edges.filter(
      (edge) =>
        nodeById.has(edge.source) &&
        nodeById.has(edge.target),
    ),
    levels,
    levelById,
    canvasWidth,
    canvasHeight,
    nodeWidth: options.nodeWidth,
    nodeHeight: options.nodeHeight,
  };
};

export const createEdgePath = (
  sourceRect,
  targetRect,
) => {
  const sourceCenterY =
    sourceRect.top + sourceRect.height / 2;
  const targetCenterY =
    targetRect.top + targetRect.height / 2;
  const downward = sourceCenterY <= targetCenterY;

  const startX = sourceRect.left + sourceRect.width / 2;
  const startY = downward
    ? sourceRect.top + sourceRect.height
    : sourceRect.top;
  const endX = targetRect.left + targetRect.width / 2;
  const endY = downward
    ? targetRect.top
    : targetRect.top + targetRect.height;
  const middleY = (startY + endY) / 2;

  return [
    `M ${startX} ${startY}`,
    `C ${startX} ${middleY},`,
    `${endX} ${middleY},`,
    `${endX} ${endY}`,
  ].join(" ");
};
