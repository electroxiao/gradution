<template>
  <section class="editor-page">
    <header class="editor-toolbar">
      <div>
        <p class="eyebrow">Assignment Editor</p>
        <h2>{{ isNew ? "新建作业" : "编辑作业" }}</h2>
        <p>{{ form.questions.length }} 题，已选择 {{ form.student_ids.length }} 名学生</p>
      </div>
      <div class="toolbar-actions">
        <router-link class="secondary-link" to="/teacher/assignments">返回列表</router-link>
        <router-link
          v-if="!isNew"
          class="secondary-link"
          :to="`/teacher/assignments/${assignmentId}/progress`"
        >
          完成情况
        </router-link>
        <button type="button" class="primary-btn" :disabled="saving" @click="saveAssignment">
          {{ saving ? "保存中..." : "保存作业" }}
        </button>
      </div>
    </header>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>
    <p v-if="successMessage" class="feedback success">{{ successMessage }}</p>

    <section class="assignment-meta">
      <label class="title-field">
        作业标题
        <input v-model="form.title" placeholder="例如：字符串比较练习" />
      </label>
      <label>
        状态
        <select v-model="form.status">
          <option value="draft">草稿</option>
          <option value="published">发布</option>
          <option value="closed">关闭</option>
        </select>
      </label>
      <label class="description-field">
        作业说明
        <textarea v-model="form.description" rows="2" placeholder="写给学生的作业说明" />
      </label>
    </section>

    <main class="editor-workbench">
      <aside class="editor-sidebar">
        <section class="side-panel">
          <div class="panel-title">
            <h3>发布学生</h3>
            <span>{{ form.student_ids.length }} / {{ students.length }}</span>
          </div>
          <div class="student-grid">
            <label v-for="student in students" :key="student.id" class="student-check">
              <input v-model="form.student_ids" type="checkbox" :value="student.id" />
              <span>{{ student.username }}</span>
            </label>
          </div>
        </section>

        <section class="side-panel question-index">
          <div class="panel-title">
            <h3>题目目录</h3>
            <button type="button" @click="addQuestion">新增</button>
          </div>
          <article
            v-for="(question, qIndex) in form.questions"
            :key="question.localKey"
            class="question-tab"
            :class="{ active: qIndex === activeQuestionIndex }"
            @click="selectQuestion(qIndex)"
          >
            <div class="question-tab-copy">
              <span>第 {{ qIndex + 1 }} 题</span>
              <strong>{{ question.title || "未命名题目" }}</strong>
              <small>{{ question.test_cases.length }} 个测试用例</small>
            </div>
            <div class="question-tab-actions">
              <button type="button" :disabled="qIndex === 0" @click.stop="moveQuestion(qIndex, -1)">↑</button>
              <button
                type="button"
                :disabled="qIndex === form.questions.length - 1"
                @click.stop="moveQuestion(qIndex, 1)"
              >
                ↓
              </button>
              <button type="button" @click.stop="removeQuestion(qIndex)">删</button>
            </div>
          </article>
        </section>
      </aside>

      <section class="editor-main">
        <section class="ai-panel">
          <div>
            <h3>AI 生成题目草稿</h3>
            <p>生成后会追加到左侧题目目录，保存前可以继续修改。</p>
          </div>
          <div class="ai-fields">
            <input v-model="generateKnowledge" placeholder="知识点，例如 String equals" />
            <input v-model="generateRequirement" placeholder="题目要求，例如 比较 == 和 equals 的区别" />
            <button type="button" :disabled="generating || !generateRequirement.trim()" @click="generateQuestion">
              {{ generating ? "生成中..." : "生成并追加" }}
            </button>
          </div>
        </section>

        <section v-if="activeQuestion" class="question-editor">
          <div class="section-heading">
            <div>
              <span>第 {{ activeQuestionIndex + 1 }} 题</span>
              <h3>{{ activeQuestion.title || "未命名题目" }}</h3>
            </div>
            <button type="button" @click="addTestCase(activeQuestion)">新增用例</button>
          </div>

          <label>
            题目标题
            <input v-model="activeQuestion.title" placeholder="题目标题" />
          </label>
          <label>
            题目描述
            <textarea
              v-model="activeQuestion.prompt"
              class="prompt-input"
              rows="10"
              placeholder="题目描述、输入输出要求"
            />
          </label>

          <div class="case-table">
            <div class="case-head">
              <span>输入</span>
              <span>期望输出</span>
              <span>示例</span>
              <span>操作</span>
            </div>
            <article
              v-for="(testCase, cIndex) in activeQuestion.test_cases"
              :key="testCase.localKey"
              class="case-row"
            >
              <textarea v-model="testCase.input_data" rows="2" placeholder="stdin 输入" />
              <textarea v-model="testCase.expected_output" rows="2" placeholder="期望 stdout" />
              <label class="sample-check">
                <input v-model="testCase.is_sample" type="checkbox" />
                <span>示例</span>
              </label>
              <button type="button" class="ghost-btn" @click="removeTestCase(activeQuestion, cIndex)">删除</button>
            </article>
          </div>
        </section>

        <section v-else class="empty-editor">
          <strong>还没有题目</strong>
          <p>新增一道题目，或使用 AI 生成题目草稿。</p>
          <button type="button" class="primary-btn" @click="addQuestion">新增题目</button>
        </section>
      </section>
    </main>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  createTeacherAssignmentApi,
  generateAssignmentQuestionApi,
  getTeacherAssignmentApi,
  updateTeacherAssignmentApi,
  updateTeacherAssignmentQuestionsApi,
} from "../api/assignments";
import { listTeacherStudentsApi } from "../api/teacher";
import { clearAuthSession } from "../utils/authStorage";

