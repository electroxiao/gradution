import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const currentDir = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(join(currentDir, "StudentAssignmentWorkPage.vue"), "utf8");

assert.ok(
  source.includes("'has-late-note': isAssignmentOverdue"),
  "editor pane should expose late-note state to its grid layout",
);
assert.ok(
  source.includes(".editor-pane.has-result {\n  grid-template-rows: auto minmax(0, 1fr) 8px minmax(220px, var(--result-pane-height, 50%));\n}"),
  "result pane layout without a late note should give the console its own visible row",
);
assert.ok(
  source.includes(".editor-pane.has-result.has-late-note {\n  grid-template-rows: auto auto minmax(0, 1fr) 8px minmax(220px, var(--result-pane-height, 50%));\n}"),
  "late-note result layout should keep the extra row only when the note is rendered",
);

console.log("StudentAssignmentWorkPage result pane layout tests passed");
