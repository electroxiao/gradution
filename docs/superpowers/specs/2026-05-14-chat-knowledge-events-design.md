# Chat Knowledge Events Design

## Goal

Move chat away from blocking graph retrieval and use the knowledge graph as a structured learning record for student and teacher analytics.

The chat answer path should be fast:

1. Save the user message.
2. Stream the LLM answer directly.
3. Save the assistant message.
4. Return `assistant_done` without waiting for graph or knowledge-point extraction.

After the answer finishes, a background task extracts the knowledge points involved in that single turn and stores them as consultation events. These events do not mark weak points, do not change mastery state, and do not affect recommendation ranking in the first version.

## Non-Goals

- Do not query Neo4j before generating a chat answer.
- Do not show selected graph paths or retrieval traces in ChatPage.
- Do not let chat create new graph nodes.
- Do not let chat consultation events call `mark_node_weak`.
- Do not use chat events for weak-point recommendation ranking in this version.

## Product Model

LLM chat and the knowledge graph have separate jobs:

- The LLM handles immediate tutoring and natural-language conversation.
- The knowledge graph stores formal knowledge-point structure.
- Assignment and practice results remain the strong signal for weak points.
- Chat consultation events are weak learning traces for review and analytics.

This keeps the student experience fast while preserving a meaningful graph-based record for teachers and students.

## Turn Granularity

Knowledge-point extraction is performed per completed turn:

```text
one user message + its assistant answer -> chat knowledge events
```

A session is only a conversation container. It is not treated as one fixed topic. If a student asks about different concepts in the same session, each turn is recorded independently.

Example:

```text
session 12 / turn 1 -> ArrayList, generics
session 12 / turn 2 -> HashMap, equals/hashCode
session 12 / turn 3 -> NullPointerException, exception handling
```

Session-level involved knowledge points may be shown as an aggregate, but raw statistics are based on turn events.

## Backend Flow

The new chat stream flow:

1. Validate the session and user.
2. Save the user `ChatMessage`.
3. Build recent chat history.
4. Stream a direct LLM answer without graph retrieval.
5. Save the assistant `ChatMessage`.
6. Commit and return `assistant_done`.
7. Start a background extraction task for this turn.

The background task:

1. Reads the current user message, assistant message, and limited previous context.
2. Calls the LLM to extract Java knowledge-point candidates.
3. Matches candidates against formal graph-backed `knowledge_nodes`.
4. Stores matched items as chat knowledge events.
5. Ignores unmatched candidates.

Extraction failure must not affect the chat response.

## Data Model

Add a `chat_knowledge_events` table:

```text
id
user_id
session_id
user_message_id
assistant_message_id
knowledge_node_id
confidence
evidence_text
created_at
```

Suggested uniqueness:

```text
(user_id, session_id, user_message_id, assistant_message_id, knowledge_node_id)
```

This prevents duplicate rows if a background job retries.

## Extraction Rules

Use an LLM for extraction, but only store formal existing knowledge nodes.

Prompt requirements:

- Extract only Java programming knowledge points.
- Return at most 3 to 5 candidates per turn.
- Do not extract generic terms such as code, error, programming, question, or learning.
- Do not decide whether the student is weak.
- Include a short evidence phrase for each candidate.
- Return structured JSON.

Matching requirements:

- Match only against existing `knowledge_nodes` mirrored from the formal graph.
- Do not create new nodes from chat.
- Drop candidates that cannot be matched confidently.

## Frontend Changes

ChatPage:

- Remove the selected-path graph card.
- Remove retrieval-trace display.
- Replace wording such as "knowledge graph and AI jointly generated" with direct AI tutoring wording.
- Keep the streaming answer UI.

Student view:

- Add or extend a "recent consultations" area.
- Show knowledge point name, latest consultation time, session title, and a link back to the conversation.
- Do not mix these records into the weak-point list.

Teacher view:

- Add class consultation hotspot statistics.
- Allow viewing consultation knowledge points by student.
- Keep consultation hotspots visually and semantically separate from assignment weak points.

## Analytics

Teacher statistics should support two metrics:

- Mention count: how often a knowledge point appears in chat consultation events.
- Student count: how many distinct students consulted that knowledge point.

Student count should be emphasized when showing class-level hotspots so a single student repeatedly asking the same concept does not dominate the class signal.

## Error Handling

- If extraction fails, log the failure and do not notify the student.
- If candidate matching fails, skip unmatched candidates.
- If duplicate insertion occurs, keep one event.
- If the background task is delayed, chat still completes normally.
- If the graph or `knowledge_nodes` mirror is unavailable, no event is written for that turn.

## Testing

Backend checks:

- Chat streaming returns without graph retrieval.
- `assistant_done` is not blocked by knowledge-point extraction.
- A completed turn can produce chat knowledge events.
- Duplicate events are not inserted twice.
- Unmatched candidates do not create knowledge nodes.
- Chat events do not change `UserWeakPoint` or `UserKnowledgeState`.

Frontend checks:

- ChatPage streams answers normally without selected path or retrieval trace UI.
- Student consultation history displays event aggregates.
- Teacher statistics distinguish consultation hotspots from weak points.

## Migration Notes

Existing `facts_json`, `reasoning_trace_json`, and `retrieval_trace_json` fields can remain for backward compatibility, but the new direct chat path should stop relying on them for normal student chat.

Existing assignment and weak-point behavior remains unchanged:

- Wrong assignment submissions mark bound knowledge nodes as unmastered weak points.
- WeakPointsPage continues to use graph structure for weak-point review and recommendation.
