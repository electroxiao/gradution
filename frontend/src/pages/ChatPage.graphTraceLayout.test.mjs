import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const currentDir = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(join(currentDir, "ChatPage.vue"), "utf8");
const assistantBodyIndex = source.indexOf('class="message-body"');
const graphStatusIndex = source.indexOf('class="graph-status-box"');
const graphPathLineIndex = source.indexOf('class="graph-path-line"');

assert.notEqual(assistantBodyIndex, -1, "ChatPage should render assistant message body");
assert.notEqual(graphStatusIndex, -1, "ChatPage should render graph status");
assert.notEqual(graphPathLineIndex, -1, "ChatPage should render one compact graph path");
assert.ok(
  assistantBodyIndex < graphStatusIndex,
  "Graph retrieval status should render below assistant content",
);
assert.ok(
  graphStatusIndex < graphPathLineIndex,
  "Compact graph path should render below graph retrieval status",
);
assert.equal(source.includes("<SelectedPathGraph"), false, "ChatPage should not render the old selected path card");
assert.equal(source.includes("相关节点信息"), false, "ChatPage should not render related node details");
assert.equal(source.includes("related-graph-"), false, "ChatPage should not keep related node detail styles");
