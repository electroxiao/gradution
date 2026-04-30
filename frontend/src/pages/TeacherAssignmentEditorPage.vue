<template>
  <section class="assignment-studio">
    <header class="studio-hero">
      <div>
        <h1>{{ isNew ? "新建作业" : "编辑作业" }} <span v-if="!isNew">/ Assignment Studio</span></h1>
        <p v-if="!isNew">面向高频布置作业：AI 出题、题库复用、题型编辑和班级发布都在一个工作台完成。</p>
      </div>
      <div class="hero-actions">
        <router-link class="btn ghost" to="/teacher/assignments">返回列表</router-link>
        <router-link v-if="!isNew" class="btn ghost" :to="`/teacher/assignments/${assignmentId}/progress`">完成情况</router-link>
        <button type="button" class="btn primary" :disabled="saving" @click="saveAssignment">
          {{ saving ? "保存中..." : "保存作业" }}
        </button>
      </div>
    </header>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>
    <p v-if="successMessage" class="feedback success">{{ successMessage }}</p>

    <section class="meta-panel panel">
      <div class="panel-head compact">
        <h2>作业基本信息</h2>
        <span>{{ selectedClassCount }} 个班级 · {{ assignedStudentCount }} 名学生</span>
      </div>
      <div class="meta-grid">
        <label class="field title-field">
          <span>作业标题</span>
          <input v-model="form.title" placeholder="例如：JDBC 事务与资源释放练习" />
        </label>
        <label class="field class-field">
          <span>班级</span>
          <div class="class-row">
            <label v-for="className in classOptions" :key="className" class="class-check">
              <input v-model="form.class_names" type="checkbox" :value="className" />
              <span>{{ className }}</span>
            </label>
          </div>
        </label>
        <label class="field">
          <span>开始时间</span>
          <input v-model="form.starts_at" type="datetime-local" />
        </label>
        <label class="field">
          <span>截止时间</span>
          <input v-model="form.due_at" type="datetime-local" />
        </label>
      </div>
    </section>

    <section class="core-row">
      <section class="ai-panel panel">
        <div class="panel-head">
          <div>
            <h2>智能出题</h2>
          </div>
        </div>

        <div class="ai-form">
          <label class="field">
            <span>题目要求</span>
            <textarea
              v-model="generateRequirement"
              rows="5"
              placeholder="例如：围绕 Java 事务、异常回滚和资源释放生成一套分层练习。"
            />
          </label>
          <div class="ai-controls">
            <label class="field">
              <span>知识点</span>
              <input v-model="generateKnowledge" placeholder="例如：JDBC 事务" />
            </label>
            <label class="field mini">
              <span>选择题</span>
              <input v-model.number="generateCounts.multiple_choice" min="0" max="20" type="number" />
            </label>
            <label class="field mini">
              <span>填空题</span>
              <input v-model.number="generateCounts.fill_blank" min="0" max="20" type="number" />
            </label>
            <label class="field mini">
              <span>编程题</span>
              <input v-model.number="generateCounts.programming" min="0" max="10" type="number" />
            </label>
            <button type="button" class="btn primary generate-btn" :disabled="generating || !generateRequirement.trim()" @click="generateQuestions">
              {{ generating ? "生成中..." : "生成题目" }}
            </button>
          </div>
        </div>
      </section>
    </section>

    <main class="studio-grid" :class="{ 'preview-open': previewOpen }">
      <aside class="question-rail panel">
        <div class="panel-head">
          <div>
            <h2>题目列表</h2>
            <span>共 {{ form.questions.length }} 题 · 已选择 {{ activeQuestion ? 1 : 0 }} 题</span>
          </div>
        </div>

        <div class="question-tabs" aria-label="题型筛选">
          <button
            v-for="tab in questionFilterTabs"
            :key="tab.value"
            type="button"
            :class="{ active: questionFilter === tab.value }"
            @click="questionFilter = tab.value"
          >
            {{ tab.label }}
          </button>
        </div>

        <VueDraggable
          v-model="form.questions"
          class="question-list"
          handle=".drag-handle"
          ghost-class="question-card-ghost"
          chosen-class="question-card-chosen"
          drag-class="question-card-drag"
          draggable=".question-card"
          :direction="verticalDragDirection"
          :animation="220"
          :fallback-on-body="true"
          :swap-threshold="0.65"
          :disabled="questionFilter !== 'all'"
          @start="startQuestionSort"
          @end="endQuestionSort"
        >
          <article
            v-for="question in form.questions"
            v-show="isQuestionVisible(question)"
            :key="question.localKey"
            class="question-card"
            :class="{
              active: questionIndex(question) === activeQuestionIndex,
              dragging: question.localKey === draggingQuestionKey,
            }"
            @click="selectQuestion(questionIndex(question))"
          >
            <span class="drag-handle" title="拖动排序" role="button" aria-label="拖动排序" @click.stop>
              <span></span>
              <span></span>
              <span></span>
            </span>
            <button type="button" class="question-main">
              <span class="order">{{ questionIndex(question) + 1 }}</span>
              <span class="copy">
                <span class="question-line">
                  <span class="question-title">{{ question.title || "未命名题目" }}</span>
                  <small :class="['type-chip', question.question_type]">{{ questionTypeText(question.question_type) }}</small>
                </span>
                <small :class="['edit-status', hasQuestionContent(question) ? 'done' : 'todo']">
                  {{ hasQuestionContent(question) ? "已编辑" : "未完成" }}
                </small>
              </span>
            </button>
            <div class="mini-actions">
              <button type="button" title="删除" class="danger" @click.stop="removeQuestion(questionIndex(question))">×</button>
            </div>
          </article>
        </VueDraggable>
        <p v-if="!visibleQuestions.length" class="empty-note">当前筛选下暂无题目。</p>

        <div class="rail-actions">
          <button type="button" class="btn dashed" @click="addQuestion({ question_type: 'multiple_choice' })">+ 选择题</button>
          <button type="button" class="btn dashed" @click="addQuestion({ question_type: 'fill_blank' })">+ 填空题</button>
          <button type="button" class="btn dashed" @click="addQuestion({ question_type: 'programming' })">+ 编程题</button>
        </div>
      </aside>

      <section class="studio-main">
        <section v-if="activeQuestion" class="editor-panel panel">
          <div class="editor-head">
            <div>
              <h2>题目编辑</h2>
            </div>
            <div class="editor-tools">
              <button type="button" class="btn primary small" :disabled="saving" @click="saveAssignment">保存</button>
              <button type="button" class="btn danger small" @click="removeQuestion(activeQuestionIndex)">删除</button>
              <button type="button" class="btn ghost small" :class="{ active: previewOpen }" @click="previewOpen = !previewOpen">预览</button>
            </div>
          </div>

          <div class="editor-grid">
            <section class="editor-fields">
              <section class="editor-section">
                <h3>A. 基本信息</h3>
                <div class="basic-grid">
                  <div class="field">
                    <span>题目类型</span>
                    <div class="question-type-tabs" role="tablist" aria-label="题目类型">
                      <button
                        v-for="tab in questionTypeTabs"
                        :key="tab.value"
                        type="button"
                        role="tab"
                        :aria-selected="activeQuestion.question_type === tab.value"
                        :class="{ active: activeQuestion.question_type === tab.value }"
                        @click="setActiveQuestionType(tab.value)"
                      >
                        {{ tab.label }}
                      </button>
                    </div>
                  </div>
                  <label class="field score-field">
                    <span>分值</span>
                    <input value="5" readonly />
                  </label>
                </div>
              </section>

              <section class="editor-section">
                <h3>B. 题干</h3>
                <label class="field">
                  <textarea v-model="activeQuestion.prompt" rows="5" maxlength="1000" placeholder="请输入题干、要求或题目说明" />
                  <small>{{ activeQuestion.prompt.length }}/1000</small>
                </label>
              </section>

              <div v-if="activeQuestion.question_type === 'multiple_choice'" class="editor-section option-editor">
                <div class="sub-head">
                  <h3>C. 选项设置（单选）</h3>
                </div>
                <article v-for="(option, index) in activeQuestion.options" :key="option.localKey" class="option-row">
                  <label>
                    <input v-model="activeQuestion.answer" type="radio" :value="option.key" />
                    <span>{{ option.key }}</span>
                  </label>
                  <input v-model="option.text" placeholder="选项内容" />
                </article>
              </div>

              <section v-if="activeQuestion.question_type === 'fill_blank'" class="editor-section">
                <h3>C. 参考答案</h3>
                <label class="field">
                  <textarea v-model="activeQuestion.answer_text" rows="3" placeholder="可填写一个或多个参考答案，用逗号分隔" />
                </label>
              </section>

              <template v-if="activeQuestion.question_type === 'programming'">
                <section class="editor-section">
                  <h3>C. 初始代码</h3>
                  <label class="field">
                    <textarea v-model="activeQuestion.starter_code" rows="5" class="code-textarea" placeholder="学生打开题目时默认展示的代码" />
                  </label>
                </section>
                <div class="editor-section grading-box">
                  <div class="sub-head">
                    <h3>D. 编程题判题</h3>
                    <button type="button" class="link-btn" :disabled="testcaseGenerating" @click="generateTestCases(activeQuestion)">
                      {{ testcaseGenerating ? "生成中..." : "AI 生成测试用例" }}
                    </button>
                  </div>
                  <select v-model="activeQuestion.grading_mode">
                    <option value="testcase">标准输出判题</option>
                    <option value="observed_ai">观察运行 + AI 判题</option>
                    <option value="ai_review">仅 AI 判题</option>
                  </select>
                  <article v-for="(testCase, index) in activeQuestion.test_cases" :key="testCase.localKey" class="case-row">
                    <textarea v-model="testCase.input_data" rows="2" placeholder="输入" />
                    <textarea v-model="testCase.expected_output" rows="2" placeholder="期望输出" />
                    <label><input v-model="testCase.is_sample" type="checkbox" /> 示例</label>
                    <button type="button" class="icon-danger" @click="removeTestCase(activeQuestion, index)">×</button>
                  </article>
                  <button type="button" class="btn dashed small" @click="addTestCase(activeQuestion)">+ 新增用例</button>
                </div>
              </template>

              <section class="editor-section">
                <h3>{{ activeQuestion.question_type === "programming" ? "E" : "D" }}. 答案解析（可选）</h3>
                <label class="field">
                  <textarea v-model="activeQuestion.explanation" rows="3" maxlength="2000" placeholder="给教师和 AI 判分参考的解析，可留空" />
                  <small>{{ activeQuestion.explanation.length }}/2000</small>
                </label>
              </section>
            </section>
          </div>
        </section>
      </section>

      <aside v-if="activeQuestion && previewOpen" class="live-preview panel">
        <div class="preview-head">
          <h2>实时预览</h2>
          <label class="student-switch">
            <span>学生视角</span>
            <input checked type="checkbox" />
          </label>
        </div>
        <div class="preview-card">
          <div class="preview-title">
            <span>{{ activeQuestionIndex + 1 }}</span>
            <strong>{{ activeQuestion.title || "未命名题目" }}</strong>
          </div>
          <p>{{ activeQuestion.prompt || "题干将在这里预览。" }}</p>
          <div v-if="activeQuestion.question_type === 'multiple_choice'" class="preview-options">
            <div v-for="option in activeQuestion.options" :key="`p-${option.localKey}`">
              <span>{{ option.key }}</span>
              <p>{{ option.text || "选项内容" }}</p>
            </div>
          </div>
          <div v-if="activeQuestion.question_type === 'fill_blank'" class="blank-preview">学生将在这里填写答案</div>
          <pre v-if="activeQuestion.question_type === 'programming'" class="code-preview">{{ activeQuestion.starter_code || "public class Main {\\n    public static void main(String[] args) {\\n    }\\n}" }}</pre>
        </div>
        <p class="preview-note">ⓘ 预览仅供展示，实际样式以学生端为准</p>
      </aside>
    </main>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { VueDraggable } from "vue-draggable-plus";

