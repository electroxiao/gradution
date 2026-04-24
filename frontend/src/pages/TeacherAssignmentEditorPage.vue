<template>
  <section class="editor-page">
    <header class="editor-hero">
      <div class="hero-copy">
        <span class="eyebrow">Assignment Studio</span>
        <h2>{{ isNew ? "新建作业" : "编辑作业" }}</h2>
        <p>在同一个工作台完成发布对象、题目内容、知识点绑定、AI 判题和测试用例配置。</p>
      </div>
      <div class="hero-actions">
        <router-link class="btn btn-quiet" to="/teacher/assignments">返回列表</router-link>
        <router-link
          v-if="!isNew"
          class="btn btn-quiet"
          :to="`/teacher/assignments/${assignmentId}/progress`"
        >
          完成情况
        </router-link>
        <button type="button" class="btn btn-primary" :disabled="saving" @click="saveAssignment">
          {{ saving ? "保存中..." : "保存作业" }}
        </button>
      </div>
    </header>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>
    <p v-if="successMessage" class="feedback success">{{ successMessage }}</p>

    <section class="meta-strip">
      <label class="field title-field">
        <span>作业标题</span>
        <input v-model="form.title" placeholder="例如：JDBC 事务与资源释放练习" />
      </label>
      <label class="field status-field">
        <span>状态</span>
        <span class="status-select">
          <select v-model="form.status">
            <option value="draft">草稿</option>
            <option value="published">发布</option>
            <option value="closed">关闭</option>
          </select>
        </span>
      </label>
      <label class="field description-field">
        <span>作业说明</span>
        <textarea v-model="form.description" rows="1" placeholder="写给学生的作业说明" />
      </label>
      <div class="meta-kpis">
        <span><strong>{{ form.questions.length }}</strong>题目</span>
        <span><strong>{{ form.student_ids.length }}</strong>学生</span>
        <span class="state">{{ assignmentStatusText(form.status) }}</span>
      </div>
    </section>

    <main class="studio-layout">
      <aside class="studio-sidebar">
        <section class="panel roster-panel">
          <div class="panel-head">
            <div>
              <h3>发布学生</h3>
              <p>{{ form.student_ids.length }} / {{ students.length }} 已选择</p>
            </div>
          </div>
          <div class="student-list">
            <label v-for="student in students" :key="student.id" class="student-item">
              <input v-model="form.student_ids" type="checkbox" :value="student.id" />
              <span>{{ student.username }}</span>
            </label>
          </div>
        </section>

        <section class="panel question-nav">
          <div class="panel-head">
            <div>
              <h3>题目目录</h3>
              <p>{{ form.questions.length }} 道题</p>
            </div>
            <button type="button" class="btn btn-primary btn-small" @click="addQuestion">新增</button>
          </div>

          <article
            v-for="(question, qIndex) in form.questions"
            :key="question.localKey"
            class="question-item"
            :class="{ active: qIndex === activeQuestionIndex }"
            @click="selectQuestion(qIndex)"
          >
            <button type="button" class="question-main">
              <span class="question-order">Q{{ qIndex + 1 }}</span>
              <span class="question-title">{{ question.title || "未命名题目" }}</span>
              <span class="question-meta">
                {{ reviewLevelText(question.ai_review_level) }} ·
                {{ question.enable_testcases ? `${question.test_cases.length} 个用例` : "无测试用例" }}
              </span>
            </button>
            <div class="question-actions">
              <button
                type="button"
                class="icon-btn"
                title="上移题目"
                :disabled="qIndex === 0"
                @click.stop="moveQuestion(qIndex, -1)"
              >
                ↑
              </button>
              <button
                type="button"
                class="icon-btn"
                title="下移题目"
                :disabled="qIndex === form.questions.length - 1"
                @click.stop="moveQuestion(qIndex, 1)"
              >
                ↓
              </button>
              <button type="button" class="icon-btn danger" title="删除题目" @click.stop="removeQuestion(qIndex)">
                ×
              </button>
            </div>
          </article>
        </section>
      </aside>

      <section class="studio-main">
        <section class="ai-draft-panel panel">
          <div class="draft-heading">
            <span class="section-index">AI</span>
            <div>
              <h3>AI 生成题目草稿</h3>
              <p>输入题目要求和知识点后，系统会追加一题草稿；生成后仍可手动调整题面、判题规则和测试用例。</p>
            </div>
          </div>
          <div class="draft-fields">
            <label class="field">
              <span>题目要求</span>
              <textarea
                v-model="generateRequirement"
                rows="5"
                placeholder="例如：设计转账事务并处理异常，要求说明事务边界、资源释放、输入输出格式和错误处理。"
              />
            </label>
            <div class="draft-bottom-row">
              <label class="field">
                <span>知识点</span>
                <input v-model="generateKnowledge" placeholder="例如：Java 事务处理、异常回滚" />
              </label>
              <button type="button" class="btn btn-primary" :disabled="generating || !generateRequirement.trim()" @click="generateQuestion">
                {{ generating ? "生成中..." : "生成题目" }}
              </button>
            </div>
          </div>
        </section>

        <section v-if="activeQuestion" class="question-workspace">
          <div class="question-summary panel">
            <div class="question-summary-title">
              <h3>{{ activeQuestion.title || "未命名题目" }}</h3>
            </div>
            <div class="summary-tags">
              <span>{{ reviewLevelText(activeQuestion.ai_review_level) }}</span>
              <span>{{ activeQuestion.enable_testcases ? `${activeQuestion.test_cases.length} 个测试用例` : "AI 独立审查" }}</span>
              <span>{{ selectedKnowledgeNodes.length }} 个知识点</span>
            </div>
          </div>

          <section class="editor-section panel">
            <div class="section-head">
              <div>
                <h4>题目内容</h4>
                <p>题面、初始代码和知识图谱绑定会直接影响学生作答与画像更新。</p>
              </div>
            </div>
            <div class="content-grid">
              <label class="field">
                <span>题目标题</span>
                <input v-model="activeQuestion.title" placeholder="例如：实现线程安全的库存扣减" />
              </label>
              <label class="field prompt-field">
                <span>题目描述</span>
                <textarea
                  v-auto-resize
                  v-model="activeQuestion.prompt"
                  class="prompt-input"
                  rows="5"
                  placeholder="题目描述、输入输出要求、实现约束、评分重点"
                />
              </label>
              <label class="field prompt-field">
                <span>初始代码</span>
                <textarea
                  v-auto-resize
                  v-model="activeQuestion.starter_code"
                  class="prompt-input code-input"
                  rows="5"
                  placeholder="学生首次打开这道题时，编辑器将默认填入这段代码；若学生已存在草稿，则不会覆盖。"
                />
              </label>
            </div>

            <div class="knowledge-block">
              <div class="section-head compact">
                <div>
                  <h4>关联知识点</h4>
                  <p>绑定已有知识图谱节点后，这道题的提交结果才会参与掌握度更新。</p>
                </div>
              </div>
              <div class="knowledge-search">
                <div class="knowledge-search-box">
                  <input
                    v-model="knowledgeNodeKeyword"
                    placeholder="输入关键词搜索图谱节点"
                    @input="handleKnowledgeNodeInput"
                    @focus="handleKnowledgeNodeInput"
                    @keydown.enter.prevent="searchKnowledgeNodes"
                  />
                  <button
                    v-if="knowledgeNodeKeyword.trim()"
                    type="button"
                    class="knowledge-clear"
                    title="清空搜索"
                    @mousedown.prevent
                    @click="resetKnowledgeNodeSearch"
                  >
                    ×
                  </button>
                  <div v-if="showKnowledgeNodeDropdown && knowledgeNodeSuggestions.length" class="knowledge-dropdown">
                    <button
                      v-for="node in knowledgeNodeSuggestions"
                      :key="node.id"
                      type="button"
                      class="knowledge-dropdown-item"
                      @mousedown.prevent="toggleKnowledgeNode(node)"
                    >
                      <strong>{{ node.node_name }}</strong>
                      <small v-if="node.match_type === 'neighbor'">相邻节点</small>
                      <small v-else>直接匹配</small>
                    </button>
                  </div>
                </div>
                <button type="button" class="btn btn-quiet" :disabled="knowledgeNodeLoading" @click="searchKnowledgeNodes()">
                  {{ knowledgeNodeLoading ? "搜索中..." : "搜索" }}
                </button>
                <button type="button" class="btn btn-quiet" @click="resetKnowledgeNodeSearch">全部</button>
              </div>
              <p v-if="knowledgeNodeKeyword.trim()" class="helper-text">
                搜索结果会包含直接命中的节点，并补充与其相连的节点。
              </p>
              <div v-if="selectedKnowledgeNodes.length" class="knowledge-tags">
                <span
                  v-for="node in selectedKnowledgeNodes"
                  :key="node.id"
                  class="knowledge-tag"
                >
                  <span class="knowledge-tag-name">
                    {{ node.node_name }}
                    <small v-if="node.match_type === 'neighbor'">相邻</small>
                  </span>
                  <button
                    type="button"
                    class="knowledge-remove"
                    :title="`移除 ${node.node_name}`"
                    @click="removeKnowledgeNode(node.id)"
                  >
                    ×
                  </button>
                </span>
              </div>
              <p v-else class="helper-text">尚未选择知识点。输入关键词后可在下拉列表里直接添加。</p>
            </div>
          </section>

          <section class="assessment-stack">
            <section class="editor-section panel grading-panel">
              <div class="section-head">
                <div>
                  <h4>AI 判题设置</h4>
                  <p>AI 默认参与判题，审查深度决定反馈严谨程度。</p>
                </div>
                <span class="pill">AI 开启</span>
              </div>

              <div class="review-level-switch">
                <button
                  type="button"
                  class="level-option"
                  :class="{ active: activeQuestion.ai_review_level === 'light' }"
                  @click="activeQuestion.ai_review_level = 'light'"
                >
                  <strong>轻审查</strong>
                  <span>适合输入输出明确、主要靠测试用例验证的练习。</span>
                </button>
                <button
                  type="button"
                  class="level-option"
                  :class="{ active: activeQuestion.ai_review_level === 'deep' }"
                  @click="activeQuestion.ai_review_level = 'deep'"
                >
                  <strong>深审查</strong>
                  <span>适合事务、并发、资源释放、设计约束较强的题目。</span>
                </button>
              </div>

              <label class="field">
                <span>评分标准</span>
                <textarea
                  v-model="activeQuestion.ai_grading_rubric"
                  rows="6"
                  placeholder="例如：重点检查事务边界、异常处理、资源释放，以及是否满足题目业务约束"
                />
              </label>

              <div class="focus-block">
                <div class="section-head compact">
                  <div>
                    <h4>AI 关注点</h4>
                    <p>教师可手动填写，也可以让 AI 根据题目自动补全。</p>
                  </div>
                  <button
                    type="button"
                    class="btn btn-quiet"
                    :disabled="focusGenerating || !canGenerateFocus(activeQuestion)"
                    @click="generateFocus(activeQuestion)"
                  >
                    {{ focusGenerating ? "生成中..." : "AI 生成" }}
                  </button>
                </div>
                <label class="field">
                  <span>关注点输入</span>
                  <input
                    v-model="activeQuestion.ai_grading_focus_text"
                    placeholder="例如：事务边界, 异常处理, 资源释放"
                  />
                </label>
                <p class="helper-text">{{ activeQuestion.focus_summary || "系统会结合题目内容和教师要求，引导 AI 审查代码重点。" }}</p>
              </div>
            </section>

            <section class="editor-section panel testcase-panel">
              <div class="section-head">
                <div>
                  <h4>测试用例</h4>
                  <p>显式验证功能正确性；关闭后会更依赖 AI 审查。</p>
                </div>
                <label class="switch">
                  <input v-model="activeQuestion.enable_testcases" type="checkbox" />
                  <span>启用</span>
                </label>
              </div>

              <transition name="fade-slide">
                <div v-if="activeQuestion.enable_testcases" class="testcase-body">
                  <div class="testcase-actions">
                    <button
                      type="button"
                      class="btn btn-quiet"
                      :disabled="testcaseGenerating || !canGenerateTestCases(activeQuestion)"
                      @click="generateTestCases(activeQuestion)"
                    >
                      {{ testcaseGenerating ? "生成中..." : "AI 生成测试用例" }}
                    </button>
                    <button type="button" class="btn btn-primary" @click="addTestCase(activeQuestion)">新增用例</button>
                  </div>

                  <article
                    v-for="(testCase, cIndex) in activeQuestion.test_cases"
                    :key="testCase.localKey"
                    class="case-card"
                  >
                    <div class="case-title">
                      <strong>用例 {{ cIndex + 1 }}</strong>
                      <label class="sample-check">
                        <input v-model="testCase.is_sample" type="checkbox" />
                        <span>示例</span>
                      </label>
                    </div>
                    <div class="case-fields">
                      <label class="field">
                        <span>输入</span>
                        <textarea v-model="testCase.input_data" rows="4" placeholder="stdin 输入" />
                      </label>
                      <label class="field">
                        <span>期望输出</span>
                        <textarea v-model="testCase.expected_output" rows="4" placeholder="期望 stdout" />
                      </label>
                    </div>
                    <div class="case-footer">
                      <button type="button" class="btn btn-danger" @click="removeTestCase(activeQuestion, cIndex)">删除用例</button>
                    </div>
                  </article>
                </div>
              </transition>

              <p v-if="!activeQuestion.enable_testcases" class="helper-text">
                当前题目未启用测试用例，保存时不会提交用例列表。
              </p>
            </section>
          </section>
        </section>

        <section v-else class="empty-editor panel">
          <strong>还没有题目</strong>
          <p>先新增一道题目，或用 AI 生成题目草稿。</p>
          <button type="button" class="btn btn-primary" @click="addQuestion">新增题目</button>
        </section>
      </section>
    </main>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
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
import { listTeacherKnowledgeNodesApi, listTeacherStudentsApi } from "../api/teacher";
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
const knowledgeNodeOptions = ref([]);
const allKnowledgeNodeOptions = ref([]);
const knowledgeNodeKeyword = ref("");
const knowledgeNodeLoading = ref(false);
const showKnowledgeNodeDropdown = ref(false);
const form = ref({
  title: "",
  description: "",
  status: "draft",
  student_ids: [],
  questions: [],
});

