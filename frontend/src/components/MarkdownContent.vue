<template>
  <div class="markdown-body" v-html="html"></div>
</template>

<script setup>
import DOMPurify from "dompurify";
import hljs from "highlight.js/lib/core";
import bash from "highlight.js/lib/languages/bash";
import cpp from "highlight.js/lib/languages/cpp";
import css from "highlight.js/lib/languages/css";
import java from "highlight.js/lib/languages/java";
import javascript from "highlight.js/lib/languages/javascript";
import json from "highlight.js/lib/languages/json";
import markdown from "highlight.js/lib/languages/markdown";
import plaintext from "highlight.js/lib/languages/plaintext";
import python from "highlight.js/lib/languages/python";
import sql from "highlight.js/lib/languages/sql";
import typescript from "highlight.js/lib/languages/typescript";
import xml from "highlight.js/lib/languages/xml";
import MarkdownIt from "markdown-it";
import { computed } from "vue";
import "highlight.js/styles/github.css";

hljs.registerLanguage("bash", bash);
hljs.registerLanguage("sh", bash);
hljs.registerLanguage("shell", bash);
hljs.registerLanguage("cpp", cpp);
hljs.registerLanguage("c++", cpp);
hljs.registerLanguage("css", css);
hljs.registerLanguage("html", xml);
hljs.registerLanguage("java", java);
hljs.registerLanguage("javascript", javascript);
hljs.registerLanguage("js", javascript);
hljs.registerLanguage("json", json);
hljs.registerLanguage("markdown", markdown);
hljs.registerLanguage("md", markdown);
hljs.registerLanguage("plaintext", plaintext);
hljs.registerLanguage("text", plaintext);
hljs.registerLanguage("python", python);
hljs.registerLanguage("py", python);
hljs.registerLanguage("sql", sql);
hljs.registerLanguage("typescript", typescript);
hljs.registerLanguage("ts", typescript);
hljs.registerLanguage("vue", xml);
hljs.registerLanguage("xml", xml);

const props = defineProps({
  content: {
    type: String,
    default: "",
  },
});

const markdownRenderer = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  typographer: true,
  highlight(code, language) {
    const normalizedLanguage = normalizeLanguage(language);
    const escapedLanguage = markdownRenderer.utils.escapeHtml(normalizedLanguage || "text");

    if (normalizedLanguage && hljs.getLanguage(normalizedLanguage)) {
      const highlighted = hljs.highlight(code, {
        language: normalizedLanguage,
        ignoreIllegals: true,
      }).value;
      return `<pre class="code-block"><span class="code-language">${escapedLanguage}</span><code class="hljs language-${escapedLanguage}">${highlighted}</code></pre>`;
    }

    const escapedCode = markdownRenderer.utils.escapeHtml(code);
    return `<pre class="code-block"><span class="code-language">text</span><code class="hljs language-text">${escapedCode}</code></pre>`;
  },
});

markdownRenderer.renderer.rules.link_open = (tokens, index, options, env, self) => {
  const token = tokens[index];
  const targetIndex = token.attrIndex("target");
  const relIndex = token.attrIndex("rel");

  if (targetIndex < 0) {
    token.attrPush(["target", "_blank"]);
  } else {
    token.attrs[targetIndex][1] = "_blank";
  }

  if (relIndex < 0) {
    token.attrPush(["rel", "noopener noreferrer"]);
  } else {
    token.attrs[relIndex][1] = "noopener noreferrer";
  }

  return self.renderToken(tokens, index, options);
};

const html = computed(() => {
  if (!props.content) return "";
  return DOMPurify.sanitize(markdownRenderer.render(props.content), {
    ADD_ATTR: ["target"],
  });
});

function normalizeLanguage(language = "") {
  const trimmed = language.trim().toLowerCase();
  if (!trimmed) return "";

  const aliases = {
    cxx: "cpp",
    "c++": "cpp",
    cmd: "bash",
    console: "bash",
    html: "xml",
    js: "javascript",
    md: "markdown",
    py: "python",
    shell: "bash",
    text: "plaintext",
    ts: "typescript",
    vue: "xml",
  };

  return aliases[trimmed] || trimmed;
}
</script>

<style scoped>
.markdown-body {
  color: #111111;
  line-height: 1.75;
  overflow-wrap: anywhere;
}

.markdown-body :deep(*) {
  box-sizing: border-box;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 18px 0 10px;
  color: #111111;
  line-height: 1.35;
  font-weight: 650;
}

.markdown-body :deep(h1:first-child),
.markdown-body :deep(h2:first-child),
.markdown-body :deep(h3:first-child),
.markdown-body :deep(h4:first-child),
.markdown-body :deep(p:first-child),
.markdown-body :deep(ul:first-child),
.markdown-body :deep(ol:first-child),
.markdown-body :deep(pre:first-child),
.markdown-body :deep(blockquote:first-child),
.markdown-body :deep(table:first-child) {
  margin-top: 0;
}

.markdown-body :deep(h1) {
  font-size: 22px;
}

.markdown-body :deep(h2) {
  font-size: 19px;
}

.markdown-body :deep(h3) {
  font-size: 16px;
}

.markdown-body :deep(h4) {
  font-size: 14px;
}

.markdown-body :deep(p) {
  margin: 0 0 12px;
}

.markdown-body :deep(a) {
  color: #111111;
  text-decoration: none;
  border-bottom: 1px solid #bdbdbd;
}

.markdown-body :deep(a:hover) {
  border-bottom-color: currentColor;
}

.markdown-body :deep(strong) {
  color: #000000;
  font-weight: 700;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 0 0 12px 22px;
  padding: 0;
}

.markdown-body :deep(li) {
  margin: 4px 0;
  padding-left: 2px;
}

.markdown-body :deep(li > p) {
  margin: 6px 0;
}

.markdown-body :deep(blockquote) {
  margin: 14px 0;
  padding: 9px 14px;
  border-left: 3px solid #bdbdbd;
  background: #f7f7f7;
  color: #333333;
}

.markdown-body :deep(blockquote > :last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(code) {
  padding: 2px 6px;
  border-radius: 6px;
  background: #f4f4f4;
  color: #111111;
  font-family: Consolas, "Courier New", monospace;
  font-size: 0.92em;
}

.markdown-body :deep(.code-block) {
  position: relative;
  margin: 14px 0;
  padding: 36px 0 0;
  overflow: hidden;
  border: 1px solid #dedede;
  border-radius: 8px;
  background: #fafafa;
}

.markdown-body :deep(.code-language) {
  position: absolute;
  top: 9px;
  right: 12px;
  color: #666666;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.markdown-body :deep(pre code) {
  display: block;
  min-width: 100%;
  padding: 0 14px 14px;
  overflow-x: auto;
  background: transparent;
  color: #111111;
  font-size: 13px;
  line-height: 1.65;
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

.markdown-body :deep(.hljs) {
  background: transparent;
}

.markdown-body :deep(:last-child) {
  margin-bottom: 0;
}
</style>