import {
  createTeacherAssignmentApi,
  createTeacherQuestionBankItemApi,
  generateAssignmentQuestionsApi,
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
const activeQuestionIndex = ref(0);
const draggingQuestionKey = ref(null);
const questionFilter = ref("all");
const previewOpen = ref(false);
const generateRequirement = ref("");
const generateKnowledge = ref("");
const generateCounts = ref({ multiple_choice: 5, fill_blank: 3, programming: 1 });
const form = ref({
  title: "",
  status: "published",
  starts_at: "",
  due_at: "",
  class_names: [],
  questions: [],
});

const classOptions = computed(() => {
  const classes = [...new Set(students.value.map((student) => student.class_name).filter(Boolean))];
  return classes.length ? classes : ["软件1班", "软件2班"];
});
const selectedClassCount = computed(() => form.value.class_names.length);
const assignedStudentCount = computed(() =>
  students.value.filter((student) => form.value.class_names.includes(student.class_name)).length,
);
const activeQuestion = computed(() => form.value.questions[activeQuestionIndex.value] || null);
const questionFilterTabs = [
  { value: "all", label: "全部" },
  { value: "multiple_choice", label: "选择题" },
  { value: "fill_blank", label: "填空题" },
  { value: "programming", label: "编程题" },
];
const questionTypeTabs = questionFilterTabs.slice(1);
const verticalDragDirection = () => "vertical";
const visibleQuestions = computed(() =>
  form.value.questions
    .map((question, index) => ({ question, index }))
    .filter(({ question }) => questionFilter.value === "all" || question.question_type === questionFilter.value),
);

onMounted(async () => {
  await loadStudents();
  if (!isNew.value) {
    await loadAssignment();
  } else {
    form.value.class_names = classOptions.value.slice(0, 1);
    addQuestion({ question_type: "multiple_choice" });
  }
});

watch(() => activeQuestion.value?.question_type, () => {
  if (activeQuestion.value) normalizeQuestionByType(activeQuestion.value);
});

async function loadStudents() {
  try {
    const { data } = await listTeacherStudentsApi();
    students.value = data || [];
  } catch (error) {
    handleApiError(error, "加载学生失败。");
  }
}

async function loadAssignment() {
  try {
    const { data } = await getTeacherAssignmentApi(assignmentId.value);
    form.value = {
      title: data.title || "",
      status: data.status || "published",
      starts_at: toDatetimeLocal(data.starts_at),
      due_at: toDatetimeLocal(data.due_at),
      class_names: data.class_names || [],
      questions: (data.questions || []).map(normalizeQuestion),
    };
    activeQuestionIndex.value = 0;
  } catch (error) {
    handleApiError(error, "加载作业失败。");
  }
}

function normalizeQuestion(question = {}) {
  const questionType = normalizeQuestionType(question.question_type);
  const normalized = {
    id: question.id,
    localKey: question.id || `q-${Date.now()}-${Math.random()}`,
    title: question.title || "",
    prompt: question.prompt || "",
    question_type: questionType,
    options: normalizeOptions(question.options),
    answer: normalizeAnswer(question.answer, questionType),
    answer_text: Array.isArray(question.answer) ? question.answer.join(", ") : String(question.answer || ""),
    explanation: question.explanation || "",
    starter_code: question.starter_code || "",
    knowledge_node_ids: Array.isArray(question.knowledge_node_ids) ? question.knowledge_node_ids.map(Number) : [],
    language: "java",
    grading_mode: question.grading_mode || "testcase",
    ai_review_level: question.ai_review_level || "light",
    ai_grading_rubric: question.ai_grading_rubric || "",
    ai_grading_focus: question.ai_grading_focus || [],
    sort_order: question.sort_order || 0,
    test_cases: (question.test_cases || []).map((item, index) => ({
      id: item.id,
      localKey: item.id || `c-${Date.now()}-${index}-${Math.random()}`,
      input_data: item.input_data || "",
      expected_output: item.expected_output || "",
      is_sample: item.is_sample !== false,
      sort_order: item.sort_order || index,
    })),
  };
  normalizeQuestionByType(normalized);
  return normalized;
}

function normalizeQuestionByType(question) {
  if (question.question_type === "multiple_choice" && !question.options.length) {
    question.options = ["A", "B", "C", "D"].map((key) => ({ key, text: "", localKey: `o-${key}-${Date.now()}` }));
    question.answer = "A";
  }
  if (question.question_type === "fill_blank") {
    question.options = [];
    question.grading_mode = "ai_review";
  }
  if (question.question_type === "programming") {
    question.answer = null;
    question.answer_text = "";
    if (!question.test_cases.length) addTestCase(question);
  }
}

function normalizeActiveQuestionByType() {
  if (activeQuestion.value) normalizeQuestionByType(activeQuestion.value);
}

function setActiveQuestionType(questionType) {
  if (!activeQuestion.value || activeQuestion.value.question_type === questionType) return;
  activeQuestion.value.question_type = questionType;
  normalizeActiveQuestionByType();
}

function normalizeOptions(options = []) {
  if (!Array.isArray(options) || !options.length) return [];
  return options.map((item, index) => ({
    key: item.key || String.fromCharCode(65 + index),
    text: item.text || "",
    localKey: item.localKey || `o-${Date.now()}-${index}-${Math.random()}`,
  }));
}

function normalizeQuestionType(value) {
  return ["multiple_choice", "fill_blank", "programming"].includes(value) ? value : "programming";
}

function normalizeAnswer(answer, questionType) {
  if (questionType === "multiple_choice") return Array.isArray(answer) ? answer[0] : (answer || "A");
  if (questionType === "fill_blank") return Array.isArray(answer) ? answer : (answer || "");
  return null;
}

function selectQuestion(index) {
  activeQuestionIndex.value = index;
}

function hasQuestionContent(question) {
  return Boolean(question.title?.trim() && question.prompt?.trim());
}

function addQuestion(source = {}) {
  form.value.questions.push(normalizeQuestion({
    title: source.title || "",
    prompt: source.prompt || "",
    question_type: source.question_type || "multiple_choice",
    options: source.options || [],
    answer: source.answer,
    explanation: source.explanation || "",
    starter_code: source.starter_code || "",
    knowledge_node_ids: source.knowledge_node_ids || [],
    grading_mode: source.grading_mode || "testcase",
    test_cases: source.test_cases || [],
  }));
  activeQuestionIndex.value = form.value.questions.length - 1;
}

function removeQuestion(index) {
  form.value.questions.splice(index, 1);
  activeQuestionIndex.value = Math.min(activeQuestionIndex.value, Math.max(form.value.questions.length - 1, 0));
}

function duplicateQuestion(index) {
  const source = form.value.questions[index];
  if (!source) return;
  const clone = normalizeQuestion({
    ...source,
    id: undefined,
    localKey: undefined,
    title: source.title ? `${source.title} 副本` : "",
    options: source.options.map(({ key, text }) => ({ key, text })),
    test_cases: source.test_cases.map(({ input_data, expected_output, is_sample, sort_order }) => ({
      input_data,
      expected_output,
      is_sample,
      sort_order,
    })),
  });
  form.value.questions.splice(index + 1, 0, clone);
  activeQuestionIndex.value = index + 1;
}

function startQuestionSort(event) {
  draggingQuestionKey.value = form.value.questions[event.oldIndex]?.localKey || null;
}

function endQuestionSort() {
  const activeKey = activeQuestion.value?.localKey;
  draggingQuestionKey.value = null;
  restoreActiveQuestion(activeKey);
}

function restoreActiveQuestion(activeKey) {
  if (!activeKey) return;
  const nextIndex = form.value.questions.findIndex((question) => question.localKey === activeKey);
  if (nextIndex >= 0) activeQuestionIndex.value = nextIndex;
}

function questionIndex(question) {
  return form.value.questions.findIndex((item) => item.localKey === question.localKey);
}

function isQuestionVisible(question) {
  return questionFilter.value === "all" || question.question_type === questionFilter.value;
}

function addOption(question) {
  const key = String.fromCharCode(65 + question.options.length);
  question.options.push({ key, text: "", localKey: `o-${Date.now()}-${Math.random()}` });
  if (!question.answer) question.answer = key;
}

function removeOption(question, index) {
  const [removed] = question.options.splice(index, 1);
  if (removed?.key === question.answer) question.answer = question.options[0]?.key || "";
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

async function generateQuestions() {
  generating.value = true;
  errorMessage.value = "";
  successMessage.value = "";
  try {
    const { data } = await generateAssignmentQuestionsApi({
      requirement: generateRequirement.value,
      knowledge_point: generateKnowledge.value,
      programming_count: Number(generateCounts.value.programming || 0),
      multiple_choice_count: Number(generateCounts.value.multiple_choice || 0),
      fill_blank_count: Number(generateCounts.value.fill_blank || 0),
    });
    const generated = Array.isArray(data.questions) && data.questions.length ? data.questions : [data];
    generated.forEach((item) => addQuestion(item));
    successMessage.value = `已追加 ${generated.length} 道题目。`;
  } catch (error) {
    handleApiError(error, "生成题目失败。");
  } finally {
    generating.value = false;
  }
}

async function generateTestCases(question) {
  if (!question.prompt.trim()) return;
  testcaseGenerating.value = true;
  try {
    const { data } = await generateAssignmentTestCasesApi({
      title: question.title,
      prompt: question.prompt,
      knowledge_point: generateKnowledge.value,
    });
    question.test_cases = (data || []).map((item, index) => ({
      localKey: `c-${Date.now()}-${index}-${Math.random()}`,
      input_data: item.input_data || "",
      expected_output: item.expected_output || "",
      is_sample: item.is_sample !== false,
      sort_order: index,
    }));
  } catch (error) {
    handleApiError(error, "生成测试用例失败。");
  } finally {
    testcaseGenerating.value = false;
  }
}

async function saveActiveQuestionToBank() {
  if (!activeQuestion.value) return;
  try {
    await createTeacherQuestionBankItemApi(toQuestionPayload(activeQuestion.value, 0));
    successMessage.value = "当前题目已保存到题库。";
  } catch (error) {
    handleApiError(error, "保存题库失败。");
  }
}

async function saveAssignment() {
  saving.value = true;
  errorMessage.value = "";
  successMessage.value = "";
  try {
    const validation = validateForm();
    if (validation) {
      errorMessage.value = validation;
      return;
    }
    const payload = buildPayload();
    if (isNew.value) {
      const { data } = await createTeacherAssignmentApi(payload);
      applySavedAssignment(data);
      router.replace(`/teacher/assignments/${data.id}`);
      successMessage.value = "作业已创建，题目已同步到题库。";
    } else {
      await updateTeacherAssignmentApi(assignmentId.value, {
        title: payload.title,
        description: "",
        status: payload.status,
        starts_at: payload.starts_at,
        due_at: payload.due_at,
        class_names: payload.class_names,
      });
      const { data } = await updateTeacherAssignmentQuestionsApi(assignmentId.value, { questions: payload.questions });
      applySavedAssignment(data);
      successMessage.value = "作业已保存，题目已同步到题库。";
    }
  } catch (error) {
    handleApiError(error, "保存作业失败。");
  } finally {
    saving.value = false;
  }
}

function applySavedAssignment(data) {
  form.value = {
    title: data.title || "",
    status: data.status || "published",
    starts_at: toDatetimeLocal(data.starts_at),
    due_at: toDatetimeLocal(data.due_at),
    class_names: data.class_names || form.value.class_names,
    questions: (data.questions || []).map(normalizeQuestion),
  };
}

function validateForm() {
  if (!form.value.title.trim()) return "请填写作业标题。";
  if (!form.value.class_names.length) return "请选择发布班级。";
  if (!form.value.questions.length) return "请至少添加一道题目。";
  const invalidIndex = form.value.questions.findIndex((question) => !question.prompt.trim());
  if (invalidIndex >= 0) {
    activeQuestionIndex.value = invalidIndex;
    return `请填写第 ${invalidIndex + 1} 题的题目内容。`;
  }
  return "";
}

function buildPayload() {
  return {
    title: form.value.title.trim(),
    description: "",
    status: form.value.status || "published",
    starts_at: fromDatetimeLocal(form.value.starts_at),
    due_at: fromDatetimeLocal(form.value.due_at),
    class_names: form.value.class_names,
    questions: form.value.questions.map(toQuestionPayload),
  };
}

function toQuestionPayload(question, index = 0) {
  const questionType = normalizeQuestionType(question.question_type);
  const answer = questionType === "fill_blank"
    ? String(question.answer_text || "").split(/[,，\n]/).map((item) => item.trim()).filter(Boolean)
    : question.answer;
  return {
    id: question.id,
    title: question.title || questionTypeText(questionType),
    prompt: question.prompt,
    question_type: questionType,
    options: questionType === "multiple_choice" ? question.options.map(({ key, text }) => ({ key, text })) : [],
    answer,
    explanation: question.explanation || "",
    starter_code: questionType === "programming" ? question.starter_code || "" : "",
    knowledge_node_ids: question.knowledge_node_ids || [],
    language: "java",
    grading_mode: questionType === "programming" ? question.grading_mode || "testcase" : "ai_review",
    enable_testcases: questionType === "programming" && question.grading_mode !== "ai_review",
    ai_review_level: questionType === "programming" && question.grading_mode === "testcase" ? "light" : "deep",
    ai_grading_rubric: question.ai_grading_rubric || "",
    ai_grading_focus: question.ai_grading_focus || [],
    sort_order: index,
    test_cases: questionType === "programming" ? question.test_cases.map((item, caseIndex) => ({
      id: item.id,
      input_data: item.input_data || "",
      expected_output: item.expected_output || "",
      is_sample: item.is_sample !== false,
      sort_order: caseIndex,
    })) : [],
  };
}

function questionTypeText(value) {
  return { multiple_choice: "选择题", fill_blank: "填空题", programming: "编程题" }[value] || "编程题";
}

function toDatetimeLocal(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60000).toISOString().slice(0, 16);
}

function fromDatetimeLocal(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
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
.assignment-studio {
  --studio-card-height: min(760px, calc(100vh - 24px));
  display: grid;
  gap: 12px;
  color: #162033;
  font-size: var(--compact-body);
  max-width: 100%;
  overflow-x: hidden;
}

.studio-hero,
.panel,
.feedback {
  border: 1px solid #e3e8f1;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 10px 28px rgba(23, 37, 60, 0.06);
}

.studio-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 18px 20px;
}

.studio-hero h1 {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 400;
  letter-spacing: 0;
}

.studio-hero h1 span {
  color: #66738a;
  font-weight: 400;
}

.studio-hero p,
.panel-head span,
.empty-note {
  margin: 0;
  color: #6d7890;
}

.hero-actions,
.editor-tools,
.ai-controls,
.mini-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.hero-actions {
  flex-shrink: 0;
}

.btn {
  box-sizing: border-box;
  min-height: 36px;
  border: 1px solid #d8e1f0;
  border-radius: 7px;
  background: #fff;
  color: #20304d;
  padding: 8px 14px;
  font-weight: 400;
  text-decoration: none;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.16s ease, border-color 0.16s ease, color 0.16s ease, transform 0.16s ease;
}

.btn.primary {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}

.btn.danger {
  border-color: #ffe0e0;
  background: #fff;
  color: #dc2626;
}

.btn.ghost {
  background: #f8fafc;
}

.btn.ghost.active {
  border-color: #2563eb;
  background: #eef5ff;
  color: #1d4ed8;
}

.btn.dashed {
  border-style: dashed;
  color: #2563eb;
}

.btn.small {
  min-height: 30px;
  padding: 5px 10px;
  font-size: 12px;
}

.btn:disabled,
.mini-actions button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.feedback {
  padding: 10px 12px;
}

.feedback.error {
  border-color: #fecaca;
  color: #b42318;
  background: #fff7f7;
}

.feedback.success {
  border-color: #bbf7d0;
  color: #166534;
  background: #f4fff7;
}

.studio-grid {
  display: grid;
  grid-template-columns: minmax(260px, 330px) minmax(0, 1fr);
  gap: 14px;
  align-items: stretch;
  max-width: 100%;
  min-width: 0;
}

.studio-grid.preview-open {
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr) minmax(300px, 360px);
}