const activeQuestion = computed(() => form.value.questions[activeQuestionIndex.value] || null);
const displayKnowledgeNodeOptions = computed(() => {
  const selectedIds = new Set((activeQuestion.value?.knowledge_node_ids || []).map(Number));
  const merged = new Map();
  for (const node of knowledgeNodeOptions.value) {
    merged.set(Number(node.id), node);
  }
  for (const node of allKnowledgeNodeOptions.value) {
    if (selectedIds.has(Number(node.id))) {
      merged.set(Number(node.id), node);
    }
  }
  return [...merged.values()];
});
const knowledgeNodeSuggestions = computed(() => displayKnowledgeNodeOptions.value.slice(0, 12));
const selectedKnowledgeNodes = computed(() => {
  const selectedIds = new Set((activeQuestion.value?.knowledge_node_ids || []).map(Number));
  return [...new Map(allKnowledgeNodeOptions.value.map((node) => [Number(node.id), node])).values()]
    .filter((node) => selectedIds.has(Number(node.id)));
});
let knowledgeNodeSuggestTimer = null;

const vAutoResize = {
  mounted(element) {
    element.addEventListener("input", resizeTextarea);
    resizeTextarea({ target: element });
  },
  updated(element) {
    nextTick(() => resizeTextarea({ target: element }));
  },
  beforeUnmount(element) {
    element.removeEventListener("input", resizeTextarea);
  },
};