const route = useRoute();
const router = useRouter();
const isNew = computed(() => route.params.assignmentId === undefined);
const assignmentId = computed(() => Number(route.params.assignmentId));
const students = ref([]);
const errorMessage = ref("");
const successMessage = ref("");
const saving = ref(false);
const generating = ref(false);
const generateKnowledge = ref("");
const generateRequirement = ref("");
const activeQuestionIndex = ref(0);
const form = ref({
  title: "",
  description: "",
  status: "draft",
  student_ids: [],
  questions: [],
});

const activeQuestion = computed(() => form.value.questions[activeQuestionIndex.value] || null);

onMounted(async () => {
  await loadStudents();
  if (!isNew.value) {
    await loadAssignment();
  } else {
    addQuestion();
  }
});

async function loadStudents() {
  try {
    const { data } = await listTeacherStudentsApi();
    students.value = data;
  } catch (error) {
    handleApiError(error, "加载学生失败。");
  }
}

async function loadAssignment() {
  try {
    const { data } = await getTeacherAssignmentApi(assignmentId.value);
    applyAssignmentData(data);
  } catch (error) {
    handleApiError(error, "加载作业失败。");
  }
}

function applyAssignmentData(data) {
  form.value = {
    title: data.title,
    description: data.description || "",
    status: data.status,
    student_ids: data.assigned_students.map((item) => item.id),
    questions: data.questions.map(normalizeQuestion),
  };
  activeQuestionIndex.value = Math.min(activeQuestionIndex.value, Math.max(form.value.questions.length - 1, 0));
}

function normalizeQuestion(question = {}) {
  return {
    id: question.id,
    localKey: question.id || `q-${Date.now()}-${Math.random()}`,
    title: question.title || "",
    prompt: question.prompt || "",
    language: "java",
    sort_order: question.sort_order || 0,
    test_cases: (question.test_cases || []).map((item) => ({
      id: item.id,
      localKey: item.id || `c-${Date.now()}-${Math.random()}`,
      input_data: item.input_data || "",
      expected_output: item.expected_output || "",
      is_sample: item.is_sample !== false,
      sort_order: item.sort_order || 0,
    })),
  };
}

function selectQuestion(index) {
  activeQuestionIndex.value = index;
}

function addQuestion(source = {}) {
  form.value.questions.push(
    normalizeQuestion({
      title: source.title || "",
      prompt: source.prompt || "",
      test_cases: source.test_cases || [
        { input_data: "", expected_output: "", is_sample: true, sort_order: 0 },
      ],
    }),
  );
  activeQuestionIndex.value = form.value.questions.length - 1;
}

