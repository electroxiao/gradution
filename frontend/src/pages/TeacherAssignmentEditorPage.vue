<template>
  <section class="editor-page">
    <header class="editor-toolbar shell-card">
      <div>
        <p class="eyebrow">Assignment Studio</p>
        <h2>{{ isNew ? "新建作业" : "编辑作业" }}</h2>
        <p>AI 默认参与判题，测试用例按题目需要启用。</p>
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

    <section class="assignment-meta shell-card">
      <label class="title-field">
        作业标题
        <input v-model="form.title" placeholder="例如：JDBC 事务与资源释放练习" />
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
        <textarea v-model="form.description" rows="3" placeholder="写给学生的作业说明" />
      </label>
    </section>

    <main class="editor-workbench">
      <aside class="editor-sidebar">
        <section class="side-panel shell-card">
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

        <section class="side-panel shell-card question-index">
          <div class="panel-title">
            <div>
              <h3>题目目录</h3>
              <p>{{ form.questions.length }} 题</p>
            </div>
            <button type="button" class="primary-btn compact-btn" @click="addQuestion">新增题目</button>
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
              <div class="question-badges">
                <span class="badge">{{ reviewLevelText(question.ai_review_level) }}</span>
                <span class="badge subtle">{{ question.enable_testcases ? `${question.test_cases.length} 个用例` : "无测试用例" }}</span>
              </div>
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
        <section class="idea-panel shell-card">
          <div>
            <p class="eyebrow">AI Draft</p>
            <h3>AI 生成题目草稿</h3>
            <p>先生成题面，再按需要生成测试用例和 AI 审查关注点。</p>
          </div>
          <div class="idea-fields">
            <input v-model="generateKnowledge" placeholder="知识点，例如 JDBC transaction" />
            <input v-model="generateRequirement" placeholder="题目要求，例如 设计转账事务并处理异常" />
            <button type="button" class="primary-btn" :disabled="generating || !generateRequirement.trim()" @click="generateQuestion">
              {{ generating ? "生成中..." : "生成题目" }}
            </button>
          </div>
        </section>

        <section v-if="activeQuestion" class="question-editor">
          <header class="question-header shell-card">
            <div>
              <p class="eyebrow">Question {{ activeQuestionIndex + 1 }}</p>
              <h3>{{ activeQuestion.title || "未命名题目" }}</h3>
              <p>先定义题面和 AI 审查策略，再决定是否用测试用例补充功能验证。</p>
            </div>
          </header>

          <section class="content-card shell-card">
            <div class="card-heading">
              <div>
                <h4>题目内容</h4>
                <p>题面越清晰，AI 生成测试用例和关注点越稳定。</p>
              </div>
            </div>
            <div class="card-grid">
              <label>
                题目标题
                <input v-model="activeQuestion.title" placeholder="例如：实现线程安全的库存扣减" />
              </label>
              <label class="prompt-field">
                题目描述
                <textarea
                  v-model="activeQuestion.prompt"
                  class="prompt-input"
                  rows="12"
                  placeholder="题目描述、输入输出要求、实现约束、评分重点"
                />
              </label>
              <label class="prompt-field">
                初始代码
                <textarea
                  v-model="activeQuestion.starter_code"
                  class="prompt-input code-input"
                  rows="11"
                  placeholder="学生首次打开这道题时，编辑器将默认填入这段代码；若学生已存在草稿，则不会覆盖。"
                />
              </label>
            </div>
          </section>

          <section class="grading-card shell-card">
            <div class="card-heading">
              <div>
                <h4>AI 判题设置</h4>
                <p>AI 默认参与判题。普通题建议轻审查，数据库/并发/开放题建议深审查。</p>
              </div>
              <div class="status-chip">AI 默认开启</div>
            </div>

            <div class="review-level-switch">
              <button
                type="button"
                class="level-btn"
                :class="{ active: activeQuestion.ai_review_level === 'light' }"
                @click="activeQuestion.ai_review_level = 'light'"
              >
                轻审查
                <small>只抓明显问题，不额外挑刺</small>
              </button>
              <button
                type="button"
                class="level-btn"
                :class="{ active: activeQuestion.ai_review_level === 'deep' }"
                @click="activeQuestion.ai_review_level = 'deep'"
              >
                深审查
                <small>重点看事务、并发、资源和设计风险</small>
              </button>
            </div>

            <label>
              评分标准
              <textarea
                v-model="activeQuestion.ai_grading_rubric"
                rows="5"
                placeholder="例如：重点检查事务边界、异常处理、资源释放，以及是否满足题目业务约束"
              />
            </label>

            <div class="focus-card">
              <div class="card-heading">
                <div>
                  <h5>AI 关注点</h5>
                  <p>教师可以手动填写，也可以让 AI 根据题目自动补全。</p>
                </div>
                <button
                  type="button"
                  class="secondary-btn"
                  :disabled="focusGenerating || !canGenerateFocus(activeQuestion)"
                  @click="generateFocus(activeQuestion)"
                >
                  {{ focusGenerating ? "生成中..." : "AI 生成关注点" }}
                </button>
              </div>
              <label>
                关注点输入
                <input
                  v-model="activeQuestion.ai_grading_focus_text"
                  placeholder="例如：事务边界, 异常处理, 资源释放"
                />
              </label>
              <p class="helper-text">{{ activeQuestion.focus_summary || "系统会结合题目内容和教师要求，引导 AI 审查代码重点。" }}</p>
            </div>
          </section>

          <section class="testcase-card shell-card">
            <div class="card-heading">
              <div>
                <h4>测试用例</h4>
                <p>用于给 AI 提供功能正确性的显式证据。不开启时，系统会自动加严 AI 审查。</p>
              </div>
              <label class="switch">
                <input v-model="activeQuestion.enable_testcases" type="checkbox" />
                <span>启用测试用例</span>
              </label>
            </div>

            <transition name="fade-slide">
              <div v-if="activeQuestion.enable_testcases" class="testcase-body">
                <div class="card-heading">
                  <div>
                    <h5>用例配置</h5>
                    <p>可手动维护，也可让 AI 基于题面自动生成一版初稿。</p>
                  </div>
                  <div class="inline-actions">
                    <button
                      type="button"
                      class="secondary-btn"
                      :disabled="testcaseGenerating || !canGenerateTestCases(activeQuestion)"
                      @click="generateTestCases(activeQuestion)"
                    >
                      {{ testcaseGenerating ? "生成中..." : "AI 生成测试用例" }}
                    </button>
                    <button type="button" class="primary-btn compact-btn" @click="addTestCase(activeQuestion)">新增用例</button>
                  </div>
                </div>

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
                    <textarea v-model="testCase.input_data" rows="3" placeholder="stdin 输入" />
                    <textarea v-model="testCase.expected_output" rows="3" placeholder="期望 stdout" />
                    <label class="sample-check">
                      <input v-model="testCase.is_sample" type="checkbox" />
                      <span>示例</span>
                    </label>
                    <button type="button" class="ghost-btn" @click="removeTestCase(activeQuestion, cIndex)">删除</button>
                  </article>
                </div>
              </div>
            </transition>
          </section>
        </section>

        <section v-else class="empty-editor shell-card">
          <strong>还没有题目</strong>
          <p>先新增一道题目，或用 AI 生成题目草稿。</p>
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
  generateAssignmentFocusApi,
  generateAssignmentQuestionApi,
  generateAssignmentTestCasesApi,
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
const testcaseGenerating = ref(false);
const focusGenerating = ref(false);
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
    starter_code: question.starter_code || "",
    language: "java",
    enable_testcases: question.enable_testcases !== false,
    ai_review_level: question.ai_review_level || "light",
    ai_grading_rubric: question.ai_grading_rubric || "",
    ai_grading_focus_text: Array.isArray(question.ai_grading_focus) ? question.ai_grading_focus.join(", ") : "",
    focus_summary: question.focus_summary || "",
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
      starter_code: source.starter_code || "",
      enable_testcases: (source.test_cases || []).length > 0,
      ai_review_level: source.ai_review_level || "light",
      ai_grading_focus: source.ai_grading_focus || [],
      test_cases: source.test_cases || [],
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
  successMessage.value = "";
  try {
    const { data } = await generateAssignmentQuestionApi({
      knowledge_point: generateKnowledge.value,
      requirement: generateRequirement.value,
    });
    addQuestion({
      ...data,
      ai_review_level: "light",
    });
    successMessage.value = "题目草稿已追加，请继续完善 AI 判题设置。";
  } catch (error) {
    handleApiError(error, "生成题目失败。");
  } finally {
    generating.value = false;
  }
}

