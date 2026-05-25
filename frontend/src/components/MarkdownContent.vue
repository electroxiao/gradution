<template>
  <MarkdownRender
    class="markdown-body"
    custom-id="chat"
    :content="content"
    :final="!animateUpdates"
    :smooth-streaming="false"
    :fade="animateUpdates"
    :typewriter="false"
    :render-code-blocks-as-pre="true"
    :code-block-stream="true"
    :show-tooltips="false"
  />
</template>

<script setup>
import MarkdownRender from "markstream-vue";
import "markstream-vue/index.css";

defineProps({
  content: {
    type: String,
    default: "",
  },
  animateUpdates: {
    type: Boolean,
    default: false,
  },
});
</script>

<style scoped>
.markdown-body {
  --fade-duration: 0.4s;
  --stream-update-fade-duration: 0.4s;
  --ms-text-body: 1em;
  --ms-leading-body: 1.75;
  --ms-text-h1: 1em;
  --ms-text-h2: 1em;
  --ms-text-h3: 1em;
  --ms-text-h4: 1em;
  --ms-text-h5: 1em;
  --ms-text-h6: 1em;
  --ms-weight-h1: 650;
  --ms-weight-h2: 650;
  --ms-weight-h3: 650;
  --ms-weight-h4: 650;
  --ms-flow-paragraph-y: 0 0 12px;
  --ms-flow-heading-1-mt: 18px;
  --ms-flow-heading-1-mb: 10px;
  --ms-flow-heading-2-mt: 18px;
  --ms-flow-heading-2-mb: 10px;
  --ms-flow-heading-3-mt: 18px;
  --ms-flow-heading-3-mb: 10px;
  --ms-flow-heading-4-mt: 18px;
  --ms-flow-heading-4-mb: 10px;
  --ms-flow-list-y: 0 0 12px;
  --ms-flow-list-indent: 22px;
  --ms-flow-blockquote-y: 14px;
  --ms-flow-blockquote-indent: 14px;
  --ms-font-mono: Consolas, "Courier New", monospace;
  color: #111111;
  font-size: inherit;
  line-height: 1.75;
  overflow-wrap: anywhere;
}

.markdown-body :deep(*) {
  box-sizing: border-box;
}

.markdown-body :deep(.heading-node) {
  color: #111111;
  font-size: 1em !important;
  line-height: 1.35;
  font-weight: 650;
}

.markdown-body :deep(.markdown-renderer),
.markdown-body :deep(.node-slot),
.markdown-body :deep(.node-content),
.markdown-body :deep(.text-node),
.markdown-body :deep(.strong-node),
.markdown-body :deep(.emphasis-node),
.markdown-body :deep(.paragraph-node),
.markdown-body :deep(.list-node),
.markdown-body :deep(.list-item),
.markdown-body :deep(.blockquote),
.markdown-body :deep(th),
.markdown-body :deep(td) {
  font-size: inherit !important;
}

.markdown-body :deep(.list-item::marker) {
  font-size: 1em;
}

.markdown-body :deep(.heading-node:first-child),
.markdown-body :deep(.paragraph-node:first-child),
.markdown-body :deep(.list-node:first-child),
.markdown-body :deep(.code-block:first-child),
.markdown-body :deep(.blockquote:first-child),
.markdown-body :deep(table:first-child) {
  margin-top: 0;
}

.markdown-body :deep(.paragraph-node) {
  margin: 0 0 12px;
}

.markdown-body :deep(.link-node) {
  color: #111111;
  text-decoration: none;
  border-bottom: 1px solid #bdbdbd;
}

.markdown-body :deep(.link-node:hover) {
  border-bottom-color: currentColor;
}

.markdown-body :deep(.strong-node) {
  color: #000000;
  font-weight: 700;
}

.markdown-body :deep(.list-node) {
  margin: 0 0 12px 22px;
  padding: 0;
}

.markdown-body :deep(.list-item) {
  margin: 4px 0;
  padding-left: 2px;
}

.markdown-body :deep(.blockquote) {
  margin: 14px 0;
  padding: 9px 14px;
  border-left: 3px solid #bdbdbd;
  background: #f7f7f7;
  color: #333333;
}

.markdown-body :deep(.inline-code) {
  padding: 2px 6px;
  border-radius: 6px;
  background: #f4f4f4;
  color: #111111;
  font-family: Consolas, "Courier New", monospace;
  font-size: 0.92em;
}

.markdown-body :deep(pre) {
  margin: 14px 0;
  padding: 14px;
  overflow-x: auto;
  border: 1px solid #dedede;
  border-radius: 8px;
  background: #fafafa;
  color: #111111;
  font-size: 13px;
  line-height: 1.65;
}

.markdown-body :deep(pre:focus),
.markdown-body :deep(pre:focus-visible),
.markdown-body :deep(pre[class^="language-"]:focus),
.markdown-body :deep(pre[class*=" language-"]:focus),
.markdown-body :deep(.code-block-container:focus),
.markdown-body :deep(.code-block-container:focus-visible) {
  outline: none !important;
  outline-offset: 0 !important;
}

.markdown-body :deep(pre code) {
  padding: 0;
  background: transparent;
  color: inherit;
  font-family: Consolas, "Courier New", monospace;
  white-space: pre;
}

.markdown-body :deep(table) {
  display: block;
  width: 100%;
  margin: 14px 0;
  overflow-x: auto;
  border-collapse: collapse;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  padding: 8px 10px;
  border: 1px solid #dedede;
  text-align: left;
  vertical-align: top;
}

.markdown-body :deep(th) {
  background: #f5f5f5;
  color: #111111;
  font-weight: 650;
}

.markdown-body :deep(hr) {
  margin: 18px 0;
  border: 0;
  border-top: 1px solid #dedede;
}

.markdown-body :deep(:last-child) {
  margin-bottom: 0;
}
</style>
