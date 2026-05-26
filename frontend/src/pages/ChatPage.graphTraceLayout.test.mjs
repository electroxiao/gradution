import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const currentDir = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(join(currentDir, "ChatPage.vue"), "utf8");
const assistantBodyIndex = source.indexOf('class="message-body"');
const graphStatusIndex = source.indexOf('class="graph-status-box"');
const selectedPathGraphIndex = source.indexOf("<SelectedPathGraph");

assert.notEqual(assistantBodyIndex, -1, "ChatPage should render assistant message body");
assert.notEqual(graphStatusIndex, -1, "ChatPage should render graph status");
assert.notEqual(selectedPathGraphIndex, -1, "ChatPage should still render selected path graph");
assert.ok(
  graphStatusIndex < assistantBodyIndex,
  "Graph retrieval details should render before long assistant content",
);
assert.equal(source.includes("相关节点信息"), false, "ChatPage should not render related node details");
assert.equal(source.includes("related-graph-"), false, "ChatPage should not keep related node detail styles");