onMounted(async () => {
  await loadStudents();
  await loadKnowledgeNodes();
  if (!isNew.value) {
    await loadAssignment();
  } else {
    addQuestion();
  }
});

function resizeTextarea(event) {
  const element = event?.target;
  if (!element) return;
  element.style.height = "auto";
  element.style.height = `${element.scrollHeight}px`;
}

async function loadStudents() {
  try {
    const { data } = await listTeacherStudentsApi();
    students.value = data;
  } catch (error) {
    handleApiError(error, "加载学生失败。");
  }
}

async function loadKnowledgeNodes() {
  knowledgeNodeLoading.value = true;
  try {
    const { data } = await listTeacherKnowledgeNodesApi({ limit: 200 });
    knowledgeNodeOptions.value = data || [];
    allKnowledgeNodeOptions.value = data || [];
  } catch (error) {
    handleApiError(error, "加载知识图谱节点失败。");
  } finally {
    knowledgeNodeLoading.value = false;
  }
}

function handleKnowledgeNodeInput() {
  if (knowledgeNodeSuggestTimer) clearTimeout(knowledgeNodeSuggestTimer);
  const query = knowledgeNodeKeyword.value.trim();
  if (!query) {
    knowledgeNodeOptions.value = allKnowledgeNodeOptions.value;
    showKnowledgeNodeDropdown.value = false;
    return;
  }
  knowledgeNodeSuggestTimer = setTimeout(() => {
    searchKnowledgeNodes(query);
  }, 180);
}