async function generateFocus(question) {
  focusGenerating.value = true;
  errorMessage.value = "";
  try {
    const { data } = await generateAssignmentFocusApi({
      title: question.title,
      prompt: question.prompt,
      ai_grading_rubric: question.ai_grading_rubric,
      ai_review_level: question.ai_review_level,
    });
    question.ai_grading_focus_text = (data.ai_grading_focus || []).join(", ");
    question.focus_summary = data.summary || "";
  } catch (error) {
    handleApiError(error, "生成 AI 关注点失败。");
  } finally {
    focusGenerating.value = false;
  }
}

async function generateTestCases(question) {
  testcaseGenerating.value = true;
  errorMessage.value = "";
  try {
    const { data } = await generateAssignmentTestCasesApi({
      title: question.title,
      prompt: question.prompt,
      knowledge_point: generateKnowledge.value,
    });
    question.test_cases = (data || []).map((item, index) => ({
      id: item.id,
      localKey: item.id || `c-${Date.now()}-${index}-${Math.random()}`,
      input_data: item.input_data || "",
      expected_output: item.expected_output || "",
      is_sample: item.is_sample !== false,
      sort_order: item.sort_order || index,
    }));
    question.enable_testcases = true;
  } catch (error) {
    handleApiError(error, "生成测试用例失败。");
  } finally {
    testcaseGenerating.value = false;
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
      starter_code: question.starter_code || "",
      language: "java",
      enable_testcases: !!question.enable_testcases,
      ai_review_level: question.ai_review_level || "light",
      ai_grading_rubric: question.ai_grading_rubric || "",
      ai_grading_focus: parseFocusText(question.ai_grading_focus_text),
      sort_order: qIndex,
      test_cases: (question.enable_testcases ? question.test_cases : []).map((testCase, cIndex) => ({
        id: testCase.id,
        input_data: testCase.input_data,
        expected_output: testCase.expected_output,
        is_sample: testCase.is_sample,
        sort_order: cIndex,
      })),
    })),
  };
}