.question-rail {
  position: sticky;
  top: 12px;
  display: grid;
  gap: 14px;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  align-self: stretch;
  height: 0;
  min-height: 100%;
  max-height: 100%;
  min-width: 0;
  overflow: hidden;
  padding: 18px;
}

.panel-head,
.editor-head,
.sub-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.panel-head.compact,
.sub-head {
  align-items: center;
}

.panel-head h2,
.editor-head h2 {
  margin: 0 0 4px;
  font-size: 16px;
  font-weight: 400;
  letter-spacing: 0;
}

.question-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  overflow: auto;
  padding-right: 2px;
}

.question-tabs {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.question-tabs button {
  min-height: 36px;
  border: 1px solid #e0e8f4;
  border-radius: 7px;
  background: #fff;
  color: #33415a;
  cursor: pointer;
  font-weight: 400;
}

.question-tabs button.active {
  border-color: #b9d0ff;
  background: #eef5ff;
  color: #1d63f0;
}

.question-card {
  flex: 0 0 auto;
  display: grid;
  grid-template-columns: 12px minmax(0, 1fr) 28px;
  gap: 10px;
  align-items: center;
  border: 1px solid #e4eaf3;
  border-radius: 8px;
  background: #fff;
  min-height: 70px;
  padding: 9px 10px;
  transition: border-color 0.16s ease, background 0.16s ease, box-shadow 0.16s ease, opacity 0.16s ease, transform 0.18s ease;
  user-select: none;
}

.question-card.active {
  border-color: #2563eb;
  background: #fbfdff;
  box-shadow: 0 10px 22px rgba(37, 99, 235, 0.08);
}

.question-card.dragging {
  opacity: 0.58;
}

.question-card-chosen {
  border-color: #9fb8ef;
}

.question-card-ghost {
  border-color: #b9c9e2;
  background: #f8fafc;
  opacity: 0.72;
}

.question-card-drag {
  box-shadow: 0 14px 28px rgba(31, 41, 55, 0.16);
  opacity: 0.95;
  transform: scale(1.02);
  z-index: 5;
}

.drag-handle {
  position: relative;
  display: grid;
  gap: 4px;
  place-items: center;
  width: 12px;
  height: 36px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  cursor: grab;
  touch-action: none;
}

.drag-handle::before {
  content: "";
  position: absolute;
  inset: -6px;
}

.drag-handle:active {
  cursor: grabbing;
}

.drag-handle span {
  width: 12px;
  height: 2px;
  border-radius: 999px;
  background: #9aa7ba;
}

.question-main {
  display: flex;
  width: 100%;
  gap: 10px;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.order {
  display: grid;
  width: 24px;
  height: 24px;
  place-items: center;
  border-radius: 7px;
  background: #eff4ff;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 400;
}

.copy {
  display: grid;
  min-width: 0;
  gap: 10px;
}

.question-line {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.question-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.question-title {
  color: #1f2937;
  font-weight: 400;
}

.edit-status {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #64748b;
  font-size: 12px;
  font-weight: 400;
}

.edit-status::before {
  content: "";
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid currentColor;
}

.edit-status.done {
  color: #0f9f62;
}

.edit-status.done::before {
  border: 0;
  background: #0f9f62;
  box-shadow: inset 0 0 0 3px #fff;
}

.edit-status.todo {
  color: #f59e0b;
}

.mini-actions {
  justify-content: center;
}

.mini-actions button,
.icon-danger {
  width: 26px;
  height: 26px;
  border: 1px solid #d9e3f2;
  border-radius: 6px;
  background: #fff;
  color: #51617c;
  cursor: pointer;
  line-height: 1;
}

.mini-actions .danger,
.icon-danger {
  color: #dc2626;
}

.rail-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.studio-main {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.editor-tools {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.editor-tools .btn {
  min-width: 72px;
}

.meta-panel,
.ai-panel,
.editor-panel,
.live-preview {
  padding: 16px;
  min-width: 0;
}

.editor-panel {
  height: auto;
  overflow: visible;
}

.live-preview {
  align-self: stretch;
  height: 0;
  min-height: 100%;
  max-height: 100%;
  overflow: auto;
}

.meta-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(220px, 0.82fr) minmax(220px, 0.82fr);
  gap: 12px;
}

.title-field {
  grid-column: 1 / -1;
}

.field {
  display: grid;
  gap: 8px;
  color: #3c4960;
  font-weight: 400;
}

.field > span {
  font-size: 12px;
}

.meta-panel .field > span {
  font-size: 13px;
  color: #a2adbf;
  font-weight: 400;
}

input,
textarea,
select {
  box-sizing: border-box;
  width: 100%;
  min-width: 0;
  border: 1px solid #d9e3f2;
  border-radius: 7px;
  background: #fff;
  color: #17233b;
  padding: 9px 10px;
  font: inherit;
  letter-spacing: 0;
}

textarea {
  resize: none;
}

.class-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 0;
}

.class-field {
  min-width: 0;
}

.class-check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  border: 1px solid #d9e3f2;
  border-radius: 7px;
  background: #fff;
  padding: 0 12px;
  color: #a2adbf;
  font-weight: 400;
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.02);
}

.class-check input {
  width: 16px;
  height: 16px;
  margin: 0;
  accent-color: #2f6ef4;
}

.class-check span {
  font-size: 13px;
  color: #a2adbf;
  font-weight: 400;
}

.core-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 14px;
}