async function searchKnowledgeNodes(queryOverride = "") {
  const query = (queryOverride || knowledgeNodeKeyword.value).trim();
  if (!query) {
    knowledgeNodeOptions.value = allKnowledgeNodeOptions.value;
    showKnowledgeNodeDropdown.value = false;
    return;
  }
  knowledgeNodeLoading.value = true;
  try {
    const { data } = await listTeacherKnowledgeNodesApi({
      keyword: query,
      include_neighbors: true,
      limit: 200,
    });
    knowledgeNodeOptions.value = data || [];
    for (const node of data || []) {
      if (!allKnowledgeNodeOptions.value.some((item) => Number(item.id) === Number(node.id))) {
        allKnowledgeNodeOptions.value.push(node);
      }
    }
    showKnowledgeNodeDropdown.value = knowledgeNodeOptions.value.length > 0;
  } catch (error) {
    handleApiError(error, "搜索知识图谱节点失败。");
    showKnowledgeNodeDropdown.value = false;
  } finally {
    knowledgeNodeLoading.value = false;
  }
}

function resetKnowledgeNodeSearch() {
  knowledgeNodeKeyword.value = "";
  knowledgeNodeOptions.value = allKnowledgeNodeOptions.value;
  showKnowledgeNodeDropdown.value = false;
}

