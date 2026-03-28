class GraphStub {
  constructor() {
    this._graph = {};
    this._nodes = new Map();
    this._edges = [];
  }

  setGraph(value) {
    this._graph = value || {};
  }

  graph() {
    return this._graph;
  }

  setDefaultEdgeLabel(fn) {
    this._edgeLabelFactory = fn;
  }

  setNode(id, value = {}) {
    this._nodes.set(id, { ...value, x: value.x ?? 0, y: value.y ?? 0 });
  }

  node(id) {
    return this._nodes.get(id);
  }

  nodes() {
    return [...this._nodes.keys()];
  }

  nodeCount() {
    return this._nodes.size;
  }

  setEdge(v, w) {
    this._edges.push({ v, w });
  }

  edge() {
    return {};
  }

  edges() {
    return this._edges;
  }

  outEdges(id) {
    return this._edges.filter((edge) => edge.v === id);
  }

  predecessors() {
    return [];
  }

  successors() {
    return [];
  }
}

const dagreStub = {
  graphlib: {
    Graph: GraphStub,
    alg: {
      components(graph) {
        return [graph.nodes()];
      },
      preorder() {
        return [];
      },
      postorder() {
        return [];
      },
    },
  },
  layout(graph) {
    return graph;
  },
};

export default dagreStub;
