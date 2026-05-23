import assert from "node:assert/strict";
import { shouldShowAssignmentAiHelp } from "./aiHelpVisibility.js";

const programmingQuestion = { question_type: "programming" };
const choiceQuestion = { question_type: "multiple_choice" };
const blankQuestion = { question_type: "fill_blank" };

assert.equal(
  shouldShowAssignmentAiHelp(programmingQuestion, { status: "wrong_answer" }),
  true,
  "programming submissions with wrong answers should show AI help",
);
assert.equal(
  shouldShowAssignmentAiHelp(programmingQuestion, { status: "runtime_error" }),
  true,
  "programming submissions with runtime errors should show AI help",
);
assert.equal(
  shouldShowAssignmentAiHelp(programmingQuestion, { status: "accepted" }),
  false,
  "accepted programming submissions should not show AI help",
);
assert.equal(
  shouldShowAssignmentAiHelp(programmingQuestion, { status: "submitted" }),
  false,
  "pending programming submissions should not show AI help",
);
assert.equal(
  shouldShowAssignmentAiHelp(programmingQuestion, null),
  false,
  "programming questions without a submission result should not show AI help",
);
assert.equal(
  shouldShowAssignmentAiHelp(choiceQuestion, { status: "ai_rejected" }),
  false,
  "objective questions should not show AI help even when rejected",
);
assert.equal(
  shouldShowAssignmentAiHelp(blankQuestion, { status: "wrong_answer" }),
  false,
  "fill blank questions should not show AI help even when wrong",
);

console.log("aiHelpVisibility tests passed");