function toggleKnowledgeNode(node) {
  if (!activeQuestion.value) return;
  const nodeId = Number(node.id);
  const selected = new Set((activeQuestion.value.knowledge_node_ids || []).map(Number));
  if (selected.has(nodeId)) {
    showKnowledgeNodeDropdown.value = false;
    return;
  } else {
    activeQuestion.value.knowledge_node_ids = [...activeQuestion.value.knowledge_node_ids, nodeId];
    showKnowledgeNodeDropdown.value = false;
  }
  if (!allKnowledgeNodeOptions.value.some((item) => Number(item.id) === nodeId)) {
    allKnowledgeNodeOptions.value.push(node);
  }
}

function removeKnowledgeNode(nodeId) {
  if (!activeQuestion.value) return;
  activeQuestion.value.knowledge_node_ids = activeQuestion.value.knowledge_node_ids.filter((id) => Number(id) !== Number(nodeId));
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
    knowledge_node_ids: Array.isArray(question.knowledge_node_ids) ? question.knowledge_node_ids.map(Number) : [],
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
      knowledge_node_ids: source.knowledge_node_ids || [],
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
      knowledge_node_ids: (question.knowledge_node_ids || []).map(Number),
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

function assignmentStatusText(value) {
  return { draft: "草稿", published: "发布中", closed: "已关闭" }[value] || value;
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
  --editor-accent: var(--app-primary);
  --editor-accent-strong: var(--app-primary-deep);
  --editor-accent-soft: var(--app-primary-soft);
  --editor-border: var(--app-line);
  --editor-border-strong: var(--app-line-strong);
  --editor-surface: var(--app-panel);
  --editor-soft: var(--app-panel-soft);
  --editor-text: var(--app-text);
  --editor-muted: var(--app-text-muted);
  --editor-danger: var(--app-danger);
  --editor-success: var(--app-success);
  display: grid;
  gap: 20px;
}

.panel,
.feedback {
  border: 1px solid var(--editor-border);
  border-radius: var(--app-radius-xl);
  background: var(--editor-surface);
  box-shadow: var(--app-shadow);
}

.editor-hero,
.hero-actions,
.panel-head,
.section-head,
.summary-tags,
.testcase-actions,
.case-title {
  display: flex;
  align-items: center;
  gap: 14px;
}

.editor-hero {
  justify-content: space-between;
  gap: 18px;
}

.hero-copy {
  min-width: 0;
}

.eyebrow {
  display: inline-flex;
  margin-bottom: 8px;
  color: #60748a;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.editor-hero h2 {
  margin: 0 0 8px;
  color: var(--editor-text);
  font-size: 32px;
  line-height: 1.08;
  font-weight: 500;
}

.editor-hero p,
.panel-head p,
.section-head p,
.helper-text,
.empty-editor p {
  margin: 0;
  color: var(--editor-muted);
  line-height: 1.65;
}

.hero-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.meta-strip {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) 180px minmax(320px, 1.1fr) auto;
  gap: 14px;
  align-items: end;
  padding: 16px;
  border: 1px solid var(--editor-border);
  border-radius: var(--app-radius-xl);
  background: rgba(255, 255, 255, 0.86);
  box-shadow: var(--app-shadow);
}