function parseFocusText(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function reviewLevelText(value) {
  return value === "deep" ? "深审查" : "轻审查";
}

function canGenerateFocus(question) {
  return Boolean(question?.prompt?.trim());
}

function canGenerateTestCases(question) {
  return Boolean(question?.prompt?.trim());
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
  gap: 16px;
}

.shell-card,
.feedback {
  border: 1px solid #dbe4f0;
  border-radius: 20px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(247, 250, 253, 0.96));
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
}

.editor-toolbar,
.toolbar-actions,
.panel-title,
.card-heading,
.inline-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.editor-toolbar {
  justify-content: space-between;
  padding: 18px 20px;
}

.editor-toolbar h2 {
  margin: 6px 0;
  color: #0f2740;
  font-size: clamp(28px, 3vw, 36px);
}

.editor-toolbar p,
.panel-title p,
.card-heading p,
.helper-text,
.empty-editor p {
  margin: 0;
  color: #66788a;
}

.eyebrow {
  margin: 0;
  color: #1e63a7;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.assignment-meta {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) 180px minmax(360px, 1.3fr);
  gap: 14px;
  padding: 18px 20px;
}

.editor-workbench {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.editor-sidebar,
.editor-main,
.question-editor {
  display: grid;
  gap: 16px;
}

.editor-sidebar {
  position: sticky;
  top: 18px;
}

.side-panel,
.idea-panel,
.question-header,
.content-card,
.grading-card,
.testcase-card,
.empty-editor {
  padding: 18px;
}

.panel-title,
.card-heading {
  justify-content: space-between;
}

.panel-title h3,
.card-heading h4,
.card-heading h5,
.idea-panel h3,
.question-header h3 {
  margin: 0;
  color: #10283d;
}

.student-grid {
  display: grid;
  gap: 8px;
  max-height: 220px;
  overflow: auto;
  padding-top: 12px;
}

.student-check {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(241, 247, 253, 0.95);
}

.question-index {
  gap: 12px;
}

.question-tab {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  padding: 12px;
  border: 1px solid #d9e3ef;
  border-radius: 16px;
  background: #fff;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.question-tab:hover {
  transform: translateY(-1px);
  border-color: #b7d2ec;
  box-shadow: 0 10px 24px rgba(30, 99, 167, 0.09);
}

.question-tab.active {
  border-color: #8cbce7;
  background: linear-gradient(180deg, #f8fbff, #eef6ff);
}

.question-tab-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.question-tab-copy span {
  color: #708294;
  font-size: 12px;
}

.question-tab-copy strong {
  color: #10283d;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.question-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.badge,
.status-chip {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: #eaf4ff;
  color: #1e63a7;
  font-size: 12px;
  font-weight: 700;
}

.badge.subtle {
  background: #eef2f6;
  color: #5f7284;
}

.status-chip {
  background: linear-gradient(135deg, #163552, #1f5f99);
  color: #fff;
}

.question-tab-actions {
  display: flex;
  gap: 4px;
}

.idea-panel {
  display: grid;
  gap: 14px;
}

.idea-fields,
.card-grid,
.review-level-switch {
  display: grid;
  gap: 12px;
}

.idea-fields {
  grid-template-columns: minmax(0, 220px) minmax(0, 1fr) auto;
  align-items: end;
}

.card-grid {
  grid-template-columns: minmax(0, 1fr);
}

.question-header {
  background:
    radial-gradient(circle at top left, rgba(30, 99, 167, 0.12), transparent 45%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(247, 250, 253, 0.96));
}

.review-level-switch {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.level-btn {
  display: grid;
  justify-items: start;
  gap: 6px;
  min-height: 108px;
  padding: 16px;
  border: 1px solid #d8e3ef;
  border-radius: 18px;
  background: #fff;
  color: #163552;
}

.level-btn small {
  color: #66788a;
}

.level-btn.active {
  border-color: #79b0e1;
  background: linear-gradient(180deg, #f6fbff, #ebf5ff);
  box-shadow: inset 0 0 0 1px rgba(121, 176, 225, 0.18);
}

.focus-card,
.testcase-body {
  display: grid;
  gap: 12px;
  padding-top: 4px;
}

.switch {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 999px;
  background: #f3f7fb;
  font-weight: 700;
}

.switch input,
.student-check input,
.sample-check input {
  width: auto;
}

label {
  display: grid;
  gap: 8px;
  color: #34495f;
  font-size: 14px;
}

input,
textarea,
select {
  width: 100%;
  padding: 11px 13px;
  border: 1px solid #d5e1ed;
  border-radius: 14px;
  color: #12263a;
  background: rgba(255, 255, 255, 0.95);
  font: inherit;
}

textarea {
  resize: vertical;
}

.prompt-input,
.case-row textarea {
  font-family: Consolas, "Courier New", monospace;
}

.code-input {
  min-height: clamp(220px, 32vh, 360px);
}

.prompt-input {
  min-height: clamp(260px, 38vh, 460px);
}

.case-table {
  border: 1px solid #dbe4f0;
  border-radius: 18px;
  overflow: hidden;
  background: #fff;
}

.case-head,
.case-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 92px 76px;
  gap: 12px;
  align-items: center;
  padding: 12px;
}

.case-head {
  background: #f5f9fd;
  color: #6a7d90;
  font-size: 13px;
  font-weight: 700;
}

.case-row {
  border-top: 1px solid #edf2f7;
}

.sample-check {
  display: flex;
  align-items: center;
  gap: 6px;
}

button,
.secondary-link,
.primary-btn,
.secondary-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 0 14px;
  border: 1px solid #d5e1ed;
  border-radius: 14px;
  background: #fff;
  color: #18344f;
  cursor: pointer;
  text-decoration: none;
  white-space: nowrap;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

button:hover,
.secondary-link:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.08);
}

.primary-btn {
  background: linear-gradient(135deg, #163552, #1f5f99);
  border-color: #163552;
  color: #fff;
}

.secondary-btn {
  background: #f7fafc;
}

.compact-btn {
  min-height: 38px;
}

.ghost-btn {
  color: #b42318;
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.empty-editor {
  justify-items: start;
  gap: 10px;
}

.empty-editor strong {
  color: #10283d;
  font-size: 22px;
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

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@media (max-width: 1260px) {
  .assignment-meta,
  .editor-workbench,
  .idea-fields,
  .review-level-switch,
  .case-head,
  .case-row {
    grid-template-columns: 1fr;
  }

  .editor-sidebar {
    position: static;
  }
}

@media (max-width: 760px) {
  .editor-toolbar,
  .toolbar-actions,
  .card-heading,
  .panel-title,
  .inline-actions {
    display: grid;
    justify-content: stretch;
  }

  .toolbar-actions > *,
  .inline-actions > *,
  .idea-fields > * {
    width: 100%;
  }
}
</style>
