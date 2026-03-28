<template>
  <section v-if="selectedPath" class="path-card">
    <div class="path-header">
      <strong>已选路径</strong>
      <span>hop {{ selectedPath.hop }}</span>
    </div>
    <div class="path-chain">
      <template v-for="(node, index) in nodes" :key="`${node.label}-${index}`">
        <div :class="['path-node', node.kind]">
          <span class="node-label">{{ node.label }}</span>
        </div>
        <div v-if="index < relations.length" class="path-connector">
          <span class="connector-label">{{ relations[index] }}</span>
          <div class="connector-line" />
        </div>
      </template>
    </div>
    <p v-if="selectedPath.reason" class="path-reason">{{ selectedPath.reason }}</p>
  </section>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  facts: {
    type: Array,
    default: () => [],
  },
});

const selectedPath = computed(() =>
  props.facts.find((fact) => fact && fact.type === "selected_path") || null,
);

function humanizeRelation(rawRelation) {
  if (!rawRelation) return "related to";
  const normalized = rawRelation.trim().toUpperCase();
  if (normalized === "DEPENDS_ON") {
    return "depend on";
  }
  return rawRelation
    .trim()
    .toLowerCase()
    .replace(/_/g, " ");
}

function parsePath(pathText, fact) {
  if (!pathText) {
    return {
      nodes: [
        { kind: "seed", label: fact.source || fact.seed || "起点" },
        { kind: "target", label: fact.target || "终点" },
      ],
      relations: [humanizeRelation(fact.relation)],
    };
  }

  const tokens = pathText.split("->").map((part) => part.trim()).filter(Boolean);
  const parsedNodes = [];
  const parsedRelations = [];

  for (const token of tokens) {
    const relationMatch = token.match(/^\(([^,]+)(?:,\s*([^)]+))?\)$/);
    if (relationMatch) {
      parsedRelations.push(humanizeRelation(relationMatch[1]));
    } else {
      parsedNodes.push(token);
    }
  }

  if (parsedNodes.length < 2) {
    return {
      nodes: [
        { kind: "seed", label: fact.source || fact.seed || "起点" },
        { kind: "target", label: fact.target || "终点" },
      ],
      relations: [humanizeRelation(fact.relation)],
    };
  }

  return {
    nodes: parsedNodes.map((node, index) => {
      if (index === 0) return { kind: "seed", label: node };
      if (index === parsedNodes.length - 1) return { kind: "target", label: node };
      return { kind: "middle", label: node };
    }),
    relations: parsedRelations,
  };
}

const nodes = computed(() => {
  const fact = selectedPath.value;
  if (!fact) return [];
  return parsePath(fact.path_text || "", fact).nodes;
});

const relations = computed(() => {
  const fact = selectedPath.value;
  if (!fact) return [];
  return parsePath(fact.path_text || "", fact).relations;
});
</script>

<style scoped>
.path-card {
  margin-top: 14px;
  padding: 14px;
  border-radius: 16px;
  background: linear-gradient(135deg, #eff8ff 0%, #f8fafc 100%);
  border: 1px solid #d6e7f7;
}

.path-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  color: #12324a;
}

.path-chain {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.path-node {
  min-width: 96px;
  max-width: 220px;
  padding: 10px 12px;
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid #d8e4ef;
  box-shadow: 0 6px 14px rgba(18, 50, 74, 0.08);
}

.path-node.seed {
  background: #dff2e7;
}

.path-node.target {
  background: #e4ecff;
}

.path-node.middle {
  background: #ffffff;
}

.node-label {
  display: block;
  font-weight: 600;
  word-break: break-word;
}

.path-connector {
  position: relative;
  display: flex;
  align-items: center;
  width: 110px;
  min-width: 110px;
  height: 46px;
}

.connector-label {
  position: absolute;
  top: -2px;
  left: 50%;
  transform: translateX(-50%);
  padding: 0 6px;
  background: linear-gradient(135deg, #eff8ff 0%, #f8fafc 100%);
  color: #55748f;
  font-size: 12px;
  line-height: 1;
  white-space: nowrap;
}

.connector-line {
  position: relative;
  width: 100%;
  height: 2px;
  margin-top: 14px;
  background: linear-gradient(90deg, #8fb5d8 0%, #4b89c8 100%);
  border-radius: 999px;
}

.connector-line::after {
  content: "";
  position: absolute;
  top: 50%;
  right: -1px;
  width: 10px;
  height: 10px;
  border-top: 2px solid #4b89c8;
  border-right: 2px solid #4b89c8;
  transform: translateY(-50%) rotate(45deg);
}

.path-reason {
  margin: 12px 0 0;
  color: #4b5563;
  line-height: 1.6;
}

@media (max-width: 720px) {
  .path-connector {
    width: 76px;
    min-width: 76px;
  }

  .connector-label {
    font-size: 11px;
  }
}
</style>
