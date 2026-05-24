# Chat Knowledge Events Design

## Goal

Chat answers stream directly from the LLM, while the knowledge graph provides a structured record of Java knowledge points mentioned in each completed turn.

The chat answer path is:

1. Save the user message.
2. Stream the LLM answer directly.
3. Save the assistant message.
4. Return `assistant_done`.
5. Start background knowledge-point extraction for the completed turn.

The background extraction stores consultation events for student review and teacher analytics. Weak points and mastery state are maintained by assignment results and targeted practice.

## Boundaries

- Chat answer generation uses recent conversation history and direct LLM tutoring.
- Chat knowledge extraction matches only existing graph-backed `knowledge_nodes`.
- Chat extraction records consultation events rather than weak points.
- Weak-point recommendation uses the weak-point state maintained by assignments and practice.
- Teacher consultation hotspots and assignment weak points are displayed as separate teaching signals.

## Product Model

LLM chat and the knowledge graph have separate jobs:

- The LLM handles immediate tutoring and natural-language conversation.
- The knowledge graph stores formal knowledge-point structure.
- Assignment mistakes identify unmastered weak points through teacher-bound question knowledge nodes.
- Targeted practice can mark a weak point as mastered after a correct answer.
- Chat consultation events are learning traces for review and analytics.

This keeps the student experience fast while preserving a meaningful graph-based record for teachers and students.

## Turn Granularity

Knowledge-point extraction is performed per completed turn:

```text
one user message + its assistant answer -> chat knowledge events
```

A session is a conversation container. If a student asks about different concepts in the same session, each turn is recorded independently.

Example:

```text
session 12 / turn 1 -> ArrayList, generics
session 12 / turn 2 -> HashMap, equals/hashCode
session 12 / turn 3 -> NullPointerException, exception handling
```

Session-level involved knowledge points may be shown as an aggregate, but raw statistics are based on turn events.

## Backend Flow

The chat stream flow:

1. Validate the session and user.
2. Save the user `ChatMessage`.
3. Build recent chat history.
4. Stream a direct LLM answer.
5. Save the assistant `ChatMessage`.
6. Commit and return `assistant_done`.
7. Start a background extraction task for this turn.

The background task:

1. Reads the current user message, assistant message, and limited previous context.
2. Calls the LLM to extract Java knowledge-point candidates.
3. Matches candidates against formal graph-backed `knowledge_nodes`.
4. Stores matched items as chat knowledge events.
5. Skips unmatched candidates.

Extraction failure is logged and the chat response remains complete.

## Data Model

`chat_knowledge_events` records the graph knowledge points mentioned in a chat turn:

```text
id
user_id
session_id
user_message_id
assistant_message_id
knowledge_node_id
created_at
```

Uniqueness:

```text
user_id, session_id, user_message_id, assistant_message_id, knowledge_node_id
```

This prevents duplicate rows if a background job retries.

## Extraction Rules

Use an LLM for extraction, and store only formal existing knowledge nodes.

Prompt requirements:

- Extract only Java programming knowledge points.
- Return at most 3 to 5 candidates per turn.
- Keep generic terms such as code, error, programming, question, and learning out of the result.
- Return `node_id` and `node_name` from the provided knowledge-node list.
- Return structured JSON.

Matching requirements:

- Match against existing `knowledge_nodes` mirrored from the formal graph.
- Store only candidates whose id and name agree with an existing node.
- Skip candidates that cannot be matched confidently.

## Frontend Model

ChatPage:

- Streams the direct tutoring answer.
- Keeps the answer UI focused on the conversation.
- Records knowledge-point events in the background.

Student view:

- Shows recent consultation knowledge points.
- Displays knowledge point name, latest consultation time, session title, and a link back to the conversation.
- Keeps consultation records separate from the weak-point list.

Teacher view:

- Shows class consultation hotspot statistics.
- Allows viewing consultation knowledge points by student.
- Keeps consultation hotspots visually and semantically separate from assignment weak points.

## Analytics

Teacher statistics support two metrics:

- Mention count: how often a knowledge point appears in chat consultation events.
- Student count: how many distinct students consulted that knowledge point.

Student count is emphasized for class-level hotspots so one student's repeated questions do not dominate the class signal.

## Error Handling

- Extraction failures are logged.
- Unmatched candidates are skipped.
- Duplicate insertion keeps one event.
- Delayed background tasks do not affect chat completion.
- If the graph or `knowledge_nodes` mirror is unavailable, no event is written for that turn.

## Testing

Backend checks:

- Chat streaming returns promptly.
- `assistant_done` is not blocked by knowledge-point extraction.
- A completed turn can produce chat knowledge events.
- Duplicate events are not inserted twice.
- Unmatched candidates do not create knowledge nodes.
- Chat events keep `UserWeakPoint` and `UserKnowledgeState` unchanged.

Frontend checks:

- ChatPage streams answers normally.
- Student consultation history displays event aggregates.
- Teacher statistics distinguish consultation hotspots from weak points.

## Assignment And Weak-Point Behavior

- Wrong assignment submissions mark bound knowledge nodes as unmastered weak points.
- AI review `diagnoses` is explanatory output for teachers and students.
- WeakPointsPage uses graph structure for weak-point review and recommendation.
