<template>
  <div ref="editorHost" class="readonly-code-block" :class="{ compact }"></div>
</template>

<script setup>
import { defaultHighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { java } from "@codemirror/lang-java";
import { EditorState } from "@codemirror/state";
import { EditorView, lineNumbers } from "@codemirror/view";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  code: {
    type: String,
    default: "",
  },
  showLineNumbers: {
    type: Boolean,
    default: true,
  },
  compact: {
    type: Boolean,
    default: false,
  },
  background: {
    type: String,
    default: "#ffffff",
  },
});

const editorHost = ref(null);
let editorView = null;

onMounted(() => {
  editorView = new EditorView({
    parent: editorHost.value,
    state: EditorState.create({
      doc: props.code,
      extensions: [
        ...(props.showLineNumbers ? [lineNumbers()] : []),
        java(),
        syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
        EditorState.readOnly.of(true),
        EditorView.editable.of(false),
        EditorView.lineWrapping,
        EditorView.theme({
          "&": {
            backgroundColor: "var(--readonly-code-bg)",
          },
          ".cm-scroller": {
            fontFamily: 'Consolas, "Courier New", monospace',
            lineHeight: "1.65",
          },
          ".cm-content": {
            caretColor: "transparent",
          },
          ".cm-gutters": {
            backgroundColor: "var(--readonly-code-bg)",
            borderRight: "1px solid #e3e7ed",
            color: "#7b8da1",
          },
          ".cm-line": {
            padding: "0 10px",
          },
          "&.cm-focused": {
            outline: "none",
          },
          "&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection, .cm-line::selection, .cm-line *::selection": {
            backgroundColor: "#2563eb !important",
            color: "#ffffff !important",
          },
        }),
      ],
    }),
  });
});

watch(
  () => props.code,
  (value) => {
    if (!editorView) return;
    const current = editorView.state.doc.toString();
    const next = value || "";
    if (next === current) return;
    editorView.dispatch({
      changes: { from: 0, to: current.length, insert: next },
    });
  },
);

onBeforeUnmount(() => {
  editorView?.destroy();
});
</script>

<style scoped>
.readonly-code-block {
  --readonly-code-bg: v-bind(background);
  overflow: hidden;
  border: 1px solid #e3e7ed;
  border-radius: 8px;
  background: var(--readonly-code-bg);
}

.readonly-code-block :deep(.cm-editor) {
  min-height: 120px;
  background: var(--readonly-code-bg);
  color: #10283d;
  font-size: 13px;
  font-weight: 400;
}

.readonly-code-block :deep(.cm-line),
.readonly-code-block :deep(.cm-line *) {
  font-weight: 400 !important;
}

.readonly-code-block :deep(.cm-scroller) {
  overflow: visible !important;
}

.readonly-code-block.compact :deep(.cm-editor) {
  min-height: 0;
}

.readonly-code-block.compact {
  border: 0;
}

.readonly-code-block.compact :deep(.cm-content) {
  padding: 8px 0;
}
</style>
