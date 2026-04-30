const QUESTION_TYPES = ["multiple_choice", "fill_blank", "programming"];

export const questionFilterTabs = [
  { value: "all", label: "全部" },
  { value: "multiple_choice", label: "选择题" },
  { value: "fill_blank", label: "填空题" },
  { value: "programming", label: "编程题" },
];

export const questionTypeTabs = questionFilterTabs.slice(1);

function createLocalKey(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function questionTypeText(value) {
  return { multiple_choice: "选择题", fill_blank: "填空题", programming: "编程题" }[value] || "编程题";
}

export function normalizeQuestionType(value) {
  return QUESTION_TYPES.includes(value) ? value : "programming";
}

export function normalizeOptions(options = []) {
  if (!Array.isArray(options) || !options.length) return [];
  return options.map((item, index) => ({
    key: item.key || String.fromCharCode(65 + index),
    text: item.text || "",
    localKey: item.localKey || createLocalKey(`o-${index}`),
  }));
}

export function normalizeAnswer(answer, questionType) {
  if (questionType === "multiple_choice") return Array.isArray(answer) ? answer[0] : (answer || "A");
  if (questionType === "fill_blank") return Array.isArray(answer) ? answer : (answer || "");
  return null;
}

export function createEmptyTestCase(sortOrder = 0) {
  return {
    localKey: createLocalKey("c"),
    input_data: "",
    expected_output: "",
    is_sample: true,
    sort_order: sortOrder,
  };
}

export function normalizeQuestionByType(question) {
  if (question.question_type === "multiple_choice" && !question.options.length) {
    question.options = ["A", "B", "C", "D"].map((key) => ({ key, text: "", localKey: createLocalKey(`o-${key}`) }));
    question.answer = "A";
  }
  if (question.question_type === "fill_blank") {
    question.options = [];
    question.grading_mode = "ai_review";
  }
  if (question.question_type === "programming") {
    question.answer = null;
    question.answer_text = "";
    if (!question.test_cases.length) question.test_cases.push(createEmptyTestCase(0));
  }
}

export function normalizeQuestion(question = {}) {
  const questionType = normalizeQuestionType(question.question_type);
  const normalized = {
    id: question.id,
    localKey: question.id || createLocalKey("q"),
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
      localKey: item.id || createLocalKey(`c-${index}`),
      input_data: item.input_data || "",
      expected_output: item.expected_output || "",
      is_sample: item.is_sample !== false,
      sort_order: item.sort_order || index,
    })),
  };
  normalizeQuestionByType(normalized);
  return normalized;
}

export function hasQuestionContent(question) {
  return Boolean(question.title?.trim() && question.prompt?.trim());
}

export function toQuestionPayload(question, index = 0) {
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

export function toDatetimeLocal(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60000).toISOString().slice(0, 16);
}

export function fromDatetimeLocal(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}
