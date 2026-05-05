<template>
  <section class="assignment-studio">
    <PageHeader
      :title="isNew ? '新建作业' : '编辑作业'"
      title-tag="h1"
      :subtitle="!isNew ? '面向高频布置作业：AI 出题、题库复用、题型编辑和班级发布都在一个工作台完成。' : ''"
    >
      <template #actions>
        <router-link class="btn ghost" to="/teacher/assignments">返回列表</router-link>
        <router-link v-if="!isNew" class="btn ghost" :to="`/teacher/assignments/${assignmentId}/progress`">完成情况</router-link>
        <button type="button" class="btn primary" :disabled="saving" @click="saveAssignment">
          {{ saving ? "保存中..." : "保存作业" }}
        </button>
      </template>
    </PageHeader>

    <Teleport to="body">
      <div v-if="errorMessage" class="dialog-backdrop" role="presentation" @click.self="errorMessage = ''">
        <section class="error-dialog" role="alertdialog" aria-modal="true" aria-labelledby="assignment-error-title">
          <div class="error-dialog-icon">!</div>
          <div class="error-dialog-content">
            <h2 id="assignment-error-title">操作未完成</h2>
            <p>{{ errorMessage }}</p>
          </div>
          <button type="button" class="dialog-close" aria-label="关闭错误提示" @click="errorMessage = ''">×</button>
        </section>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="questionBankOpen" class="dialog-backdrop" role="presentation" @click.self="closeQuestionBankDialog">
        <section class="bank-dialog" role="dialog" aria-modal="true" aria-labelledby="question-bank-title">
          <div class="bank-dialog-head">
            <div>
              <h2 id="question-bank-title">从题库导入</h2>
              <p>选择题库中的题目追加到当前作业，导入后仍需保存作业。</p>
            </div>
            <button type="button" class="dialog-close" aria-label="关闭题库导入" @click="closeQuestionBankDialog">×</button>
          </div>

          <form class="bank-filters" @submit.prevent="loadQuestionBank">
            <label class="field">
              <span>搜索</span>
              <input v-model="questionBankFilters.keyword" placeholder="搜索题干或标题" />
            </label>
            <label class="field">
              <span>题型</span>
              <select v-model="questionBankFilters.question_type" @change="loadQuestionBank">
                <option value="">全部</option>
                <option value="multiple_choice">选择题</option>
                <option value="fill_blank">填空题</option>
                <option value="programming">编程题</option>
              </select>
            </label>
            <label class="field">
              <span>章节</span>
              <select v-model="questionBankFilters.chapter" @change="loadQuestionBank">
                <option value="">全部章节</option>
                <option v-for="chapter in knowledgeChapterOptions" :key="chapter" :value="chapter">{{ chapter }}</option>
              </select>
            </label>
            <button type="submit" class="btn ghost" :disabled="questionBankLoading">搜索</button>
          </form>

          <div class="bank-list">
            <p v-if="questionBankLoading" class="empty-note">正在加载题库...</p>
            <p v-else-if="!questionBankItems.length" class="empty-note">题库暂无题目，保存作业后题目会同步到题库。</p>
            <template v-else>
              <label v-for="item in questionBankItems" :key="item.id" class="bank-item">
                <input v-model="selectedQuestionBankIds" type="checkbox" :value="item.id" />
                <span class="bank-item-body">
                  <span class="bank-item-meta">
                    <small :class="['type-chip', item.question_type]">{{ questionTypeText(item.question_type) }}</small>
                    <small>{{ questionBankItemChapterText(item) }}</small>
                    <small>复用 {{ item.reuse_count || 0 }} 次</small>
                  </span>
                  <strong>{{ item.title || questionTypeText(item.question_type) }}</strong>
                  <span>{{ item.prompt || "暂无题干" }}</span>
                </span>
              </label>
            </template>
          </div>

          <div class="bank-dialog-foot">
            <span>已选择 {{ selectedQuestionBankIds.length }} 题</span>
            <div>
              <button type="button" class="btn ghost" @click="closeQuestionBankDialog">取消</button>
              <button
                type="button"
                class="btn primary"
                :disabled="!selectedQuestionBankIds.length || importingQuestionBank"
                @click="importSelectedQuestionBankItems"
              >
                {{ importingQuestionBank ? "导入中..." : "导入选中题目" }}
              </button>
            </div>
          </div>
        </section>
      </div>
    </Teleport>
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
              rows="3"
              placeholder="例如：围绕 Java 事务、异常回滚和资源释放生成一套分层练习。"
            />
          </label>
          <div class="ai-controls">
            <div class="field knowledge-search-field">
              <span>知识点</span>
              <div class="knowledge-search-row">
                <select v-model="selectedKnowledgeChapter" class="knowledge-chapter-select" @change="handleKnowledgeChapterChange">
                  <option value="">全部章节</option>
                  <option v-for="chapter in knowledgeChapterOptions" :key="chapter" :value="chapter">{{ chapter }}</option>
                </select>
                <div class="knowledge-search-box">
                  <input
                    v-model="knowledgeSearchKeyword"
                    placeholder="搜索正式图谱节点，例如：JDBC 事务"
                    @input="handleKnowledgeSearchInput"
                    @focus="handleKnowledgeSearchInput"
                    @blur="deferHideKnowledgeSuggestions"
                    @keydown.enter.prevent="selectFirstKnowledgeSuggestion"
                  />
                  <div v-if="showKnowledgeSuggestions && knowledgeSuggestions.length" class="knowledge-search-dropdown">
                    <button
                      v-for="node in knowledgeSuggestions"
                      :key="node.id"
                      type="button"
                      class="knowledge-search-item"
                      @mousedown.prevent="selectKnowledgeSuggestion(node)"
                    >
                      <strong>{{ node.name }}</strong>
                      <small v-if="node.desc">{{ node.desc }}</small>
                    </button>
                  </div>
                </div>
              </div>
              <div v-if="selectedKnowledgeNodes.length" class="knowledge-tags" aria-label="已选择知识点">
                <button
                  v-for="node in selectedKnowledgeNodes"
                  :key="node.id || node.name"
                  type="button"
                  class="knowledge-tag"
                  :title="`移除 ${node.name}`"
                  @click="removeKnowledgeTag(node)"
                >
                  {{ node.name }}
                  <span aria-hidden="true">×</span>
                </button>
              </div>
            </div>
            <label class="field mini">
              <span>选择题</span>
              <div class="count-stepper">
                <button type="button" :disabled="generateCounts.multiple_choice <= 0" aria-label="减少选择题数量" @click="adjustGenerateCount('multiple_choice', -1, 0, 20)">
                  −
                </button>
                <input v-model.number="generateCounts.multiple_choice" aria-label="选择题数量" min="0" max="20" type="number" />
                <button type="button" :disabled="generateCounts.multiple_choice >= 20" aria-label="增加选择题数量" @click="adjustGenerateCount('multiple_choice', 1, 0, 20)">
                  +
                </button>
              </div>
            </label>
            <label class="field mini">
              <span>填空题</span>
              <div class="count-stepper">
                <button type="button" :disabled="generateCounts.fill_blank <= 0" aria-label="减少填空题数量" @click="adjustGenerateCount('fill_blank', -1, 0, 20)">
                  −
                </button>
                <input v-model.number="generateCounts.fill_blank" aria-label="填空题数量" min="0" max="20" type="number" />
                <button type="button" :disabled="generateCounts.fill_blank >= 20" aria-label="增加填空题数量" @click="adjustGenerateCount('fill_blank', 1, 0, 20)">
                  +
                </button>
              </div>
            </label>
            <label class="field mini">
              <span>编程题</span>
              <div class="count-stepper">
                <button type="button" :disabled="generateCounts.programming <= 0" aria-label="减少编程题数量" @click="adjustGenerateCount('programming', -1, 0, 10)">
                  −
                </button>
                <input v-model.number="generateCounts.programming" aria-label="编程题数量" min="0" max="10" type="number" />
                <button type="button" :disabled="generateCounts.programming >= 10" aria-label="增加编程题数量" @click="adjustGenerateCount('programming', 1, 0, 10)">
                  +
                </button>
              </div>
            </label>
            <button type="button" class="btn primary generate-btn" :disabled="generating || !generateRequirement.trim()" @click="generateQuestions">
              <span class="generate-btn-content">
                <svg class="generate-btn-icon" viewBox="0 0 28 24" aria-hidden="true" focusable="false">
                  <path
                    d="M12.2 2.4l1.55 4.78 4.78 1.55-4.78 1.55-1.55 4.78-1.55-4.78-4.78-1.55 4.78-1.55 1.55-4.78z"
                    fill="currentColor"
                  />
                  <path
                    d="M21.2 1.7l.68 2.08 2.08.68-2.08.68-.68 2.08-.68-2.08-2.08-.68 2.08-.68.68-2.08z"
                    fill="currentColor"
                  />
                </svg>
                <span>{{ generating ? "生成中..." : "生成题目" }}</span>
              </span>
            </button>
          </div>
        </div>
      </section>
    </section>

    <main class="studio-grid" :class="{ 'preview-open': activeQuestion && previewOpen }">
      <aside class="question-rail panel">
        <div class="panel-head">
          <div>
            <h2>题目列表</h2>
          </div>
        </div>

        <div class="question-actions">
          <button type="button" class="btn primary" @click="addQuestion()">新建题目</button>
          <button type="button" class="btn ghost" @click="openQuestionBankDialog">导入题目</button>
        </div>

        <VueDraggable
          v-model="form.questions"
          class="question-list"
          handle=".drag-handle"
          ghost-class="question-card-ghost"
          chosen-class="question-card-chosen"
          drag-class="question-card-drag"
          fallback-class="question-card-fallback"
          draggable=".question-card"
          :direction="verticalDragDirection"
          :animation="220"
          :force-fallback="true"
          :fallback-on-body="true"
          :swap-threshold="0.65"
          @start="startQuestionSort"
          @end="endQuestionSort"
        >
          <article
            v-for="question in form.questions"
            :key="question.localKey"
            class="question-card"
            :data-question-key="question.localKey"
            :class="{
              active: questionIndex(question) === activeQuestionIndex,
              dragging: question.localKey === draggingQuestionKey,
              settling: question.localKey === settlingQuestionKey,
            }"
            @click="selectQuestion(questionIndex(question))"
          >
            <span class="drag-handle" title="拖动排序" role="button" aria-label="拖动排序" @click.stop></span>
            <button type="button" class="question-main">
              <span class="order">{{ questionIndex(question) + 1 }}</span>
              <span class="copy">
                <span class="question-line">
                  <span class="question-title">{{ questionListTitle(question) }}</span>
                  <small :class="['type-chip', question.question_type]">{{ questionTypeText(question.question_type) }}</small>
                </span>
              </span>
            </button>
            <div class="mini-actions">
              <button type="button" title="删除" class="danger" @click.stop="removeQuestion(questionIndex(question))">×</button>
            </div>
          </article>
        </VueDraggable>

      </aside>

      <section class="studio-main">
        <section v-if="activeQuestion" class="editor-panel panel">
          <div class="editor-head">
            <div>
              <h2>题目编辑</h2>
            </div>
            <div class="editor-tools">
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
        <section v-else class="editor-empty panel">
          <div class="editor-empty-mark">+</div>
          <h2>暂无题目</h2>
          <p>添加一道题目后即可继续编辑题干、选项、答案解析和判题设置。</p>
          <div class="editor-empty-actions">
            <button type="button" class="btn primary" @click="addQuestion()">新建题目</button>
            <button type="button" class="btn ghost" @click="openQuestionBankDialog">导入题目</button>
          </div>
        </section>
      </section>

      <aside v-if="activeQuestion && previewOpen" class="live-preview panel">
        <div class="preview-head">
          <h2>实时预览</h2>
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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { VueDraggable } from "vue-draggable-plus";