.field {
  display: grid;
  gap: 8px;
  align-content: start;
  color: #34495f;
  font-size: 14px;
  font-weight: 500;
}

.field span {
  color: #53687e;
}

.meta-kpis {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  justify-content: flex-end;
  min-height: 78px;
  min-width: 260px;
  flex-wrap: wrap;
}

.meta-kpis span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid #dfe7f1;
  border-radius: 999px;
  background: #fff;
  color: #50657a;
  font-size: 13px;
}

.meta-kpis strong {
  color: var(--editor-text);
  font-size: 18px;
  font-weight: 600;
}

.meta-kpis .state {
  background: var(--editor-accent-soft);
  color: var(--editor-accent-strong);
  border-color: #cfe0ff;
}

.status-select {
  position: relative;
  display: block;
}

.status-select::after {
  content: "";
  position: absolute;
  right: 16px;
  top: 50%;
  width: 8px;
  height: 8px;
  border-right: 2px solid #49657f;
  border-bottom: 2px solid #49657f;
  pointer-events: none;
  transform: translateY(-65%) rotate(45deg);
}

.status-select select {
  height: 44px;
  appearance: none;
  padding-right: 42px;
  background: #fff;
  color: var(--editor-text);
  font-weight: 500;
}

.studio-layout {
  display: grid;
  grid-template-columns: 318px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.studio-sidebar,
.studio-main,
.question-workspace {
  display: grid;
  gap: 18px;
}

.studio-sidebar {
  position: sticky;
  top: 16px;
}

.roster-panel,
.question-nav,
.ai-draft-panel,
.question-summary,
.editor-section,
.empty-editor {
  padding: 22px;
}

.panel-head,
.section-head {
  justify-content: space-between;
  align-items: flex-start;
}

.panel-head h3,
.section-head h4,
.ai-draft-panel h3,
.question-summary h3,
.empty-editor strong {
  margin: 0;
  color: var(--editor-text);
  font-weight: 600;
}

.panel-head h3,
.ai-draft-panel h3 {
  font-size: 22px;
  font-weight: 500;
}

.section-head h4 {
  font-size: 22px;
  font-weight: 500;
}

.student-list {
  display: grid;
  gap: 8px;
  max-height: 232px;
  margin-top: 14px;
  overflow: auto;
}

.student-item {
  display: flex;
  align-items: center;
  gap: 9px;
  min-height: 38px;
  padding: 8px 10px;
  border: 1px solid #e5edf5;
  border-radius: var(--app-radius-md);
  background: var(--editor-soft);
  color: #31445f;
  font-size: 14px;
  font-weight: 500;
}

.question-nav {
  display: grid;
  gap: 8px;
}

.question-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  padding: 10px;
  border: 1px solid #e3ebf4;
  border-radius: var(--app-radius-lg);
  background: #fff;
  cursor: pointer;
}

.question-item:hover {
  border-color: #bdd1e8;
  background: #fbfdff;
}

.question-item.active {
  border-color: var(--editor-accent);
  background: var(--editor-accent-soft);
  box-shadow: none;
}

.question-item.active .question-order,
.question-item.active .question-title {
  color: var(--editor-accent-strong);
}