.core-row > *,
.panel-head > div {
  min-width: 0;
}

.ai-form {
  display: grid;
  gap: 12px;
  margin-top: 12px;
}

.ai-controls {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  align-items: end;
}

.ai-controls > .field:first-child {
  grid-column: 1 / -1;
}

.field.mini input {
  text-align: center;
}

.generate-btn {
  align-self: end;
  width: 100%;
}

.link-btn {
  border: 0;
  background: transparent;
  color: #2563eb;
  font-weight: 400;
  cursor: pointer;
}

.type-chip {
  display: inline-flex;
  width: fit-content;
  border-radius: 6px;
  padding: 3px 7px;
  background: #edf4ff;
  color: #2563eb;
  font-size: 12px;
  font-weight: 400;
}

.type-chip.fill_blank {
  background: #ecfdf5;
  color: #047857;
}

.type-chip.programming {
  background: #fff7ed;
  color: #c2410c;
}

.editor-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 14px;
  margin-top: 14px;
}

.editor-fields {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.editor-section {
  display: grid;
  gap: 10px;
  border-bottom: 1px solid #e8eef6;
  padding-bottom: 16px;
  min-width: 0;
}

.editor-section:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

.editor-section h3,
.sub-head h3 {
  margin: 0;
  color: #15223a;
  font-size: 15px;
  font-weight: 400;
}

.editor-section small {
  justify-self: end;
  color: #8b99ad;
  font-size: 12px;
}

.basic-grid {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 100px;
  gap: 14px;
}

.question-type-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.question-type-tabs button {
  min-height: 38px;
  border: 1px solid #d9e3f2;
  border-radius: 7px;
  background: #fff;
  color: #33415a;
  cursor: pointer;
  font: inherit;
  font-weight: 400;
}

.question-type-tabs button.active {
  border-color: #b9d0ff;
  background: #eef5ff;
  color: #1d63f0;
}

.score-field {
  position: relative;
}

.score-field::after {
  content: "分";
  position: absolute;
  right: 12px;
  bottom: 11px;
  color: #8b99ad;
}

.score-field input {
  padding-right: 34px;
}

.option-editor,
.grading-box {
  display: grid;
  gap: 10px;
  border-bottom: 1px solid #e8eef6;
  background: #fff;
  padding: 0 0 16px;
}

.option-row,
.case-row {
  display: grid;
  grid-template-columns: 76px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
}

.option-row label,
.case-row label {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  font-weight: 400;
}

.option-row input[type="radio"],
.case-row input[type="checkbox"] {
  width: auto;
  accent-color: #2f6ef4;
}

.option-row label span {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: 50%;
  background: #eef4ff;
  color: #2563eb;
  font-weight: 400;
}

.case-row {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 70px 28px;
}

.code-textarea,
.code-preview {
  font-family: Consolas, "Courier New", monospace;
}

.live-preview {
  position: sticky;
  top: 12px;
  display: grid;
  gap: 18px;
  grid-template-rows: auto minmax(0, 1fr) auto;
}

.preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.preview-head h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 400;
}

