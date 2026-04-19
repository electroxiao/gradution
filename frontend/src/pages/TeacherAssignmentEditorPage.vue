<template>
  <section class="editor-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Assignment Editor</p>
        <h2>{{ isNew ? "新建作业" : "编辑作业" }}</h2>
        <p>题目使用 Java Main 类，从标准输入读取并输出结果。</p>
      </div>
      <router-link class="secondary-link" to="/teacher/assignments">返回列表</router-link>
    </header>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>
    <p v-if="successMessage" class="feedback success">{{ successMessage }}</p>

    <section class="panel">
      <div class="form-grid">
        <label>
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
      </div>
      <label>
        作业说明
        <textarea v-model="form.description" rows="3" placeholder="写给学生的作业说明" />
      </label>
    </section>

    <section class="panel">
      <div class="section-title">
        <h3>发布学生</h3>
        <span>已选择 {{ form.student_ids.length }} 人</span>
      </div>
      <div class="student-grid">
        <label v-for="student in students" :key="student.id" class="student-check">
          <input v-model="form.student_ids" type="checkbox" :value="student.id" />
          {{ student.username }}
        </label>
      </div>
    </section>

    <section class="panel">
      <div class="section-title">
        <h3>AI 生成题目草稿</h3>
        <button type="button" :disabled="generating || !generateRequirement.trim()" @click="generateQuestion">
          {{ generating ? "生成中..." : "生成并追加" }}
        </button>
      </div>
      <div class="form-grid">
        <input v-model="generateKnowledge" placeholder="知识点，例如 String equals" />
        <input v-model="generateRequirement" placeholder="题目要求，例如 比较 == 和 equals 的区别" />
      </div>
    </section>

    <section class="panel">
      <div class="section-title">
        <h3>题目</h3>
        <button type="button" @click="addQuestion">新增题目</button>
      </div>

      <article v-for="(question, qIndex) in form.questions" :key="question.localKey" class="question-card">
        <div class="question-actions">
          <strong>第 {{ qIndex + 1 }} 题</strong>
          <div>
            <button type="button" :disabled="qIndex === 0" @click="moveQuestion(qIndex, -1)">上移</button>
            <button type="button" :disabled="qIndex === form.questions.length - 1" @click="moveQuestion(qIndex, 1)">下移</button>
            <button type="button" @click="removeQuestion(qIndex)">删除</button>
          </div>
        </div>
        <input v-model="question.title" placeholder="题目标题" />
        <textarea v-model="question.prompt" rows="5" placeholder="题目描述、输入输出要求" />

        <div class="section-title compact">
          <h4>测试用例</h4>
          <button type="button" @click="addTestCase(question)">新增用例</button>
        </div>
        <div v-for="(testCase, cIndex) in question.test_cases" :key="testCase.localKey" class="case-row">
          <label>
            输入
            <textarea v-model="testCase.input_data" rows="2" />
          </label>
          <label>
            期望输出
            <textarea v-model="testCase.expected_output" rows="2" />
          </label>
          <label class="sample-check">
            <input v-model="testCase.is_sample" type="checkbox" />
            示例
          </label>
          <button type="button" @click="removeTestCase(question, cIndex)">删除</button>
        </div>
      </article>
    </section>

    <div class="footer-actions">
      <button type="button" class="primary-btn" :disabled="saving" @click="saveAssignment">
        {{ saving ? "保存中..." : "保存作业" }}
      </button>
    </div>
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
const form = ref({
  title: "",
  description: "",
  status: "draft",
  student_ids: [],
  questions: [],
});

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
    form.value = {
      title: data.title,
      description: data.description || "",
      status: data.status,
      student_ids: data.assigned_students.map((item) => item.id),
      questions: data.questions.map(normalizeQuestion),
    };
  } catch (error) {
    handleApiError(error, "加载作业失败。");
  }
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
}

function removeQuestion(index) {
  form.value.questions.splice(index, 1);
}

function moveQuestion(index, direction) {
  const next = index + direction;
  const [item] = form.value.questions.splice(index, 1);
  form.value.questions.splice(next, 0, item);
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
      router.replace(`/teacher/assignments/${data.id}`);
      successMessage.value = "作业已创建。";
    } else {
      await updateTeacherAssignmentApi(assignmentId.value, {
        title: payload.title,
        description: payload.description,
        status: payload.status,
        student_ids: payload.student_ids,
      });
      await updateTeacherAssignmentQuestionsApi(assignmentId.value, { questions: payload.questions });
      await loadAssignment();
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
.editor-page,
.panel,
.question-card {
  display: grid;
  gap: 16px;
}

.page-header,
.section-title,
.question-actions,
.footer-actions {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.page-header h2 {
  margin: 8px 0 10px;
  font-size: 34px;
}

.page-header p,
.section-title span {
  margin: 0;
  color: #6f8297;
}

.eyebrow {
  color: #5b86b3;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.panel,
.question-card,
.feedback {
  padding: 18px;
  border: 1px solid #e2ebf4;
  border-radius: 8px;
  background: #fff;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

label {
  display: grid;
  gap: 6px;
  color: #34495f;
}

input,
textarea,
select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d7e5f3;
  border-radius: 8px;
  color: #12263a;
}

button,
.secondary-link,
.primary-btn {
  padding: 10px 12px;
  border: 1px solid #d7e5f3;
  border-radius: 8px;
  background: #fff;
  color: #18344f;
  cursor: pointer;
  text-decoration: none;
}

.primary-btn,
.section-title button {
  background: #10283d;
  border-color: #10283d;
  color: #fff;
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.student-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
}

.student-check,
.sample-check {
  display: flex;
  align-items: center;
  gap: 8px;
}

.student-check input,
.sample-check input {
  width: auto;
}

.case-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto auto;
  gap: 10px;
  align-items: end;
}

.compact {
  margin-top: 4px;
}

.compact h4,
.section-title h3 {
  margin: 0;
}

.feedback.error {
  color: #b42318;
  background: #fff8f8;
}

.feedback.success {
  color: #027a48;
  background: #ecfdf3;
}

@media (max-width: 760px) {
  .page-header,
  .section-title,
  .question-actions,
  .case-row {
    grid-template-columns: 1fr;
    display: grid;
  }
}
</style>