import {
  createTeacherAssignmentApi,
  generateAssignmentQuestionsApi,
  generateAssignmentTestCasesApi,
  getTeacherAssignmentApi,
  listTeacherQuestionBankApi,
  reuseTeacherQuestionBankItemApi,
  updateTeacherAssignmentApi,
  updateTeacherAssignmentQuestionsApi,
} from "../api/assignments";
import { getTeacherGraphApi, listTeacherStudentsApi } from "../api/teacher";
import PageHeader from "../components/PageHeader.vue";
import {
  createEmptyTestCase,
  fromDatetimeLocal,
  normalizeQuestion,
  normalizeQuestionByType,
  questionTypeTabs,
  questionTypeText,
  toDatetimeLocal,
  toQuestionPayload,
} from "../features/teacher-assignments/editorModel";
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
const questionBankOpen = ref(false);
const questionBankLoading = ref(false);
const importingQuestionBank = ref(false);
const questionBankItems = ref([]);
const selectedQuestionBankIds = ref([]);
const questionBankFilters = ref({
  keyword: "",
  question_type: "",
  chapter: "",
});
const activeQuestionIndex = ref(0);
const draggingQuestionKey = ref(null);
const settlingQuestionKey = ref(null);
const previewOpen = ref(false);
const generateRequirement = ref("");
const generateKnowledge = ref("");
const knowledgeSearchKeyword = ref("");
const knowledgeSuggestions = ref([]);
const selectedKnowledgeNodes = ref([]);
const showKnowledgeSuggestions = ref(false);
const selectedKnowledgeChapter = ref("");
const knowledgeChapterOptions = ref([]);
const generateCounts = ref({ multiple_choice: 5, fill_blank: 3, programming: 1 });
let questionSettleTimer = null;
let questionFlightAnimation = null;
let questionDragPointerOffset = null;
let knowledgeSuggestTimer = null;
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
const verticalDragDirection = () => "vertical";