.question-main {
  display: grid;
  gap: 4px;
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.question-order {
  color: var(--editor-accent);
  font-size: 12px;
  font-weight: 700;
}

.question-title {
  min-width: 0;
  overflow: hidden;
  color: var(--editor-text);
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.question-meta {
  color: var(--editor-muted);
  font-size: 12px;
}

.question-actions {
  display: grid;
  grid-template-columns: repeat(3, 28px);
  gap: 4px;
  align-content: start;
}

.ai-draft-panel {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
  align-items: start;
  background:
    radial-gradient(circle at 100% 0%, rgba(47, 103, 246, 0.08), transparent 32%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.draft-heading {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.section-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: var(--app-radius-md);
  background: var(--editor-accent);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}

.draft-fields {
  display: grid;
  gap: 14px;
  width: 100%;
}

.draft-bottom-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 14px;
  align-items: end;
}

.draft-bottom-row .btn {
  min-width: 132px;
}

.question-summary {
  justify-content: space-between;
  display: flex;
  gap: 16px;
  align-items: center;
}

.question-summary-title {
  flex: 1;
  min-width: 0;
  text-align: left;
}

.question-summary h3 {
  margin: 0;
  font-size: 26px;
  font-weight: 500;
}

.summary-tags {
  flex-wrap: wrap;
  justify-content: center;
  align-self: center;
}

.summary-tags span,
.pill {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid #d8e5f3;
  background: #f4f8fd;
  color: #49627c;
  font-size: 12px;
  font-weight: 600;
}

.pill {
  background: #ecfdf3;
  border-color: #cce7d8;
  color: var(--editor-success);
}

.editor-section {
  display: grid;
  gap: 18px;
}

.content-grid {
  display: grid;
  gap: 12px;
}

.assessment-stack {
  display: grid;
  gap: 18px;
}

.knowledge-block,
.focus-block,
.testcase-body {
  display: grid;
  gap: 14px;
  padding-top: 2px;
}

.knowledge-search {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 10px;
  align-items: start;
}

.knowledge-search-box {
  position: relative;
}

.knowledge-search-box input {
  padding-right: 44px;
}

.knowledge-clear {
  position: absolute;
  right: 10px;
  top: 50%;
  z-index: 2;
  min-width: 26px;
  min-height: 26px;
  padding: 0;
  border-radius: 50%;
  border-color: #d8e5f3;
  background: #f7fafc;
  color: #66788b;
  font-size: 16px;
  line-height: 1;
  transform: translateY(-50%);
}

.knowledge-clear:hover:not(:disabled) {
  background: #eef5ff;
  color: var(--editor-accent-strong);
  box-shadow: none;
  transform: translateY(-50%);
}

.knowledge-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  z-index: 10;
  display: grid;
  gap: 6px;
  max-height: 280px;
  padding: 8px;
  overflow-y: auto;
  border: 1px solid var(--editor-border);
  border-radius: var(--app-radius-lg);
  background: #fff;
  box-shadow: 0 16px 34px rgba(20, 34, 53, 0.12);
}

.knowledge-dropdown-item {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  min-height: 40px;
  padding: 8px 10px;
  border: 1px solid #e3ebf4;
  border-radius: var(--app-radius-md);
  background: #fff;
  color: #29455f;
  text-align: left;
}

.knowledge-dropdown-item:hover {
  border-color: #9bbdf2;
  background: var(--editor-accent-soft);
}

.knowledge-dropdown-item small {
  color: var(--editor-muted);
  white-space: nowrap;
}

.knowledge-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.knowledge-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  padding: 0 6px 0 10px;
  border: 1px solid #cfe0ff;
  border-radius: 999px;
  background: var(--editor-accent-soft);
  color: #2454a6;
  font-weight: 500;
}

.knowledge-tag-name {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.knowledge-tag small {
  color: #60748a;
}

.knowledge-remove {
  min-width: 24px;
  min-height: 24px;
  padding: 0;
  border-radius: 50%;
  border-color: #bfd3f5;
  background: #fff;
  color: #37659f;
  font-size: 16px;
  line-height: 1;
}

.knowledge-remove:hover:not(:disabled) {
  background: #e7f0ff;
  box-shadow: none;
  transform: none;
}

.review-level-switch {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.level-option {
  display: grid;
  gap: 8px;
  justify-items: start;
  min-height: 96px;
  padding: 16px;
  border: 1px solid #dbe5f0;
  border-radius: var(--app-radius-lg);
  background: #fff;
  color: var(--editor-text);
}

.level-option strong {
  font-size: 16px;
  font-weight: 500;
}

.level-option span {
  color: var(--editor-muted);
  font-size: 13px;
  line-height: 1.45;
}

.level-option.active {
  border-color: var(--editor-accent);
  background: var(--editor-accent-soft);
  box-shadow: none;
}

.level-option.active strong {
  color: var(--editor-accent-strong);
}

.level-option.active span {
  color: #37659f;
}

.switch,
.sample-check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #35495e;
  font-weight: 600;
}

.switch {
  min-height: 34px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid #dfe7f1;
  background: #fff;
  font-size: 13px;
}

.switch input,
.student-item input,
.sample-check input {
  width: auto;
}

.testcase-actions {
  justify-content: flex-end;
  flex-wrap: wrap;
}

.case-card {
  display: grid;
  gap: 14px;
  padding: 16px 18px;
  border: 1px solid #e3ebf4;
  border-radius: var(--app-radius-lg);
  background: var(--editor-soft);
}

.case-title {
  justify-content: space-between;
}

.case-title strong {
  color: var(--editor-text);
  font-weight: 500;
}

.case-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.case-footer {
  display: flex;
  justify-content: flex-end;
}

input,
textarea,
select {
  width: 100%;
  min-height: 44px;
  padding: 12px 14px;
  border: 1px solid var(--editor-border);
  border-radius: var(--app-radius-md);
  color: #12263a;
  background: #fff;
  font: inherit;
}

input:focus,
textarea:focus,
select:focus {
  outline: none;
  border-color: #9bbdf2;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.1);
}

textarea {
  resize: none;
}

.description-field textarea {
  height: 44px;
  min-height: 44px;
  overflow: hidden;
}

.prompt-input,
.case-row textarea {
  font-family: Consolas, "Courier New", monospace;
}

.prompt-input {
  min-height: 150px;
  overflow: hidden;
}

.prompt-input.code-input {
  min-height: 140px;
}

.btn,
.icon-btn,
button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 0 14px;
  border: 1px solid var(--editor-border);
  border-radius: var(--app-radius-md);
  background: #fff;
  color: #18344f;
  cursor: pointer;
  text-decoration: none;
  white-space: nowrap;
}

.btn:hover:not(:disabled),
.icon-btn:hover:not(:disabled),
button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 10px 20px rgba(20, 34, 53, 0.08);
}

