<template>
  <section class="assignment-studio">
    <header class="studio-hero">
      <div>
        <h1>{{ isNew ? "新建作业" : "编辑作业" }} <span>/ Assignment Studio</span></h1>
        <p>面向高频布置作业：AI 出题、题库复用、题型编辑和班级发布都在一个工作台完成。</p>
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

    <main class="studio-grid">
      <aside class="question-rail panel">
        <div class="panel-head">
          <div>
            <h2>当前作业题目</h2>
            <span>共 {{ form.questions.length }} 题</span>
          </div>
        </div>

        <div class="question-list">
          <article
            v-for="(question, index) in form.questions"
            :key="question.localKey"
            class="question-card"
            :class="{
              active: index === activeQuestionIndex,
              dragging: index === draggingQuestionIndex,
              'drag-over': index === dragOverQuestionIndex && index !== draggingQuestionIndex,
            }"
            @dragover.prevent
            @dragenter.prevent="dragEnterQuestion(index)"
            @drop.prevent="dropQuestion(index)"
            @click="selectQuestion(index)"
          >
            <button
              type="button"
              class="drag-handle"
              title="拖动排序"
              draggable="true"
              @dragstart.stop="startQuestionDrag(index, $event)"
              @dragend="endQuestionDrag"
              @click.stop
            >
              <span></span>
              <span></span>
              <span></span>
            </button>
            <button type="button" class="question-main">
              <span class="order">{{ index + 1 }}</span>
              <span class="copy">
                <span class="question-title">{{ question.title || "未命名题目" }}</span>
                <small :class="['type-chip', question.question_type]">{{ questionTypeText(question.question_type) }}</small>
              </span>
            </button>
            <div class="mini-actions">
              <button type="button" title="删除" class="danger" @click.stop="removeQuestion(index)">×</button>
            </div>
          </article>
        </div>

        <div class="rail-actions">
          <button type="button" class="btn dashed" @click="addQuestion({ question_type: 'multiple_choice' })">+ 选择题</button>
          <button type="button" class="btn dashed" @click="addQuestion({ question_type: 'fill_blank' })">+ 填空题</button>
          <button type="button" class="btn dashed" @click="addQuestion({ question_type: 'programming' })">+ 编程题</button>
        </div>
      </aside>

      <section class="studio-main">
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
            <label class="field">
              <span>开始时间</span>
              <input v-model="form.starts_at" type="datetime-local" />
            </label>
            <label class="field">
              <span>截止时间</span>
              <input v-model="form.due_at" type="datetime-local" />
            </label>
          </div>
          <div class="class-row">
            <label v-for="className in classOptions" :key="className" class="class-check">
              <input v-model="form.class_names" type="checkbox" :value="className" />
              <span>{{ className }}</span>
            </label>
          </div>
        </section>

        <section class="core-row">
          <section class="ai-panel panel">
            <div class="panel-head">
              <div>
                <h2>智能出题与题库复用</h2>
                <span>AI 会按题型数量生成题目，可直接追加到当前作业并自动入库。</span>
              </div>
              <div class="mode-tabs">
                <button type="button" :class="{ active: coreMode === 'ai' }" @click="coreMode = 'ai'">AI 生成题目</button>
                <button type="button" :class="{ active: coreMode === 'bank' }" @click="coreMode = 'bank'">复用题库</button>
              </div>
            </div>

            <div v-if="coreMode === 'ai'" class="ai-form">
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

            <div v-else class="bank-inline">
              <div class="bank-filters">
                <input v-model="bankFilters.keyword" placeholder="搜索题目标题 / 题干 / 知识点" @keydown.enter.prevent="loadQuestionBank" />
                <select v-model="bankFilters.question_type">
                  <option value="">全部题型</option>
                  <option value="multiple_choice">选择题</option>
                  <option value="fill_blank">填空题</option>
                  <option value="programming">编程题</option>
                </select>
                <select v-model="bankFilters.difficulty">
                  <option value="">全部难度</option>
                  <option value="easy">简单</option>
                  <option value="medium">中等</option>
                  <option value="hard">困难</option>
                </select>
                <button type="button" class="btn ghost" :disabled="bankLoading" @click="loadQuestionBank">
                  {{ bankLoading ? "搜索中..." : "搜索" }}
                </button>
              </div>
              <div class="bank-list">
                <article v-for="item in questionBank" :key="item.id" class="bank-item">
                  <div>
                    <strong>{{ item.title }}</strong>
                    <p>{{ item.prompt }}</p>
                    <span :class="['type-chip', item.question_type]">{{ questionTypeText(item.question_type) }}</span>
                  </div>
                  <button type="button" class="btn primary small" @click="reuseBankQuestion(item)">加入作业</button>
                </article>
                <p v-if="!questionBank.length && !bankLoading" class="empty-note">暂无可复用题目，保存作业后会自动沉淀到题库。</p>
              </div>
            </div>
          </section>

          <aside class="bank-panel panel">
            <div class="panel-head compact">
              <h2>复用题库</h2>
              <button type="button" class="link-btn" @click="loadQuestionBank">刷新</button>
            </div>
            <div class="compact-bank-list">
              <button
                v-for="item in questionBank.slice(0, 5)"
                :key="`compact-${item.id}`"
                type="button"
                class="compact-bank-item"
                @click="reuseBankQuestion(item)"
              >
                <span>{{ item.title }}</span>
                <small>{{ questionTypeText(item.question_type) }}</small>
              </button>
              <p v-if="!questionBank.length" class="empty-note">题库为空</p>
            </div>
          </aside>
        </section>

        <section v-if="activeQuestion" class="editor-panel panel">
          <div class="editor-head">
            <div>
              <h2>题目编辑 / 预览</h2>
              <span>{{ questionTypeText(activeQuestion.question_type) }}</span>
            </div>
            <div class="editor-tools">
              <select v-model="activeQuestion.question_type" @change="normalizeActiveQuestionByType">
                <option value="multiple_choice">选择题</option>
                <option value="fill_blank">填空题</option>
                <option value="programming">编程题</option>
              </select>
              <button type="button" class="btn ghost small" @click="saveActiveQuestionToBank">保存到题库</button>
            </div>
          </div>

          <div class="editor-grid">
            <section class="editor-fields">
              <label class="field">
                <span>题目标题</span>
                <input v-model="activeQuestion.title" placeholder="请输入题目标题" />
              </label>
              <label class="field">
                <span>题目内容</span>
                <textarea v-model="activeQuestion.prompt" rows="7" placeholder="请输入题干、要求和必要说明" />
              </label>

              <div v-if="activeQuestion.question_type === 'multiple_choice'" class="option-editor">
                <div class="sub-head">
                  <strong>选项（单选）</strong>
                  <button type="button" class="link-btn" @click="addOption(activeQuestion)">新增选项</button>
                </div>
                <article v-for="(option, index) in activeQuestion.options" :key="option.localKey" class="option-row">
                  <label>
                    <input v-model="activeQuestion.answer" type="radio" :value="option.key" />
                    <span>{{ option.key }}</span>
                  </label>
                  <input v-model="option.text" placeholder="选项内容" />
                  <button type="button" class="icon-danger" @click="removeOption(activeQuestion, index)">×</button>
                </article>
              </div>

              <label v-if="activeQuestion.question_type === 'fill_blank'" class="field">
                <span>参考答案</span>
                <textarea v-model="activeQuestion.answer_text" rows="3" placeholder="可填写一个或多个参考答案，用逗号分隔" />
              </label>

              <template v-if="activeQuestion.question_type === 'programming'">
                <label class="field">
                  <span>初始代码</span>
                  <textarea v-model="activeQuestion.starter_code" rows="5" class="code-textarea" placeholder="学生打开题目时默认展示的代码" />
                </label>
                <div class="grading-box">
                  <div class="sub-head">
                    <strong>编程题判题</strong>
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

              <label class="field">
                <span>解析 / AI 判分依据</span>
                <textarea v-model="activeQuestion.explanation" rows="3" placeholder="给教师和 AI 判分参考的解析，可留空" />
              </label>
            </section>

            <aside class="preview-box">
              <div class="preview-title">
                <span>预览</span>
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
            </aside>
          </div>
        </section>
      </section>
    </main>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  createTeacherAssignmentApi,
  createTeacherQuestionBankItemApi,
  generateAssignmentQuestionsApi,
  generateAssignmentTestCasesApi,
  getTeacherAssignmentApi,
  listTeacherQuestionBankApi,
  reuseTeacherQuestionBankItemApi,
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
const questionBank = ref([]);
const errorMessage = ref("");
const successMessage = ref("");
const saving = ref(false);
const generating = ref(false);
const testcaseGenerating = ref(false);
const bankLoading = ref(false);
const coreMode = ref("ai");
const activeQuestionIndex = ref(0);
const draggingQuestionIndex = ref(null);
const dragOverQuestionIndex = ref(null);
const generateRequirement = ref("");
const generateKnowledge = ref("");
const generateCounts = ref({ multiple_choice: 5, fill_blank: 3, programming: 1 });
const bankFilters = ref({ keyword: "", question_type: "", difficulty: "" });
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

