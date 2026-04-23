<template>
  <section class="editor-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Assignment Studio</p>
        <h2>{{ isNew ? "新建作业" : "编辑作业" }}</h2>
        <p class="page-copy">AI 默认参与判题，测试用例按题目需要启用。</p>
      </div>
    </header>

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

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>
    <p v-if="successMessage" class="feedback success">{{ successMessage }}</p>

    <section class="assignment-meta shell-card">
      <div class="meta-banner">
        <div class="meta-banner-copy">
          <p class="meta-kicker">Assignment Blueprint</p>
          <h3>作业基础信息</h3>
          <p>先确定标题、状态和说明，再继续配置题目、知识点和 AI 判题规则。</p>
        </div>
        <div class="meta-glance">
          <span class="meta-chip">{{ form.questions.length }} 题</span>
          <span class="meta-chip">{{ form.student_ids.length }} 名学生</span>
          <span class="meta-chip status">{{ assignmentStatusText(form.status) }}</span>
        </div>
      </div>
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
              <button
                type="button"
                class="icon-action"
                title="上移题目"
                :disabled="qIndex === 0"
                @click.stop="moveQuestion(qIndex, -1)"
              >
                ↑
              </button>
              <button
                type="button"
                class="icon-action"
                title="下移题目"
                :disabled="qIndex === form.questions.length - 1"
                @click.stop="moveQuestion(qIndex, 1)"
              >
                ↓
              </button>
              <button type="button" class="icon-action danger-action" title="删除题目" @click.stop="removeQuestion(qIndex)">
                ×
              </button>
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
              <div class="knowledge-card">
                <div class="card-heading compact-heading">
                  <div>
                    <h5>关联知识点</h5>
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
                    <div v-if="showKnowledgeNodeDropdown && knowledgeNodeSuggestions.length" class="knowledge-dropdown">
                      <button
                        v-for="node in knowledgeNodeSuggestions"
                        :key="node.id"
                        type="button"
                        class="knowledge-dropdown-item"
                        @mousedown.prevent="toggleKnowledgeNode(node)"
                      >
                        <strong>{{ node.node_name }}</strong>
                        <span>
                          <small v-if="node.match_type === 'neighbor'">相邻节点</small>
                          <small v-else>直接匹配</small>
                        </span>
                      </button>
                    </div>
                  </div>
                  <button type="button" :disabled="knowledgeNodeLoading" @click="searchKnowledgeNodes()">
                    {{ knowledgeNodeLoading ? "搜索中..." : "搜索" }}
                  </button>
                  <button type="button" class="ghost-btn" @click="resetKnowledgeNodeSearch">全部</button>
                </div>
                <p v-if="knowledgeNodeKeyword.trim()" class="helper-text">
                  搜索结果会包含直接命中的节点，并补充与其相连的节点，便于一起绑定。
                </p>
                <div v-if="selectedKnowledgeNodes.length" class="knowledge-grid">
                  <button
                    v-for="node in selectedKnowledgeNodes"
                    :key="node.id"
                    type="button"
                    class="knowledge-check selected"
                    @click="toggleKnowledgeNode(node)"
                  >
                    <span>
                      {{ node.node_name }}
                      <small v-if="node.match_type === 'neighbor'">相邻节点</small>
                    </span>
                  </button>
                </div>
                <p v-else class="helper-text">尚未选择知识点。输入关键词后可在下拉列表里直接添加。</p>
              </div>
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

