# Teacher Student Portrait Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the teacher-side student portrait page so a teacher can inspect one student's weak points, assignment status, consultation knowledge points, and related chat turns.

**Architecture:** Keep `/teacher/students` as the route and rename the teacher navigation entry to “学生画像”. Add two teacher-only read APIs: a student assignment summary endpoint and a knowledge-point chat-turn endpoint. Refactor `TeacherStudentsPage.vue` in place into a student list plus portrait workspace with three tabs.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Vue 3, Vite, Headless UI Listbox, lucide-vue-next, Axios.

---

### Task 1: Backend Teacher Student Portrait APIs

**Files:**
- Modify: `backend/schemas/teacher.py`
- Modify: `backend/services/teacher_service.py`
- Modify: `backend/services/chat_knowledge_event_service.py`
- Modify: `backend/api/routes/teacher.py`

- [ ] **Step 1: Add teacher response schemas**

Add `TeacherStudentAssignmentResponse` and `TeacherStudentConsultationTurnResponse` to `backend/schemas/teacher.py`.

- [ ] **Step 2: Add student assignment aggregation**

In `backend/services/teacher_service.py`, import assignment models and implement `list_student_assignments(db, student_id)`. Query assignments assigned to the student, group that student's submissions by assignment/question, calculate `question_count`, `submitted_question_count`, `accepted_question_count`, `latest_submitted_at`, and a status of `not_submitted`, `partial`, `submitted`, or `completed`.

- [ ] **Step 3: Add consultation-turn lookup**

In `backend/services/chat_knowledge_event_service.py`, add a dataclass for the turn result and implement `list_student_consultation_turns(db, student_id, knowledge_node_id, limit)`. Join `ChatKnowledgeEvent`, `ChatSession`, user message, and assistant message aliases; filter by student and knowledge node; order newest first.

- [ ] **Step 4: Expose teacher routes**

In `backend/api/routes/teacher.py`, add:

```python
GET /api/teacher/students/{student_id}/assignments
GET /api/teacher/students/{student_id}/consultations/{knowledge_node_id}/turns
```

Both routes must depend on `get_current_teacher` and validate the student exists with `role == "student"`.

- [ ] **Step 5: Verify backend syntax**

Run: `python -m compileall backend`

Expected: command completes without Python syntax errors.

### Task 2: Frontend API and Teacher Navigation

**Files:**
- Modify: `frontend/src/api/teacher.js`
- Modify: `frontend/src/pages/TeacherLayout.vue`

- [ ] **Step 1: Add API wrappers**

Add:

```javascript
export const listTeacherStudentAssignmentsApi = (studentId) =>
  http.get(`/api/teacher/students/${studentId}/assignments`);

export const listTeacherStudentConsultationTurnsApi = (studentId, knowledgeNodeId, limit = 20) =>
  http.get(`/api/teacher/students/${studentId}/consultations/${knowledgeNodeId}/turns`, { params: { limit } });
```

- [ ] **Step 2: Rename nav entry**

Change the teacher sidebar label from “学生薄弱点” to “学生画像”.

### Task 3: Student Portrait Page Refactor

**Files:**
- Modify: `frontend/src/pages/TeacherStudentsPage.vue`

- [ ] **Step 1: Update imports and state**

Import the new API wrappers and additional lucide icons. Add active tab state, assignment list state, selected consultation knowledge-node state, consultation turns state, expanded turn state, and loading flags.

- [ ] **Step 2: Load portrait data on student selection**

When a student is selected, load weak points, consultation summaries, and assignment summaries in parallel. Reset the selected consultation node and turn timeline.

- [ ] **Step 3: Build student portrait template**

Change the title to “学生画像”. Keep the student list left panel. Replace the right-side two-panel layout with a summary header and tabbed panels:

- `薄弱点`
- `作业情况`
- `提问情况`

- [ ] **Step 4: Implement assignment tab**

Render assignment rows with status, accepted/submitted counts, due date, latest submission date, and a link to `/teacher/assignments/:assignmentId/progress?studentId=:studentId`.

- [ ] **Step 5: Implement consultation tab**

Render consultation knowledge-point rows. On click, load related turns for that knowledge point. Render a timeline with session title, asked time, question/answer previews, and expandable full content.

- [ ] **Step 6: Add scoped styles**

Update the existing scoped CSS to support the portrait header, tabs, assignment rows, consultation timeline, compact 8px-radius controls, and mobile stacking.

### Task 4: Assignment Progress Student Deep Link

**Files:**
- Modify: `frontend/src/pages/TeacherAssignmentProgressPage.vue`

- [ ] **Step 1: Read query parameter**

Use `useRoute()` to read `studentId` from the query string after progress data loads.

- [ ] **Step 2: Apply filter or focus**

If the student exists in the progress result, set the matrix filter so submitted/unsubmitted filtering does not hide them, set the page containing that student, and optionally open their first relevant detail row only if the data structure already makes that safe.

- [ ] **Step 3: Avoid disruptive behavior**

Do not auto-open a modal if the assignment has no submissions for the target student.

### Task 5: Verification

**Files:**
- Verify all modified files.

- [ ] **Step 1: Backend compile check**

Run: `python -m compileall backend`

Expected: command succeeds.

- [ ] **Step 2: Frontend build check**

Run: `npm --prefix frontend run build`

Expected: Vite build succeeds.

- [ ] **Step 3: Git diff review**

Run: `git diff --stat` and `git diff --check`.

Expected: only intended files changed; no whitespace errors.
