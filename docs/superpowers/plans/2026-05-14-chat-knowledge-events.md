# Chat Knowledge Events Implementation Notes

## Goal

Chat answers can use the restored knowledge-graph RAG path before generation. After each completed turn, the system still records the Java knowledge points mentioned in that turn as consultation events for student review and teacher analytics.

## Current Architecture

- `backend/services/chat_service.py` saves the user message, optionally runs graph retrieval, emits `graph_trace`, streams the assistant answer, saves the assistant message, and starts a background extraction thread.
- `backend/services/rag_engine.py` extracts graph keywords, queries Neo4j, selects a relevant path, formats RAG facts, and streams graph-enhanced tutoring answers.
- `backend/services/chat_knowledge_event_service.py` extracts candidates from the completed turn and matches them against existing graph-backed `knowledge_nodes`.
- `backend/models/chat.py` stores RAG facts and traces on `ChatMessage`, and stores matched consultation events in `ChatKnowledgeEvent`.
- `frontend/src/pages/ChatPage.vue` provides the graph retrieval toggle and displays graph status, selected path, related nodes, and retrieval traces.
- Student and teacher pages present chat consultation knowledge points separately from assignment weak points.

## Data Rules

- Chat consultation events record knowledge points the student recently asked about.
- Chat consultation events keep `UserWeakPoint` and `UserKnowledgeState` unchanged.
- Chat RAG facts and traces are answer context stored on `chat_messages`; they are not weak-point writes and are separate from `chat_knowledge_events`.
- Assignment submissions write weak points through the question's bound knowledge nodes when the submission status is not `accepted`.
- Targeted practice can mark a weak point as mastered after a correct answer.
- AI review `diagnoses` is explanatory output and is not used for weak-point writes.

## Backend Flow

1. Validate the session and user.
2. Save the user `ChatMessage`.
3. Build recent conversation history.
4. If `use_knowledge_graph` is enabled, extract keywords, query Neo4j, select a path, and emit `graph_trace`.
5. Stream a graph-enhanced answer when RAG facts exist; otherwise stream a direct LLM tutoring answer.
6. Save the assistant `ChatMessage` with optional `facts_json`, `reasoning_trace_json`, and `retrieval_trace_json`.
7. Commit and emit `assistant_done`.
8. Start background extraction for the completed turn.
9. Store matched knowledge nodes as `ChatKnowledgeEvent` rows.

## RAG Rules

- The default frontend request enables `use_knowledge_graph`.
- Graph retrieval failure logs the error and falls back to direct tutoring.
- `graph_trace` contains `facts`, `reasoning_trace`, and `retrieval_trace`.
- Historical assistant messages replay saved RAG details from `chat_messages`.

## Extraction Rules

- Use the current user message, assistant answer, and limited previous context.
- Ask the LLM for Java knowledge-point candidates.
- Provide the formal `knowledge_nodes` list to the extraction prompt.
- Store only candidates whose `node_id` and `node_name` match an existing node.
- Skip unmatched candidates and duplicate events.

## Student Experience

- Chat answers appear as a streaming tutoring conversation with optional graph context above the assistant answer.
- Students can disable graph retrieval from the ChatPage composer.
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