onMounted(async () => {
  await loadStudents();
  await loadKnowledgeNodes();
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
    activeQuestion.value.knowledge_node_ids = activeQuestion.value.knowledge_node_ids.filter((id) => Number(id) !== nodeId);
  } else {
    activeQuestion.value.knowledge_node_ids = [...activeQuestion.value.knowledge_node_ids, nodeId];
  }
  if (!allKnowledgeNodeOptions.value.some((item) => Number(item.id) === nodeId)) {
    allKnowledgeNodeOptions.value.push(node);
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
  --editor-accent: #2b6cb0;
  --editor-accent-soft: #edf4ff;
  --editor-border: #dfe8f2;
  --editor-surface: rgba(255, 255, 255, 0.94);
  --editor-text: #10283d;
  --editor-muted: #6f8297;
  display: grid;
  gap: 18px;
}

.shell-card,
.feedback {
  border: 1px solid var(--editor-border);
  border-radius: 28px;
  background: var(--editor-surface);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.06);
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

.page-header h2 {
  margin: 10px 0 8px;
  color: #0f2840;
  font-size: 32px;
  font-weight: 500;
}

.page-copy,
.panel-title p,
.card-heading p,
.helper-text,
.empty-editor p {
  margin: 0;
  color: var(--editor-muted);
}

.eyebrow {
  margin: 0;
  color: #6e86a6;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.toolbar-actions {
  width: fit-content;
  max-width: 100%;
  margin-left: auto;
  justify-content: flex-end;
  flex-wrap: wrap;
  padding: 8px;
  border: 1px solid var(--editor-border);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.04);
}

.assignment-meta {
  display: grid;
  grid-template-columns: minmax(240px, 1.1fr) 180px minmax(360px, 1.25fr);
  gap: 16px;
  padding: 22px;
  overflow: hidden;
  position: relative;
}

.assignment-meta::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at top right, rgba(67, 123, 194, 0.12), transparent 34%),
    linear-gradient(180deg, rgba(244, 249, 255, 0.66), rgba(255, 255, 255, 0));
  pointer-events: none;
}

