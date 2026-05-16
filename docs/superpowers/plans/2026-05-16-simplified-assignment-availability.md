# Simplified Assignment Availability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify assignment availability to draft/published plus start and due times, with late submissions allowed and marked.

**Architecture:** Keep the existing FastAPI service and Vue page structure. The backend remains the source of truth for visibility, start-time access, and late-submission marking; the frontend mirrors those rules for clear UI feedback.

**Tech Stack:** FastAPI, SQLAlchemy, MySQL-compatible bootstrap schema updates, Vue 3, Vite.

---

### Task 1: Backend Availability Rules

**Files:**
- Modify: `backend/models/assignment.py`
- Modify: `backend/schemas/assignment.py`
- Modify: `backend/services/assignment_service.py`
- Modify: `backend/db/bootstrap.py`
- Test: `tests/test_assignment_availability.py`

- [x] Add `is_late` to `AssignmentSubmission`, response schemas, and bootstrap schema repair.
- [x] Change valid assignment statuses to `draft` and `published`.
- [x] Treat existing `closed` assignments as `published` during bootstrap cleanup.
- [x] Student assignment list returns published assignments, including future-start assignments.
- [x] Student assignment detail and submit reject assignments whose `starts_at` is in the future.
- [x] Submit marks each new submission with `is_late=True` when `due_at` is before submission time; late submissions still grade normally.
- [x] Add focused unit tests for future-start rejection and late marking.

### Task 2: Teacher UI Simplification

**Files:**
- Modify: `frontend/src/pages/TeacherAssignmentEditorPage.vue`
- Modify: `frontend/src/pages/TeacherAssignmentsPage.vue`

- [x] Remove the `已关闭` status option from the editor.
- [x] Keep `开始时间` and `截止时间`.
- [x] Ensure payloads still send `starts_at` and `due_at`.
- [x] Update teacher list labels so `closed` is not presented as a normal status.
- [x] Show start/due timing in assignment list copy instead of only created time.

### Task 3: Student UI Timing Feedback

**Files:**
- Modify: `frontend/src/pages/StudentAssignmentsPage.vue`
- Modify: `frontend/src/pages/StudentAssignmentWorkPage.vue`

- [x] Compute assignment availability from `starts_at` and `due_at`.
- [x] Show `未开始`, `进行中`, or `已逾期` in the student list.
- [x] Disable entering a future-start assignment from the list.
- [x] Show a late-submission note on the work page when `due_at` has passed.
- [x] Display late submission labels when returned submission rows include `is_late`.

### Task 4: Verification

**Files:**
- Verify only.

- [x] Run `python -m compileall backend`.
- [x] Run focused backend tests for assignment availability.
- [x] Run `npm --prefix frontend run build`.
