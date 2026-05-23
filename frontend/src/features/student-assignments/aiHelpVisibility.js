const ASSIGNMENT_AI_HELP_ERROR_STATUSES = new Set([
  "wrong_answer",
  "runtime_error",
  "timeout",
  "sandbox_error",
  "ai_rejected",
  "teacher_rejected",
]);

export function shouldShowAssignmentAiHelp(question, result) {
  const questionType = question?.question_type || "programming";
  return questionType === "programming" && ASSIGNMENT_AI_HELP_ERROR_STATUSES.has(result?.status);
}