.btn-primary {
  background: var(--editor-accent);
  border-color: var(--editor-accent);
  color: #fff;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.18);
}

.btn-primary:hover:not(:disabled) {
  background: var(--editor-accent-strong);
  border-color: var(--editor-accent-strong);
}

.btn-quiet {
  background: #f7fafc;
  color: #31445f;
}

.btn-danger {
  width: fit-content;
  min-height: 36px;
  border-color: #efcaca;
  background: #fff5f5;
  color: var(--editor-danger);
}

.btn-small {
  min-height: 34px;
  padding: 0 10px;
}

.icon-btn {
  min-width: 28px;
  min-height: 28px;
  padding: 0;
  border-radius: 10px;
  color: #4a627a;
  font-size: 13px;
}

.icon-btn.danger {
  border-color: #efcaca;
  background: #fff5f5;
  color: var(--editor-danger);
}

button:disabled,
.btn:disabled {
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
  color: var(--editor-text);
  font-size: 22px;
  font-weight: 600;
}

.feedback {
  padding: 12px 14px;
}

.feedback.error {
  color: var(--editor-danger);
  background: #fff8f8;
  border-color: #efcaca;
}

.feedback.success {
  color: var(--editor-success);
  background: #ecfdf3;
  border-color: #cce7d8;
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
  .meta-strip,
  .studio-layout,
  .ai-draft-panel,
  .draft-fields,
  .knowledge-search {
    grid-template-columns: 1fr;
  }

  .meta-kpis,
  .summary-tags {
    justify-content: center;
    min-width: 0;
  }

  .studio-sidebar {
    position: static;
  }
}

@media (max-width: 760px) {
  .editor-hero,
  .hero-actions,
  .panel-head,
  .section-head,
  .question-summary,
  .testcase-actions,
  .case-title {
    display: grid;
    justify-content: stretch;
  }

  .hero-actions > *,
  .draft-fields > *,
  .draft-bottom-row > *,
  .testcase-actions > *,
  .knowledge-search > * {
    width: 100%;
  }

  .editor-hero h2 {
    font-size: 28px;
  }

  .question-item {
    grid-template-columns: 1fr;
  }

  .question-actions {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .draft-bottom-row,
  .review-level-switch {
    grid-template-columns: 1fr;
  }

  .case-fields {
    grid-template-columns: 1fr;
  }

  .roster-panel,
  .question-nav,
  .ai-draft-panel,
  .question-summary,
  .editor-section,
  .empty-editor {
    padding: 18px;
  }
}
</style>