.student-switch {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #64748b;
  font-size: 12px;
  font-weight: 400;
}

.student-switch input {
  width: 36px;
  height: 20px;
  padding: 0;
  accent-color: #2563eb;
}

.preview-card {
  display: grid;
  align-content: start;
  gap: 18px;
  min-height: 0;
  border: 1px solid #dfe8f5;
  border-radius: 8px;
  background: #fff;
  overflow: auto;
  padding: 28px 22px;
}

.preview-title {
  display: flex;
  align-items: center;
  gap: 14px;
}

.preview-title span {
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  border-radius: 50%;
  background: #eef4ff;
  color: #2563eb;
  font-size: 18px;
  font-weight: 400;
}

.preview-title strong {
  min-width: 0;
  color: #0f172a;
  font-size: 20px;
  font-weight: 400;
}

.preview-card > p {
  margin: 0;
  white-space: pre-wrap;
  color: #31405a;
  line-height: 1.65;
}

.preview-options {
  display: grid;
  gap: 8px;
}

.preview-options div {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  border: 1px solid #e4edf8;
  border-radius: 7px;
  min-height: 72px;
  padding: 13px;
}

.preview-options span {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 50%;
  background: #eef4ff;
  color: #2563eb;
  font-weight: 400;
}

.preview-options p {
  margin: 7px 0 0;
  color: #334155;
}

