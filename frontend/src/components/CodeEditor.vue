<template>
  <div ref="editorHost" class="code-editor"></div>
</template>

<script setup>
import { closeBrackets } from "@codemirror/autocomplete";
import { defaultKeymap, history, historyKeymap, indentWithTab } from "@codemirror/commands";
import { bracketMatching, defaultHighlightStyle, indentOnInput, syntaxHighlighting } from "@codemirror/language";
import { java } from "@codemirror/lang-java";
import { EditorState } from "@codemirror/state";
import {
  drawSelection,
  dropCursor,
  EditorView,
  highlightActiveLine,
  highlightActiveLineGutter,
  keymap,
  lineNumbers,
} from "@codemirror/view";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  modelValue: {
    type: String,
    default: "",
  },
});

const emit = defineEmits(["update:modelValue"]);
const editorHost = ref(null);
let editorView = null;
let isInternalUpdate = false;

onMounted(() => {
  editorView = new EditorView({
    parent: editorHost.value,
    state: EditorState.create({
      doc: props.modelValue,
      extensions: [
        lineNumbers(),
        highlightActiveLineGutter(),
        history(),
        drawSelection(),
        dropCursor(),
        indentOnInput(),
        bracketMatching(),
        closeBrackets(),
        java(),
        syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
        highlightActiveLine(),
        keymap.of([indentWithTab, ...defaultKeymap, ...historyKeymap]),
        EditorView.lineWrapping,
        EditorView.updateListener.of((update) => {
          if (!update.docChanged) return;
          isInternalUpdate = true;
          emit("update:modelValue", update.state.doc.toString());
          isInternalUpdate = false;
        }),
      ],
    }),
  });
});

watch(
  () => props.modelValue,
  (value) => {
    if (!editorView || isInternalUpdate) return;
    const current = editorView.state.doc.toString();
    if (value === current) return;
    editorView.dispatch({
      changes: { from: 0, to: current.length, insert: value || "" },
    });
  },
);

onBeforeUnmount(() => {
  editorView?.destroy();
});
</script>

<style scoped>
.code-editor {
  height: 100%;
  min-height: 360px;
  border: 1px solid #e0e7ef;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}

.code-editor :deep(.cm-editor) {
  height: 100%;
  min-height: 360px;
  font-size: 14px;
}

.code-editor :deep(.cm-scroller) {
  font-family: Consolas, "Courier New", monospace;
  line-height: 1.65;
}

.code-editor :deep(.cm-gutters) {
  border-right: 1px solid #edf2f7;
  background: #f8fafc;
  color: #7b8da1;
}

.code-editor :deep(.cm-activeLine),
.code-editor :deep(.cm-activeLineGutter) {
  background: #f5f9ff;
}

.code-editor :deep(.cm-focused) {
  outline: none;
}
</style>
