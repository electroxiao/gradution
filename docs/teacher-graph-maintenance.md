# Teacher Graph & Pending Review Maintenance Guide

## 1. Scope

This document explains the parts of the system that are hardest to understand and easiest to break:

- teacher knowledge graph editing
- pending batch generation from chat / weak-point flows
- teacher-side pending batch review
- session-scoped frontend auth storage

It is written as a maintenance guide rather than a user guide.

## 2. Core Concepts

### Formal graph

- Stored in Neo4j as `Knowledge` nodes plus graph relationships such as `DEPENDS_ON`.
- Used by chat retrieval, weak-point recommendation, teacher graph management, and approved pending content.

### Pending batch

- Stored in MySQL, not Neo4j.
- Represents one candidate knowledge subgraph proposal, usually generated from chat or weak-point recommendation.
- Contains:
  - one anchor concept
  - multiple pending nodes
  - suggested edges
  - source metadata such as user, chat session, weak point, and question excerpt

### Legacy pending proposal

- Older single-node pending records still exist and are kept readable for compatibility.
- Teacher APIs expose them as `legacy:*` batch ids so the new review UI can still render them.

## 3. End-to-End Data Flow

### A. Chat creates a pending batch

1. `chat_service.stream_message()` extracts keywords and queries graph facts.
2. The assistant answer is streamed immediately.
3. In parallel, `_run_pending_chat_proposal()` calls `pending_batch_service.propose_pending_batch_from_chat()`.
4. The pending batch service:
   - resolves an anchor concept
   - asks the model for candidate nodes / descriptions / reasons / edges
   - falls back to keyword-based candidates if the model or graph recall is insufficient
   - filters out nodes that already exist in Neo4j or are already pending
   - stores the batch in MySQL
5. After the answer is done, chat emits a `pending_notice` SSE event if a batch was created.

### B. Weak page reuses pending content

- Weak-point recommendation APIs can read pending nodes linked to the same anchor.
- This lets chat-discovered candidates appear again in the weak-point page before teacher approval.

### C. Teacher reviews the batch

1. `TeacherGraphPage` loads:
   - the formal graph from Neo4j
   - pending batch summaries from MySQL
2. When a batch is selected, the page loads batch detail and hydrates editable drafts.
3. The review graph is built from:
   - pending nodes
   - context nodes that already exist in Neo4j
   - suggested edges
4. Teacher keeps or removes nodes and edges.
5. Approval writes selected nodes and edges into Neo4j.
6. Batch review state is updated in MySQL as `approved`, `partially_approved`, or `rejected`.

## 4. Key Files

### Backend

- `backend/services/pending_batch_service.py`
  - batch creation
  - chat-driven pending proposal generation
  - teacher-facing batch detail assembly
  - approval / rejection
- `backend/services/chat_service.py`
  - triggers background pending-batch proposal after facts are ready
  - keeps pending generation off the main answer path

### Frontend

- `frontend/src/pages/TeacherGraphPage.vue`
  - formal graph editing mode
  - pending batch review mode
  - layout and draft state for teacher review
- `frontend/src/utils/authStorage.js`
  - per-tab auth storage
  - migration from older `localStorage` auth

## 5. Important Maintenance Rules

### Do not write pending content directly into Neo4j

- New candidate knowledge must stay in MySQL until approved.
- Only approval code should create Neo4j nodes and relationships for pending content.

### Keep anchor handling consistent

- An anchor may already exist in Neo4j or may itself be pending.
- Review graphs therefore mix pending nodes with existing context nodes.
- Any change to anchor resolution must be reflected in:
  - chat proposal generation
  - weak-point pending reuse
  - teacher batch detail building

### Always guarantee a non-empty `desc`

- Teacher review becomes confusing very quickly if pending nodes have blank descriptions.
- The system currently follows:
  - model `desc` first
  - `reason` fallback
  - generated fallback description last

### Keep teacher edits in drafts, not in raw API payload

- `TeacherGraphPage` copies batch detail into editable drafts before the teacher changes names, descriptions, or keep flags.
- This avoids mutating the source payload and makes approval payload generation predictable.

### Keep auth per browser tab

- Teacher and student are expected to be usable at the same time in different tabs.
- Frontend auth now uses `sessionStorage`, with lazy migration from legacy `localStorage`.
- Any future auth helper should go through `authStorage.js` rather than reading browser storage directly.

## 6. Common Failure Points

- Pending nodes duplicated:
  - usually caused by bypassing `create_pending_batch_from_candidates()`
- Pending edge approval silently skipped:
  - happens when one edge endpoint is not present in Neo4j after filtering
- Teacher review UI looks inconsistent:
  - usually caused by changing pending batch response shape without updating draft hydration
- Teacher / student login collisions:
  - happens if code reads or writes `localStorage` directly instead of using `authStorage.js`

## 7. Safe Change Checklist

When changing pending review or teacher graph features, verify all of the following:

- chat still answers normally even if pending proposal generation fails
- pending batch detail still mixes pending nodes and existing context nodes correctly
- teacher can partially approve a batch without breaking remaining edges
- weak-point page can still reuse pending nodes for the same anchor
- teacher and student can still be logged in simultaneously in separate tabs
- frontend build and backend compile still pass