.blank-preview {
  border: 1px dashed #bfd0e7;
  border-radius: 7px;
  padding: 12px;
  color: #7a879d;
}

.code-preview {
  overflow: auto;
  border-radius: 7px;
  background: #182238;
  color: #e8eef8;
  padding: 12px;
  white-space: pre;
}

.preview-note {
  margin: 0;
  color: #94a3b8;
  font-size: 12px;
}

@media (max-width: 1440px) {
  .studio-grid {
    grid-template-columns: minmax(240px, 300px) minmax(0, 1fr);
  }

  .studio-grid.preview-open {
    grid-template-columns: minmax(210px, 260px) minmax(0, 1fr) minmax(280px, 320px);
  }

  .ai-controls {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .generate-btn {
    grid-column: 1 / -1;
  }
}

@media (max-width: 1180px) {
  .studio-grid {
    grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  }

  .studio-grid.preview-open {
    grid-template-columns: minmax(190px, 230px) minmax(0, 1fr) minmax(260px, 300px);
  }

  .question-tabs,
  .rail-actions {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 900px) {
  .assignment-studio {
    --studio-card-height: 640px;
  }

  .studio-grid,
  .studio-grid.preview-open,
  .editor-grid {
    grid-template-columns: 1fr;
  }

  .question-rail,
  .live-preview {
    position: static;
  }

  .question-rail {
    height: var(--studio-card-height);
    min-height: 0;
    max-height: none;
  }

  .meta-grid,
  .ai-controls {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 720px) {
  .studio-hero,
  .panel-head,
  .editor-head {
    flex-direction: column;
  }

  .hero-actions,
  .editor-tools,
  .basic-grid,
  .meta-grid,
  .ai-controls {
    display: grid;
    grid-template-columns: 1fr;
    width: 100%;
  }

  .question-tabs,
  .rail-actions {
    grid-template-columns: 1fr 1fr;
  }

  .case-row,
  .option-row {
    grid-template-columns: 1fr;
  }
}
</style>