function removeQuestion(index) {
  form.value.questions.splice(index, 1);
  if (!form.value.questions.length) {
    activeQuestionIndex.value = 0;
    return;
  }
  activeQuestionIndex.value = Math.min(activeQuestionIndex.value, form.value.questions.length - 1);
}

function moveQuestion(index, direction) {
  const next = index + direction;
  if (next < 0 || next >= form.value.questions.length) return;
  const [item] = form.value.questions.splice(index, 1);
  form.value.questions.splice(next, 0, item);

  if (activeQuestionIndex.value === index) {
    activeQuestionIndex.value = next;
  } else if (activeQuestionIndex.value === next) {
    activeQuestionIndex.value = index;
  }
}

function addTestCase(question) {
  question.test_cases.push({
    localKey: `c-${Date.now()}-${Math.random()}`,
    input_data: "",
    expected_output: "",
    is_sample: true,
    sort_order: question.test_cases.length,
  });
}

function removeTestCase(question, index) {
  question.test_cases.splice(index, 1);
}

async function generateQuestion() {
  generating.value = true;
  errorMessage.value = "";
  try {
    const { data } = await generateAssignmentQuestionApi({
      knowledge_point: generateKnowledge.value,
      requirement: generateRequirement.value,
    });
    addQuestion(data);
    successMessage.value = "题目草稿已追加，请检查后保存。";
  } catch (error) {
    handleApiError(error, "生成题目失败。");
  } finally {
    generating.value = false;
  }
}

async function saveAssignment() {
  saving.value = true;
  errorMessage.value = "";
  successMessage.value = "";
  try {
    const payload = buildPayload();
    if (isNew.value) {
      const { data } = await createTeacherAssignmentApi(payload);
      applyAssignmentData(data);
      router.replace(`/teacher/assignments/${data.id}`);
      successMessage.value = "作业已创建。";
    } else {
      await updateTeacherAssignmentApi(assignmentId.value, {
        title: payload.title,
        description: payload.description,
        status: payload.status,
        student_ids: payload.student_ids,
      });
      const { data } = await updateTeacherAssignmentQuestionsApi(assignmentId.value, { questions: payload.questions });
      applyAssignmentData(data);
      successMessage.value = "作业已保存。";
    }
  } catch (error) {
    handleApiError(error, "保存作业失败。");
  } finally {
    saving.value = false;
  }
}

function buildPayload() {
  return {
    title: form.value.title,
    description: form.value.description,
    status: form.value.status,
    student_ids: form.value.student_ids,
    questions: form.value.questions.map((question, qIndex) => ({
      id: question.id,
      title: question.title,
      prompt: question.prompt,
      language: "java",
      sort_order: qIndex,
      test_cases: question.test_cases.map((testCase, cIndex) => ({
        id: testCase.id,
        input_data: testCase.input_data,
        expected_output: testCase.expected_output,
        is_sample: testCase.is_sample,
        sort_order: cIndex,
      })),
    })),
  };
}

function handleApiError(error, fallbackMessage) {
  const status = error?.response?.status;
  if (status === 401 || status === 403) {
    clearAuthSession();
    router.push("/login");
    return;
  }
  errorMessage.value = error?.response?.data?.detail || fallbackMessage;
}
</script>

<style scoped>
.editor-page {
  display: grid;
  gap: 14px;
}

.editor-toolbar,
.toolbar-actions,
.panel-title,
.section-heading,
.ai-panel,
.ai-fields {
  display: flex;
  align-items: center;
  gap: 12px;
}

.editor-toolbar {
  justify-content: space-between;
}

.editor-toolbar h2 {
  margin: 6px 0 6px;
  color: #0f2840;
  font-size: 32px;
}

.editor-toolbar p,
.ai-panel p,
.panel-title span,
.section-heading span {
  margin: 0;
  color: #6f8297;
}

