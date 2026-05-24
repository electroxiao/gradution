# Chat Knowledge Events Implementation Notes

## Goal

Chat answers stream directly from the LLM. After each completed turn, the system records the Java knowledge points mentioned in that turn as consultation events for student review and teacher analytics.

## Current Architecture

- `backend/services/chat_service.py` saves the user message, streams the assistant answer, saves the assistant message, and starts a background extraction thread.
- `backend/services/chat_knowledge_event_service.py` extracts candidates from the completed turn and matches them against existing graph-backed `knowledge_nodes`.
- `backend/models/chat.py` stores matched events in `ChatKnowledgeEvent`.
- `frontend/src/pages/ChatPage.vue` focuses on the tutoring conversation.
- Student and teacher pages present chat consultation knowledge points separately from assignment weak points.

## Data Rules

- Chat consultation events record knowledge points the student recently asked about.
- Chat consultation events keep `UserWeakPoint` and `UserKnowledgeState` unchanged.
- Assignment submissions write weak points through the question's bound knowledge nodes when the submission status is not `accepted`.
- Targeted practice can mark a weak point as mastered after a correct answer.
- AI review `diagnoses` is explanatory output and is not used for weak-point writes.

## Backend Flow

1. Validate the session and user.
2. Save the user `ChatMessage`.
3. Build recent conversation history.
4. Stream a direct LLM tutoring answer.
5. Save the assistant `ChatMessage`.
6. Commit and emit `assistant_done`.
7. Start background extraction for the completed turn.
8. Store matched knowledge nodes as `ChatKnowledgeEvent` rows.

## Extraction Rules

- Use the current user message, assistant answer, and limited previous context.
- Ask the LLM for Java knowledge-point candidates.
- Provide the formal `knowledge_nodes` list to the extraction prompt.
- Store only candidates whose `node_id` and `node_name` match an existing node.
- Skip unmatched candidates and duplicate events.

## Student Experience

- Chat answers appear as a normal streaming tutoring conversation.
- Recent consultation knowledge points show what the student has asked about.
- Weak-point lists remain focused on concepts currently marked unmastered.

## Teacher Experience

- Teacher dashboards can show consultation hotspots by class or student.
- Consultation hotspots indicate student attention and questions.
- Assignment weak points indicate unmastered concepts from submitted work.

## Verification

Useful checks for this area:

```powershell
python -m compileall backend
npm --prefix frontend run build
pytest tests/test_chat_knowledge_events.py
```