.meta-banner {
  grid-column: 1 / -1;
  position: relative;
  z-index: 1;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.meta-banner-copy {
  display: grid;
  gap: 8px;
}

.meta-kicker {
  margin: 0;
  color: var(--editor-accent);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.meta-banner-copy h3 {
  margin: 0;
  color: var(--editor-text);
  font-size: 24px;
  font-weight: 500;
}

.meta-banner-copy p {
  margin: 0;
  max-width: 640px;
  color: var(--editor-muted);
  line-height: 1.7;
}

.meta-glance {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid #d8e6f5;
  background: rgba(255, 255, 255, 0.88);
  color: #49657f;
  font-size: 13px;
}

.meta-chip.status {
  border-color: #cfe0f2;
  background: var(--editor-accent-soft);
  color: var(--editor-accent);
}

.assignment-meta > label {
  position: relative;
  z-index: 1;
  padding: 16px 18px;
  border: 1px solid #e6edf6;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.88);
}

.editor-workbench {
  display: grid;
  grid-template-columns: 330px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.editor-sidebar,
.editor-main,
.question-editor {
  display: grid;
  gap: 18px;
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
  padding: 22px;
  border: 1px solid #e6edf6;
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
  color: var(--editor-text);
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
  padding: 11px 13px;
  border: 1px solid #e7eef7;
  border-radius: 16px;
  background: #fbfdff;
}

.question-index {
  gap: 12px;
}

.question-index .panel-title {
  align-items: flex-start;
}

.question-tab {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  padding: 14px;
  border: 1px solid #deebf7;
  border-radius: 18px;
  background: #fff;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.question-tab:hover {
  transform: translateY(-1px);
  border-color: #b7d2ec;
  box-shadow: 0 14px 28px rgba(30, 99, 167, 0.08);
}

.question-tab.active {
  border-color: #8cbce7;
  background: linear-gradient(180deg, #fbfdff, #f1f7ff);
  box-shadow: inset 0 0 0 1px rgba(140, 188, 231, 0.22);
}

.question-tab-copy {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.question-tab-copy span {
  color: #708294;
  font-size: 12px;
}

.question-tab-copy strong {
  color: var(--editor-text);
  font-weight: 500;
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
  color: var(--editor-accent);
  font-size: 12px;
  font-weight: 500;
}

.badge.subtle {
  background: #eef2f6;
  color: #5f7284;
}

.status-chip {
  background: linear-gradient(135deg, #143450, #285f90);
  color: #fff;
}

.question-tab-actions {
  display: grid;
  gap: 6px;
  align-content: start;
}

.question-tab-actions button {
  min-width: 36px;
  min-height: 36px;
  padding: 0;
  border-radius: 12px;
}

.icon-action {
  border-color: #d9e6f4;
  background: #f8fbff;
  color: #365879;
  font-size: 16px;
  line-height: 1;
  box-shadow: none;
}

.icon-action:hover:not(:disabled) {
  background: #eef5fd;
  border-color: #c8dff4;
}

.danger-action {
  color: #b42318;
  background: #fff7f6;
  border-color: #f3d0cc;
}

.danger-action:hover:not(:disabled) {
  background: #fdeceb;
  border-color: #efc0ba;
}

.idea-panel {
  display: grid;
  gap: 14px;
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(circle at top right, rgba(64, 136, 222, 0.12), transparent 34%),
    linear-gradient(180deg, rgba(248, 251, 255, 0.96), rgba(255, 255, 255, 0.94));
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
    linear-gradient(135deg, rgba(247, 251, 255, 0.98), rgba(255, 255, 255, 0.92));
  border-color: #dbe8f5;
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
  border: 1px solid #dbe7f3;
  border-radius: 20px;
  background: #fff;
  color: #163552;
}

.level-btn small {
  color: #66788a;
}

.level-btn.active {
  border-color: #79b0e1;
  background: #f6fbff;
  box-shadow: inset 0 0 0 1px rgba(121, 176, 225, 0.18);
}

.focus-card,
.testcase-body {
  display: grid;
  gap: 12px;
  padding-top: 4px;
}

.knowledge-card {
  display: grid;
  gap: 12px;
  padding: 16px;
  border-radius: 22px;
  background: linear-gradient(180deg, #f9fbfe, #f4f8fd);
  border: 1px solid #dde8f3;
}

.compact-heading {
  align-items: flex-start;
}

.knowledge-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}

.knowledge-search {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 10px;
}

.knowledge-search-box {
  position: relative;
}

.knowledge-search input {
  width: 100%;
  padding: 11px 12px;
  border: 1px solid #d8e2ee;
  border-radius: 14px;
  background: #fff;
  font: inherit;
}

.knowledge-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  z-index: 6;
  display: grid;
  gap: 6px;
  max-height: 280px;
  padding: 8px;
  overflow-y: auto;
  border: 1px solid #dce8f5;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.12);
}

.knowledge-dropdown-item {
  display: grid;
  gap: 5px;
  padding: 10px 12px;
  text-align: left;
  justify-items: start;
  justify-content: start;
  border: 1px solid #deebf7;
  border-radius: 14px;
  background: #fff;
  color: #234462;
}

.knowledge-dropdown-item span {
  display: flex;
  gap: 6px;
}

.knowledge-dropdown-item:hover {
  background: #1e63a7;
  color: #fff;
}

.knowledge-dropdown-item:hover small {
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
}

.knowledge-check {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  padding: 10px 12px;
  border-radius: 16px;
  background: #fff;
  border: 1px solid #deebf7;
  color: #234462;
}

.knowledge-check.selected {
  cursor: pointer;
}

.knowledge-check span {
  display: grid;
  gap: 3px;
}

.knowledge-check small {
  width: fit-content;
  padding: 2px 7px;
  border-radius: 999px;
  background: #eef5fd;
  color: #5f7284;
  font-size: 11px;
}

.switch {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 999px;
  border: 1px solid #e1ebf5;
  background: #f8fbff;
  font-weight: 500;
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
  padding: 12px 14px;
  border: 1px solid var(--editor-border);
  border-radius: 16px;
  color: #12263a;
  background: rgba(255, 255, 255, 0.98);
  font: inherit;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}

input:focus,
textarea:focus,
select:focus {
  outline: none;
  border-color: #8cbce7;
  box-shadow: 0 0 0 4px rgba(122, 176, 244, 0.14);
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
  border-radius: 22px;
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
  font-weight: 500;
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
  border-radius: 16px;
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
  background: linear-gradient(135deg, #2f67f6, #6f96ff);
  border-color: #2f67f6;
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
  color: var(--editor-text);
  font-size: 22px;
  font-weight: 500;
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

  .meta-banner {
    display: grid;
  }

  .meta-glance {
    justify-content: flex-start;
  }

  .editor-sidebar {
    position: static;
  }
}

@media (max-width: 760px) {
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