.eyebrow {
  margin: 0;
  color: #5b86b3;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.assignment-meta,
.side-panel,
.ai-panel,
.question-editor,
.empty-editor,
.feedback {
  border: 1px solid #e2ebf4;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
}

.assignment-meta {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 160px minmax(320px, 1.4fr);
  gap: 12px;
  padding: 14px;
}

.title-field,
.description-field {
  min-width: 0;
}

.editor-workbench {
  display: grid;
  grid-template-columns: 310px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}

.editor-sidebar,
.editor-main {
  display: grid;
  gap: 14px;
}

.editor-sidebar {
  position: sticky;
  top: 18px;
}

.side-panel,
.question-editor,
.empty-editor {
  padding: 14px;
}

.panel-title,
.section-heading {
  justify-content: space-between;
}

.panel-title h3,
.section-heading h3,
.ai-panel h3 {
  margin: 0;
  color: #10283d;
}

.student-grid {
  display: grid;
  gap: 8px;
  max-height: 190px;
  overflow: auto;
  padding-top: 10px;
}

.student-check {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #f8fbff;
}

.student-check input,
.sample-check input {
  width: auto;
}

.question-index {
  display: grid;
  gap: 10px;
}

.question-tab {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  padding: 10px;
  border: 1px solid #e2ebf4;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
}

.question-tab.active {
  border-color: #9cc7ef;
  background: #f3f9ff;
}

.question-tab-copy {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.question-tab-copy span,
.question-tab-copy small {
  color: #6f8297;
  font-size: 12px;
}

.question-tab-copy strong {
  color: #10283d;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.question-tab-actions {
  display: flex;
  gap: 4px;
}

.question-tab-actions button {
  min-width: 32px;
  padding: 0;
}

.ai-panel {
  justify-content: space-between;
  padding: 14px;
}

.ai-fields {
  flex: 1;
  justify-content: flex-end;
}

.ai-fields input {
  max-width: 260px;
}

.question-editor {
  display: grid;
  gap: 12px;
}

label {
  display: grid;
  gap: 6px;
  color: #34495f;
  font-size: 14px;
}

input,
textarea,
select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d7e5f3;
  border-radius: 8px;
  color: #12263a;
  background: #fff;
}

textarea {
  resize: none;
}

.prompt-input,
.case-row textarea {
  font-family: Consolas, "Courier New", monospace;
}

.description-field textarea {
  min-height: clamp(72px, 9vh, 108px);
}

.prompt-input {
  min-height: clamp(240px, 34vh, 420px);
}

.case-row textarea {
  min-height: clamp(54px, 8vh, 82px);
  max-height: 120px;
}

button,
.secondary-link,
.primary-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid #d7e5f3;
  border-radius: 8px;
  background: #fff;
  color: #18344f;
  cursor: pointer;
  text-decoration: none;
  white-space: nowrap;
}

.primary-btn,
.ai-fields button,
.panel-title button,
.section-heading button {
  background: #10283d;
  border-color: #10283d;
  color: #fff;
}

.ghost-btn {
  color: #b42318;
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.case-table {
  border: 1px solid #e2ebf4;
  border-radius: 8px;
  overflow: hidden;
}

.case-head,
.case-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 92px 74px;
  gap: 10px;
  align-items: center;
  padding: 10px;
}

.case-head {
  background: #f8fbff;
  color: #6f8297;
  font-size: 13px;
  font-weight: 700;
}

.case-row {
  border-top: 1px solid #eef3f8;
}

.sample-check {
  display: flex;
  align-items: center;
  gap: 6px;
}

.empty-editor {
  display: grid;
  justify-items: start;
  gap: 10px;
  color: #6f8297;
}

.empty-editor strong {
  color: #10283d;
  font-size: 20px;
}

.empty-editor p {
  margin: 0;
}

.feedback {
  padding: 12px 14px;
}

.feedback.error {
  color: #b42318;
  background: #fff8f8;
}

.feedback.success {
  color: #027a48;
  background: #ecfdf3;
}

@media (max-width: 1180px) {
  .assignment-meta,
  .editor-workbench,
  .case-head,
  .case-row {
    grid-template-columns: 1fr;
  }

  .editor-sidebar {
    position: static;
  }

  .ai-panel,
  .ai-fields {
    display: grid;
  }

  .ai-fields input {
    max-width: none;
  }
}

@media (max-width: 720px) {
  .editor-toolbar,
  .toolbar-actions,
  .section-heading {
    display: grid;
    justify-content: stretch;
  }
}
</style>