onMounted(async () => {
  await Promise.all([loadStudents(), loadQuestionBank()]);
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

async function loadQuestionBank() {
  bankLoading.value = true;
  try {
    const { data } = await listTeacherQuestionBankApi({ ...bankFilters.value, limit: 80 });
    questionBank.value = data || [];
  } catch (error) {
    handleApiError(error, "加载题库失败。");
  } finally {
    bankLoading.value = false;
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

function startQuestionDrag(index, event) {
  draggingQuestionIndex.value = index;
  dragOverQuestionIndex.value = index;
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", String(index));
}

function dragEnterQuestion(index) {
  if (draggingQuestionIndex.value === null) return;
  dragOverQuestionIndex.value = index;
}

function dropQuestion(index) {
  if (draggingQuestionIndex.value === null) return;
  moveQuestionTo(draggingQuestionIndex.value, index);
  endQuestionDrag();
}

function endQuestionDrag() {
  draggingQuestionIndex.value = null;
  dragOverQuestionIndex.value = null;
}

function moveQuestionTo(fromIndex, toIndex) {
  if (fromIndex === toIndex || toIndex < 0 || toIndex >= form.value.questions.length) return;
  const [item] = form.value.questions.splice(fromIndex, 1);
  form.value.questions.splice(toIndex, 0, item);
  activeQuestionIndex.value = toIndex;
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

async function reuseBankQuestion(item) {
  try {
    const { data } = await reuseTeacherQuestionBankItemApi(item.id);
    addQuestion(data);
    successMessage.value = "题库题目已加入当前作业。";
    await loadQuestionBank();
  } catch (error) {
    handleApiError(error, "复用题目失败。");
  }
}

async function saveActiveQuestionToBank() {
  if (!activeQuestion.value) return;
  try {
    await createTeacherQuestionBankItemApi(toQuestionPayload(activeQuestion.value, 0));
    successMessage.value = "当前题目已保存到题库。";
    await loadQuestionBank();
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
    await loadQuestionBank();
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
  display: grid;
  gap: 12px;
  color: #162033;
  font-size: var(--compact-body);
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
  font-weight: 650;
  letter-spacing: 0;
}

.studio-hero h1 span {
  color: #66738a;
  font-weight: 500;
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
.bank-filters,
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
  font-weight: 560;
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

.btn.ghost {
  background: #f8fafc;
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
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}

.question-rail {
  position: sticky;
  top: 12px;
  display: grid;
  gap: 10px;
  padding: 12px;
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
  font-weight: 650;
  letter-spacing: 0;
}

.question-list,
.bank-list,
.compact-bank-list {
  display: grid;
  gap: 7px;
}

.question-card {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) 28px;
  gap: 8px;
  align-items: center;
  border: 1px solid #e4eaf3;
  border-radius: 8px;
  background: #fff;
  padding: 7px;
  transition: border-color 0.16s ease, background 0.16s ease, box-shadow 0.16s ease, opacity 0.16s ease;
}

.question-card.active {
  border-color: #2563eb;
  background: #f8fbff;
  box-shadow: inset 2px 0 0 #2563eb;
}

.question-card.dragging {
  opacity: 0.58;
}

.question-card.drag-over {
  border-color: #94a3b8;
  background: #f8fafc;
}

.drag-handle {
  display: grid;
  gap: 3px;
  place-items: center;
  width: 24px;
  height: 42px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  cursor: grab;
}

.drag-handle:active {
  cursor: grabbing;
}

.drag-handle span {
  width: 4px;
  height: 4px;
  border-radius: 50%;
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
  font-weight: 650;
}

.copy {
  display: grid;
  min-width: 0;
  gap: 5px;
}

.question-title,
.compact-bank-item span,
.bank-item strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.question-title {
  color: #1f2937;
  font-weight: 540;
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
  gap: 8px;
}

.studio-main {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.meta-panel,
.ai-panel,
.bank-panel,
.editor-panel {
  padding: 16px;
}

.meta-grid {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) 190px 190px;
  gap: 12px;
}

.field {
  display: grid;
  gap: 7px;
  color: #3c4960;
  font-weight: 540;
}

.field span {
  font-size: 12px;
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
  resize: vertical;
}

.class-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
}

.class-check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #dbe6f6;
  border-radius: 7px;
  background: #f8fafc;
  padding: 8px 10px;
  font-weight: 540;
}

.class-check input {
  width: auto;
}

.core-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 14px;
}

.core-row > *,
.panel-head > div {
  min-width: 0;
}

.mode-tabs {
  display: inline-grid;
  grid-template-columns: 1fr 1fr;
  border: 1px solid #d8e3f2;
  border-radius: 7px;
  overflow: hidden;
}

.mode-tabs button {
  border: 0;
  background: #fff;
  padding: 8px 14px;
  color: #52637d;
  font-weight: 560;
  cursor: pointer;
}

.mode-tabs .active {
  background: #2563eb;
  color: #fff;
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

.bank-inline {
  display: grid;
  gap: 12px;
  margin-top: 12px;
}

.bank-filters {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) 130px 130px auto;
}

.bank-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  border: 1px solid #e0e9f6;
  border-radius: 8px;
  padding: 10px;
  background: #fbfdff;
}

.bank-item p {
  display: -webkit-box;
  margin: 4px 0 8px;
  overflow: hidden;
  color: #6c7890;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.compact-bank-item {
  display: grid;
  gap: 4px;
  border: 1px solid #e0e9f6;
  border-radius: 8px;
  background: #fbfdff;
  padding: 10px;
  text-align: left;
  cursor: pointer;
}

.compact-bank-item small {
  color: #6d7890;
}

.link-btn {
  border: 0;
  background: transparent;
  color: #2563eb;
  font-weight: 560;
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
  font-weight: 560;
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
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 16px;
  margin-top: 14px;
}

.editor-fields {
  display: grid;
  gap: 12px;
}

.option-editor,
.grading-box {
  display: grid;
  gap: 10px;
  border: 1px solid #e1eaf7;
  border-radius: 8px;
  background: #fbfdff;
  padding: 12px;
}

.option-row,
.case-row {
  display: grid;
  grid-template-columns: 70px minmax(0, 1fr) 28px;
  gap: 8px;
  align-items: center;
}

.option-row label,
.case-row label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 560;
}

.option-row input[type="radio"],
.case-row input[type="checkbox"] {
  width: auto;
}

.case-row {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 70px 28px;
}

.code-textarea,
.code-preview {
  font-family: Consolas, "Courier New", monospace;
}

.preview-box {
  display: grid;
  align-content: start;
  gap: 12px;
  border: 1px solid #dfe8f5;
  border-radius: 8px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  padding: 14px;
}

.preview-title {
  display: grid;
  gap: 4px;
}

.preview-title span {
  color: #6d7890;
  font-size: 12px;
  font-weight: 560;
}

.preview-box p {
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
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 8px;
  align-items: start;
  border: 1px solid #e4edf8;
  border-radius: 7px;
  padding: 8px;
}

.preview-options span {
  display: grid;
  width: 24px;
  height: 24px;
  place-items: center;
  border-radius: 50%;
  background: #eef4ff;
  color: #2563eb;
  font-weight: 650;
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

@media (max-width: 1440px) {
  .ai-controls {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .generate-btn {
    grid-column: 1 / -1;
  }
}

@media (max-width: 900px) {
  .studio-grid,
  .core-row,
  .editor-grid {
    grid-template-columns: 1fr;
  }

  .question-rail {
    position: static;
  }

  .meta-grid,
  .ai-controls,
  .bank-filters {
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
  .meta-grid,
  .ai-controls,
  .bank-filters {
    display: grid;
    grid-template-columns: 1fr;
    width: 100%;
  }

  .case-row,
  .option-row {
    grid-template-columns: 1fr;
  }
}
</style>
