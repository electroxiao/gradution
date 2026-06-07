import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import assert from "node:assert/strict";

const __dirname = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(resolve(__dirname, "TeacherAssignmentEditorPage.vue"), "utf8");

assert.match(source, /<h3>题目知识点<\/h3>/);
assert.match(source, /listTeacherKnowledgeNodesApi/);
assert.match(source, /activeQuestion\.value\.knowledge_node_ids/);
assert.match(source, /function addActiveQuestionKnowledgeNode/);
assert.match(source, /function removeActiveQuestionKnowledgeNode/);

console.log("TeacherAssignmentEditorPage knowledge binding checks passed");