onMounted(async () => {
  await Promise.all([loadStudents(), loadKnowledgeChapterOptions()]);
  if (!isNew.value) {
    await loadAssignment();
  } else {
    form.value.class_names = classOptions.value.slice(0, 1);
    addQuestion({ question_type: "multiple_choice" });
  }
});

onBeforeUnmount(() => {
  clearQuestionSettleState();
  if (knowledgeSuggestTimer) clearTimeout(knowledgeSuggestTimer);
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

async function loadKnowledgeChapterOptions() {
  try {
    const { data } = await getTeacherGraphApi({ keyword: "", limit: 2000 });
    knowledgeChapterOptions.value = [...new Set((data.nodes || []).map((node) => node.chapter).filter(Boolean))].sort((left, right) =>
      left.localeCompare(right, "zh-Hans-CN"),
    );
  } catch (error) {
    knowledgeChapterOptions.value = [];
  }
}

function selectQuestion(index) {
  activeQuestionIndex.value = index;
}

function setActiveQuestionType(questionType) {
  if (!activeQuestion.value || activeQuestion.value.question_type === questionType) return;
  activeQuestion.value.question_type = questionType;
  if (activeQuestion.value) normalizeQuestionByType(activeQuestion.value);
}

function addQuestion(source = {}) {
  form.value.questions.push(normalizeQuestion({
    ...source,
    id: source.id,
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

function openQuestionBankDialog() {
  questionBankOpen.value = true;
  errorMessage.value = "";
  successMessage.value = "";
  selectedQuestionBankIds.value = [];
  loadQuestionBank();
}

function closeQuestionBankDialog() {
  if (importingQuestionBank.value) return;
  questionBankOpen.value = false;
}

async function loadQuestionBank() {
  questionBankLoading.value = true;
  try {
    const { data } = await listTeacherQuestionBankApi({
      keyword: questionBankFilters.value.keyword.trim(),
      question_type: questionBankFilters.value.question_type,
      chapter: questionBankFilters.value.chapter,
      limit: 50,
    });
    questionBankItems.value = Array.isArray(data) ? data : [];
    const availableIds = new Set(questionBankItems.value.map((item) => item.id));
    selectedQuestionBankIds.value = selectedQuestionBankIds.value.filter((id) => availableIds.has(id));
  } catch (error) {
    handleApiError(error, "加载题库失败。");
  } finally {
    questionBankLoading.value = false;
  }
}

async function importSelectedQuestionBankItems() {
  const selectedIds = new Set(selectedQuestionBankIds.value);
  const selectedItems = questionBankItems.value.filter((item) => selectedIds.has(item.id));
  if (!selectedItems.length) return;

  importingQuestionBank.value = true;
  try {
    const firstImportedIndex = form.value.questions.length;
    selectedItems.forEach((item) => addQuestion(toImportedQuestion(item)));
    activeQuestionIndex.value = firstImportedIndex;
    await Promise.all(selectedItems.map((item) => reuseTeacherQuestionBankItemApi(item.id)));
    successMessage.value = `已导入 ${selectedItems.length} 道题目，保存作业后生效。`;
    questionBankOpen.value = false;
  } catch (error) {
    handleApiError(error, "导入题库题目失败。");
  } finally {
    importingQuestionBank.value = false;
  }
}

function toImportedQuestion(item) {
  return {
    ...item,
    id: undefined,
    test_cases: (item.test_cases || []).map((testCase) => ({
      ...testCase,
      id: undefined,
    })),
  };
}

function questionBankItemChapterText(item) {
  const chapters = [...new Set((item.knowledge_nodes || []).map((node) => node.chapter).filter(Boolean))];
  return chapters.length ? chapters.join("、") : "未绑定章节";
}

function removeQuestion(index) {
  form.value.questions.splice(index, 1);
  activeQuestionIndex.value = Math.min(activeQuestionIndex.value, Math.max(form.value.questions.length - 1, 0));
}

function startQuestionSort(event) {
  clearQuestionSettleState();
  settlingQuestionKey.value = null;
  draggingQuestionKey.value = form.value.questions[event.oldIndex]?.localKey || null;
  questionDragPointerOffset = getQuestionDragPointerOffset(event);
}

function endQuestionSort(event) {
  const draggedKey = draggingQuestionKey.value;
  const pointer = getEventPointer(event);
  const flightSource = event?.item?.cloneNode(true);

  draggingQuestionKey.value = null;
  settlingQuestionKey.value = draggedKey;

  nextTick(() => animateQuestionReturn(draggedKey, pointer, flightSource));
  selectQuestionByKey(draggedKey);
}

function clearQuestionSettleState() {
  if (questionSettleTimer) {
    clearTimeout(questionSettleTimer);
    questionSettleTimer = null;
  }
  if (questionFlightAnimation) {
    questionFlightAnimation.remove();
    questionFlightAnimation = null;
  }
  questionDragPointerOffset = null;
}

function getEventPointer(event) {
  const originalEvent = event?.originalEvent || event;
  const touch = originalEvent?.changedTouches?.[0] || originalEvent?.touches?.[0];
  if (touch) return { x: touch.clientX, y: touch.clientY };
  if (Number.isFinite(originalEvent?.clientX) && Number.isFinite(originalEvent?.clientY)) {
    return { x: originalEvent.clientX, y: originalEvent.clientY };
  }
  return null;
}

function getQuestionDragPointerOffset(event) {
  const pointer = getEventPointer(event);
  const itemRect = event?.item?.getBoundingClientRect?.();
  if (!pointer || !itemRect) return null;
  return {
    x: pointer.x - itemRect.left,
    y: pointer.y - itemRect.top,
  };
}

function findQuestionCardElement(localKey) {
  return Array.from(document.querySelectorAll(".question-card")).find((item) => item.dataset.questionKey === String(localKey));
}

function animateQuestionReturn(draggedKey, pointer, sourceElement) {
  const targetElement = findQuestionCardElement(draggedKey);
  if (!draggedKey || !pointer || !targetElement) {
    finishQuestionReturn(draggedKey, 0);
    return;
  }

  const targetRect = targetElement.getBoundingClientRect();
  const pointerOffset = questionDragPointerOffset || {
    x: targetRect.width / 2,
    y: targetRect.height / 2,
  };
  const startLeft = pointer.x - pointerOffset.x;
  const startTop = pointer.y - pointerOffset.y;
  const flightCard = sourceElement || targetElement.cloneNode(true);
  flightCard.classList.remove("dragging", "settling", "question-card-ghost", "question-card-drag", "question-card-fallback");
  flightCard.classList.add("question-card-flight");
  flightCard.style.width = `${targetRect.width}px`;
  flightCard.style.height = `${targetRect.height}px`;
  flightCard.style.left = `${startLeft}px`;
  flightCard.style.top = `${startTop}px`;
  document.body.appendChild(flightCard);

  const deltaX = targetRect.left - startLeft;
  const deltaY = targetRect.top - startTop;
  const animation = flightCard.animate(
    [
      { transform: "translate3d(0, 0, 0) scale(1.02)", opacity: 1 },
      { transform: `translate3d(${deltaX}px, ${deltaY}px, 0) scale(1)`, opacity: 1 },
    ],
    {
      duration: 280,
      easing: "cubic-bezier(0.22, 1, 0.36, 1)",
      fill: "forwards",
    },
  );

  questionFlightAnimation = flightCard;
  animation.onfinish = () => {
    flightCard.remove();
    questionFlightAnimation = null;
    finishQuestionReturn(draggedKey, 0);
  };
  animation.oncancel = () => {
    flightCard.remove();
  };
}

function finishQuestionReturn(draggedKey, delay = 0) {
  questionSettleTimer = setTimeout(() => {
    if (settlingQuestionKey.value === draggedKey) {
      settlingQuestionKey.value = null;
    }
    questionSettleTimer = null;
  }, delay);
}

function selectQuestionByKey(localKey) {
  if (!localKey) return;
  const nextIndex = form.value.questions.findIndex((question) => question.localKey === localKey);
  if (nextIndex >= 0) activeQuestionIndex.value = nextIndex;
}

function questionIndex(question) {
  return form.value.questions.findIndex((item) => item.localKey === question.localKey);
}

function questionListTitle(question) {
  return question.prompt?.trim() || question.title?.trim() || "未命名题目";
}

function adjustGenerateCount(key, delta, min, max) {
  const current = Number(generateCounts.value[key]) || 0;
  const next = Math.min(max, Math.max(min, current + delta));
  generateCounts.value[key] = next;
}

function addTestCase(question) {
  question.test_cases.push(createEmptyTestCase(question.test_cases.length));
}

function removeTestCase(question, index) {
  question.test_cases.splice(index, 1);
}

function handleKnowledgeSearchInput() {
  if (knowledgeSuggestTimer) clearTimeout(knowledgeSuggestTimer);
  const query = knowledgeSearchKeyword.value.trim();
  if (!query && !selectedKnowledgeChapter.value) {
    knowledgeSuggestions.value = [];
    showKnowledgeSuggestions.value = false;
    return;
  }
  knowledgeSuggestTimer = setTimeout(() => {
    fetchKnowledgeSuggestions(query);
  }, 180);
}

async function fetchKnowledgeSuggestions(query) {
  try {
    const { data } = await getTeacherGraphApi({ keyword: query, chapter: selectedKnowledgeChapter.value, limit: 50 });
    knowledgeSuggestions.value = (data.nodes || []).filter(
      (node) => !selectedKnowledgeNodes.value.some((selected) => isSameKnowledgeNode(selected, node)),
    );
    showKnowledgeSuggestions.value = knowledgeSuggestions.value.length > 0;
  } catch (error) {
    knowledgeSuggestions.value = [];
    showKnowledgeSuggestions.value = false;
  }
}

function handleKnowledgeChapterChange() {
  handleKnowledgeSearchInput();
}

function selectKnowledgeSuggestion(node) {
  if (!selectedKnowledgeNodes.value.some((selected) => isSameKnowledgeNode(selected, node))) {
    selectedKnowledgeNodes.value.push({
      id: node.id,
      name: node.name,
      desc: node.desc || "",
    });
    syncGenerateKnowledge();
  }
  knowledgeSearchKeyword.value = "";
  knowledgeSuggestions.value = [];
  showKnowledgeSuggestions.value = false;
}

function selectFirstKnowledgeSuggestion() {
  if (knowledgeSuggestions.value.length) {
    selectKnowledgeSuggestion(knowledgeSuggestions.value[0]);
  }
}

function removeKnowledgeTag(node) {
  selectedKnowledgeNodes.value = selectedKnowledgeNodes.value.filter((item) => !isSameKnowledgeNode(item, node));
  syncGenerateKnowledge();
}

function syncGenerateKnowledge() {
  generateKnowledge.value = selectedKnowledgeNodes.value.map((node) => node.name).join("、");
}

function isSameKnowledgeNode(left, right) {
  return String(left.id || left.name) === String(right.id || right.name);
}

function deferHideKnowledgeSuggestions() {
  setTimeout(() => {
    showKnowledgeSuggestions.value = false;
  }, 120);
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

function handleApiError(error, fallbackMessage) {
  const status = error?.response?.status;
  if (status === 401 || status === 403) {
    clearAuthSession();
    router.push("/login");
    return;
  }
  errorMessage.value = formatApiErrorDetail(error?.response?.data?.detail, fallbackMessage);
}

function formatApiErrorDetail(detail, fallbackMessage) {
  if (typeof detail === "string") return detail;
  if (!Array.isArray(detail)) return fallbackMessage;

  return detail
    .map((item) => {
      const field = Array.isArray(item?.loc) ? item.loc[item.loc.length - 1] : "";
      if (field === "title" && item?.type === "string_too_short") return "作业标题不能为空。";
      if (field === "prompt" && item?.type === "string_too_short") return "题目内容不能为空。";
      return item?.msg || fallbackMessage;
    })
    .filter(Boolean)
    .join("；");
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

.panel,
.feedback {
  border: 1px solid #e3e8f1;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 10px 28px rgba(23, 37, 60, 0.06);
}

.empty-note {
  margin: 0;
  color: #6d7890;
}

.editor-tools,
.ai-controls,
.mini-actions {
  display: flex;
  align-items: center;
  gap: 10px;
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
  background: #ffffff;
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

:global(.dialog-backdrop) {
  position: fixed;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(15, 23, 42, 0.42);
  padding: 20px;
  z-index: 10000;
}

:global(.error-dialog) {
  position: relative;
  box-sizing: border-box;
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  gap: 14px;
  width: min(440px, 100%);
  border: 1px solid #fecaca;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.28);
  padding: 20px 48px 20px 20px;
}

:global(.error-dialog-icon) {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 50%;
  background: #fee2e2;
  color: #b42318;
  font-size: 20px;
  font-weight: 600;
  line-height: 1;
}

:global(.error-dialog-content) {
  min-width: 0;
}

:global(.error-dialog h2) {
  margin: 0 0 8px;
  color: #172033;
  font-size: 16px;
  font-weight: 500;
  letter-spacing: 0;
}

:global(.error-dialog p) {
  margin: 0;
  color: #b42318;
  line-height: 1.65;
  word-break: break-word;
}

:global(.dialog-close) {
  position: absolute;
  top: 12px;
  right: 12px;
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border: 1px solid #f3d5d5;
  border-radius: 6px;
  background: #fff;
  color: #9f1d1d;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
}

:global(.dialog-close:hover) {
  background: #fff7f7;
}

.bank-dialog {
  position: relative;
  box-sizing: border-box;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: 16px;
  width: min(860px, 100%);
  max-height: min(760px, calc(100vh - 40px));
  border: 1px solid #e3e8f1;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.28);
  padding: 22px;
}

.bank-dialog-head {
  padding-right: 42px;
}

.bank-dialog-head h2 {
  margin: 0 0 6px;
  color: #172033;
  font-size: 18px;
  font-weight: 500;
}

.bank-dialog-head p {
  margin: 0;
  color: #6d7890;
  line-height: 1.6;
}

.bank-filters {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 150px 140px auto;
  gap: 10px;
  align-items: end;
}

.bank-list {
  display: grid;
  align-content: start;
  gap: 10px;
  min-height: 220px;
  overflow: auto;
  padding-right: 4px;
}

.bank-list > .empty-note {
  align-self: center;
  justify-self: center;
  text-align: center;
}

.bank-item {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  border: 1px solid #e4eaf3;
  border-radius: 8px;
  background: #fff;
  padding: 12px;
  cursor: pointer;
  transition: border-color 0.16s ease, background 0.16s ease;
}

.bank-item:hover {
  border-color: #b9d0ff;
  background: #fbfdff;
}

.bank-item input {
  width: 16px;
  height: 16px;
  margin: 4px 0 0;
  accent-color: #2563eb;
}

.bank-item-body {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.bank-item-body strong {
  overflow: hidden;
  color: #172033;
  font-size: 14px;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bank-item-body > span:last-child {
  display: -webkit-box;
  overflow: hidden;
  color: #4b5870;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.bank-item-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.bank-item-meta small:not(.type-chip) {
  border-radius: 5px;
  background: #f5f7fb;
  color: #7a879d;
  padding: 1px 5px;
  font-size: 10px;
}

.bank-dialog-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-top: 1px solid #e8eef6;
  padding-top: 14px;
  color: #6d7890;
}

.bank-dialog-foot > div {
  display: flex;
  align-items: center;
  gap: 10px;
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

.question-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.question-actions .btn {
  width: 100%;
}

.question-card {
  flex: 0 0 auto;
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr) 30px;
  gap: 6px;
  align-items: center;
  border: 1px solid #e4eaf3;
  border-radius: 7px;
  background: #fff;
  min-height: 54px;
  padding: 8px 9px 8px 6px;
  transition: border-color 0.16s ease, background 0.16s ease, box-shadow 0.16s ease, opacity 0.16s ease;
  user-select: none;
}

.question-card.active {
  border-color: #2563eb;
  background: #ffffff;
  box-shadow: 0 10px 22px rgba(37, 99, 235, 0.08);
}

.question-card.dragging:not(.question-card-drag):not(.question-card-fallback) {
  opacity: 0 !important;
  pointer-events: none;
}

.question-card.settling {
  opacity: 0 !important;
  pointer-events: none;
}

.question-card-chosen {
  border-color: #9fb8ef;
}

:global(.question-card-ghost) {
  opacity: 0 !important;
  visibility: hidden !important;
  border-color: transparent !important;
  background: transparent !important;
  box-shadow: none !important;
}

.question-card-drag {
  box-shadow: 0 14px 28px rgba(31, 41, 55, 0.16);
  z-index: 5;
  transition: none !important;
  opacity: 1 !important;
  visibility: visible !important;
}

:global(.question-card-fallback) {
  display: grid !important;
  grid-template-columns: 8px minmax(0, 1fr) 30px !important;
  gap: 6px !important;
  align-items: center !important;
  min-height: 54px !important;
  padding: 8px 9px 8px 6px !important;
  color: #162033;
  font-size: 13px !important;
  opacity: 1 !important;
  visibility: visible !important;
}

:global(.question-card-flight) {
  position: fixed !important;
  box-sizing: border-box;
  display: grid !important;
  grid-template-columns: 8px minmax(0, 1fr) 30px !important;
  gap: 6px !important;
  align-items: center !important;
  min-height: 54px !important;
  padding: 8px 9px 8px 6px !important;
  color: #162033;
  font-size: 13px !important;
  margin: 0 !important;
  pointer-events: none;
  z-index: 100000;
  opacity: 1 !important;
  visibility: visible !important;
  box-shadow: 0 18px 34px rgba(31, 41, 55, 0.18);
  transition: none !important;
}

:global(.question-card-fallback .question-main),
:global(.question-card-flight .question-main) {
  font: inherit !important;
}

:global(.question-card-fallback .question-title),
:global(.question-card-flight .question-title) {
  color: #1f2937;
  font-size: 13px !important;
  font-weight: 400;
  line-height: normal;
}

.drag-handle {
  position: relative;
  width: 12px;
  height: 24px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  cursor: grab;
  opacity: 0.72;
  touch-action: none;
  transition: opacity 0.16s ease, transform 0.16s ease;
}

.drag-handle::before {
  content: "";
  position: absolute;
  inset: -6px;
}

.drag-handle::after {
  content: "";
  position: absolute;
  top: 5px;
  left: 1px;
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #8a96aa;
  box-shadow: 0 6px 0 #8a96aa, 0 12px 0 #8a96aa, 6px 0 0 #8a96aa, 6px 6px 0 #8a96aa, 6px 12px 0 #8a96aa;
}

.drag-handle:active {
  cursor: grabbing;
  opacity: 1;
  transform: scale(0.96);
}

.question-card:hover .drag-handle {
  opacity: 1;
}

.question-main {
  display: flex;
  width: 100%;
  gap: 6px;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.order {
  display: grid;
  width: 21px;
  height: 21px;
  place-items: center;
  border-radius: 6px;
  background: #eff4ff;
  color: #1d4ed8;
  font-size: 10px;
  font-weight: 400;
}

.copy {
  display: grid;
  min-width: 0;
}

.question-line {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.question-title {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.question-line .type-chip {
  flex: 0 0 auto;
}

.question-title {
  color: #1f2937;
  font-weight: 400;
}

.mini-actions {
  justify-content: center;
}

.mini-actions button,
.icon-danger {
  width: 28px;
  height: 28px;
  border: 1px solid #d9e3f2;
  border-radius: 7px;
  background: #fff;
  color: #51617c;
  display: grid;
  place-items: center;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.mini-actions .danger,
.icon-danger {
  color: #dc2626;
  font-size: 20px;
}

.mini-actions .danger {
  position: relative;
  color: transparent;
  font-size: 0;
}

.mini-actions .danger::before,
.mini-actions .danger::after {
  content: "";
  position: absolute;
  top: 50%;
  left: 50%;
  width: 12px;
  height: 2px;
  border-radius: 999px;
  background: #dc2626;
  transform-origin: center;
}

.mini-actions .danger::before {
  transform: translate(-50%, -50%) rotate(45deg);
}

.mini-actions .danger::after {
  transform: translate(-50%, -50%) rotate(-45deg);
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

.editor-empty {
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 12px;
  min-height: 320px;
  padding: 36px 24px;
  text-align: center;
}

.editor-empty-mark {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border: 1px dashed #9fb8ef;
  border-radius: 8px;
  background: #f8fbff;
  color: #2563eb;
  font-size: 28px;
  line-height: 1;
}

.editor-empty h2 {
  margin: 0;
  color: #172033;
  font-size: 18px;
  font-weight: 400;
}

.editor-empty p {
  max-width: 420px;
  margin: 0;
  color: #6d7890;
  line-height: 1.7;
}

.editor-empty-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  width: min(440px, 100%);
  margin-top: 6px;
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

.ai-panel .field > span {
  font-size: 13px;
  color: #a2adbf;
  font-weight: 400;
}

.editor-section .field > span {
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
  margin-top: 0;
}

.ai-controls {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  align-items: end;
}

.ai-controls > .field:first-child {
  grid-column: 1 / -1;
}

.field.mini {
  align-content: start;
}

.knowledge-search-field {
  position: relative;
  align-content: start;
}

.knowledge-search-row {
  display: grid;
  grid-template-columns: minmax(128px, 0.28fr) minmax(0, 1fr);
  gap: 8px;
}

.knowledge-chapter-select {
  min-height: 40px;
}

.knowledge-search-box {
  position: relative;
}

.knowledge-search-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  z-index: 20;
  display: grid;
  gap: 6px;
  max-height: 260px;
  overflow-y: auto;
  border: 1px solid #dce8f5;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.12);
  padding: 8px;
}

.knowledge-search-item {
  display: grid;
  gap: 3px;
  width: 100%;
  border: 1px solid #d8e7f6;
  border-radius: 7px;
  background: #fff;
  color: #214666;
  padding: 9px 10px;
  text-align: left;
  cursor: pointer;
}

.knowledge-search-item strong {
  overflow: hidden;
  color: inherit;
  font-size: 13px;
  font-weight: 400;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.knowledge-search-item small {
  overflow: hidden;
  color: #73869a;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.knowledge-search-item:hover {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
}

.knowledge-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 28px;
}

.knowledge-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  border: 1px solid #cfe0ff;
  border-radius: 7px;
  background: #f8fbff;
  color: #1d4ed8;
  padding: 5px 8px;
  font: inherit;
  font-size: 12px;
  line-height: 1.2;
  cursor: pointer;
}

.knowledge-tag span {
  color: #6d7890;
  font-size: 14px;
  line-height: 1;
}

.knowledge-tag:hover {
  border-color: #9fb8ef;
  background: #edf4ff;
}

.count-stepper {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) 44px;
  align-items: stretch;
  min-height: 40px;
  border: 1px solid #d9e3f2;
  border-radius: 10px;
  background: #fff;
  overflow: hidden;
}

.count-stepper button {
  display: grid;
  place-items: center;
  border: 0;
  background: transparent;
  color: #5472b5;
  cursor: pointer;
  font-size: 22px;
  font-weight: 400;
  line-height: 1;
  transition: background 0.16s ease, color 0.16s ease;
}

.count-stepper button:hover:not(:disabled) {
  background: #f5f9ff;
  color: #2563eb;
}

.count-stepper button:disabled {
  color: #c4cfde;
  cursor: not-allowed;
}

.count-stepper input {
  border: 0;
  border-left: 1px solid #dfe7f3;
  border-right: 1px solid #dfe7f3;
  border-radius: 0;
  background: #fff;
  color: #17233b;
  font-size: 18px;
  font-weight: 400;
  line-height: 1;
  padding: 0;
  text-align: center;
  -moz-appearance: textfield;
}

.count-stepper input::-webkit-outer-spin-button,
.count-stepper input::-webkit-inner-spin-button {
  margin: 0;
  -webkit-appearance: none;
}

.generate-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  align-self: end;
  width: 100%;
  min-height: 38px;
  border-radius: 9px;
  padding: 8px 14px;
  font-size: 15px;
  font-weight: 400;
  letter-spacing: 0;
}

.generate-btn-content {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: fit-content;
  margin: 0 auto;
  transform: translateX(-8px);
}

.generate-btn-content > span {
  transform: translateX(-6px);
}

.generate-btn-icon {
  width: 24px;
  height: 24px;
  flex: none;
  transform: translateY(2px);
}

.generate-btn span {
  line-height: 1;
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
  border-radius: 5px;
  padding: 1px 5px;
  background: #edf4ff;
  color: #2563eb;
  font-size: 10px;
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
  background: #ffffff;
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
  background: #ffffff;
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
  background: #ffffff;
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
  background: #ffffff;
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
    min-height: 38px;
  }
}

@media (max-width: 1180px) {
  .studio-grid {
    grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  }

  .studio-grid.preview-open {
    grid-template-columns: minmax(190px, 230px) minmax(0, 1fr) minmax(260px, 300px);
  }

  .editor-empty-actions {
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
  .bank-dialog {
    max-height: calc(100vh - 24px);
    padding: 18px;
  }

  .bank-filters,
  .bank-dialog-foot,
  .bank-dialog-foot > div {
    display: grid;
    grid-template-columns: 1fr;
    width: 100%;
  }

  .panel-head,
  .editor-head {
    flex-direction: column;
  }

  .editor-tools,
  .basic-grid,
  .meta-grid,
  .ai-controls {
    display: grid;
    grid-template-columns: 1fr;
    width: 100%;
  }

  .editor-empty-actions {
    grid-template-columns: 1fr 1fr;
  }

  .knowledge-search-row {
    grid-template-columns: 1fr;
  }

  .case-row,
  .option-row {
    grid-template-columns: 1fr;
  }
}
</style>
