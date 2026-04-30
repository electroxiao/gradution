<template>
  <div class="page-shell app-shell" :class="{ embedded }">
    <SessionSidebar
      v-if="!embedded"
      :sessions="sessions"
      :active-session-id="activeSessionId"
      @create-session="createSession"
      @select-session="selectSession"
      @rename-session="renameSession"
      @delete-session="deleteSession"
    />

    <main class="chat-stage">
      <header class="topbar">
        <div class="topbar-copy">
          <h1><AnimatedTitle :text="activeSessionTitle" /></h1>
          <p>知识图谱与 AI 联合生成</p>
        </div>
      </header>

      <section ref="messageScroller" class="message-stream">
        <article
          v-for="message in messages"
          :key="message.id ?? message.tempId"
          class="message-row"
          :class="message.role === 'user' ? 'user-row' : message.role === 'system' ? 'system-row' : 'assistant-row'"
        >
          <div class="message-stack" :class="message.role === 'user' ? 'user-stack' : message.role === 'system' ? 'system-stack' : 'assistant-stack'">
            <div v-if="message.role === 'system' || (message.role === 'assistant' && message.streaming)" class="message-meta" :class="{ 'assistant-meta': message.role === 'assistant' }">
              <strong v-if="message.role === 'system'">系统提示</strong>
              <span v-if="message.streaming" class="streaming-flag">正在生成</span>
            </div>

            <div class="message-body" :class="message.role === 'user' ? 'user-body' : message.role === 'system' ? 'system-body' : 'assistant-body'">
              <MarkdownContent v-if="message.role === 'assistant'" :content="message.content" />
              <p v-else class="plain-text">{{ message.content }}</p>
            </div>

            <SelectedPathGraph v-if="message.role === 'assistant'" :facts="message.facts || []" />

            <details
              v-if="message.role === 'assistant' && (message.reasoning_trace?.length || message.retrieval_trace?.length)"
              class="trace-box"
            >
              <summary>查看检索过程</summary>
              <div v-if="message.reasoning_trace?.length" class="trace-group">
                <strong>推理轨迹</strong>
                <ul>
                  <li v-for="(item, index) in message.reasoning_trace" :key="`reason-${index}`">
                    {{ item.title }}：{{ item.summary }}
                  </li>
                </ul>
              </div>
              <div v-if="message.retrieval_trace?.length" class="trace-group">
                <strong>检索轨迹</strong>
                <ul>
                  <li v-for="(item, index) in message.retrieval_trace" :key="`retrieval-${index}`">
                    {{ item.title }}：{{ item.summary }}
                  </li>
                </ul>
              </div>
            </details>
          </div>
        </article>

        <p v-if="errorMessage" class="error-banner">{{ errorMessage }}</p>
      </section>

        <form class="composer-shell" @submit.prevent="sendMessage">
          <div class="composer-card">
            <textarea
              ref="composerInput"
              v-model="content"
              rows="1"
              placeholder="发消息..."
              @input="syncComposerHeight"
            />
            <div class="composer-actions">
              <span />
              <button
                type="submit"
                class="composer-submit"
                :disabled="sending || !content.trim()"
                :aria-label="sending ? '生成中' : '发送消息'"
              >
                <span v-if="sending" class="submit-dot" />
                <svg v-else viewBox="0 0 20 20" fill="none" aria-hidden="true">
                  <path
                    d="M10 15V5M10 5L6.5 8.5M10 5L13.5 8.5"
                    stroke="currentColor"
                    stroke-width="1.9"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </button>
            </div>
          </div>
        </form>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import {
  createSessionApi,
  deleteSessionApi,
  listMessagesApi,
  listSessionsApi,
  renameSessionApi,
  streamMessageApi,
} from "../api/chat";
import AnimatedTitle from "../components/AnimatedTitle.vue";
import MarkdownContent from "../components/MarkdownContent.vue";
import SelectedPathGraph from "../components/SelectedPathGraph.vue";
import SessionSidebar from "../components/SessionSidebar.vue";
import { useAuthStore } from "../stores/auth";

defineProps({
  embedded: {
    type: Boolean,
    default: false,
  },
});
defineEmits(["close"]);

const DEFAULT_RAG_DEPTH = 2;
const DEFAULT_RAG_WIDTH = 3;

const authStore = useAuthStore();
const router = useRouter();
const sessions = ref([]);
const messages = ref([]);
const activeSessionId = ref(null);
const content = ref("");
const errorMessage = ref("");
const sending = ref(false);
const messageScroller = ref(null);
const composerInput = ref(null);

const activeSessionTitle = computed(() => {
  return sessions.value.find((session) => session.id === activeSessionId.value)?.title || "新对话";
});

onMounted(async () => {
  syncComposerHeight();
  try {
    await loadSessions();
    if (!sessions.value.length) {
      await createSession();
    } else {
      await selectSession(sessions.value[0].id);
    }
  } catch (error) {
    handleApiError(error, "加载会话失败，请先登录。");
  }
});

async function loadSessions() {
  const { data } = await listSessionsApi();
  sessions.value = data;
}

async function createSession() {
  const { data } = await createSessionApi({ title: "新对话" });
  await loadSessions();
  await selectSession(data.id);
}

async function renameSession({ sessionId, title }) {
  try {
    await renameSessionApi(sessionId, { title });
    await loadSessions();
  } catch (error) {
    handleApiError(error, "重命名失败，请稍后重试。");
  }
}

async function deleteSession(sessionId) {
  try {
    await deleteSessionApi(sessionId);
    await loadSessions();

    if (!sessions.value.length) {
      await createSession();
      return;
    }

    const nextSession = sessions.value.find((session) => session.id !== sessionId) || sessions.value[0];
    await selectSession(nextSession.id);
  } catch (error) {
    handleApiError(error, "删除失败，请稍后重试。");
  }
}

async function selectSession(sessionId) {
  activeSessionId.value = sessionId;
  const { data } = await listMessagesApi(sessionId);
  messages.value = data.map((message) => ({ ...message, streaming: false }));
  await scrollToBottom();
}

function syncComposerHeight() {
  if (!composerInput.value) return;
  composerInput.value.style.height = "auto";
  composerInput.value.style.height = `${Math.min(composerInput.value.scrollHeight, window.innerHeight * 0.5)}px`;
}

async function sendMessage() {
  if (!content.value.trim() || !activeSessionId.value || sending.value) return;

  errorMessage.value = "";
  sending.value = true;

  const draftContent = content.value;
  const tempUserId = `user-${Date.now()}`;
  const tempAssistantId = `assistant-${Date.now()}`;
  const tempUser = {
    tempId: tempUserId,
    role: "user",
    content: draftContent,
    facts: [],
    reasoning_trace: [],
    retrieval_trace: [],
    streaming: false,
  };
  const tempAssistant = {
    tempId: tempAssistantId,
    role: "assistant",
    content: "",
    facts: [],
    reasoning_trace: [],
    retrieval_trace: [],
    streaming: true,
  };
  content.value = "";
  messages.value.push(tempUser);
  messages.value.push(tempAssistant);
  await nextTick();
  syncComposerHeight();
  await scrollToBottom();

  try {
    await streamMessageApi(
      activeSessionId.value,
      {
        content: draftContent,
        rag_depth: DEFAULT_RAG_DEPTH,
        rag_width: DEFAULT_RAG_WIDTH,
      },
      {
        async onUserMessage(data) {
          const userIndex = messages.value.findIndex((item) => item.tempId === tempUserId);
          if (userIndex >= 0) {
            messages.value.splice(userIndex, 1, { ...data, streaming: false });
          } else {
            messages.value.push({ ...data, streaming: false });
          }
          await scrollToBottom();
        },
        async onAssistantDelta(data) {
          const index = messages.value.findIndex((item) => item.tempId === tempAssistantId);
          if (index >= 0) {
            messages.value[index] = {
              ...messages.value[index],
              content: `${messages.value[index].content || ""}${data.content || ""}`,
            };
            await scrollToBottom();
          }
        },
        async onAssistantDone(data) {
          const index = messages.value.findIndex((item) => item.tempId === tempAssistantId);
          const assistantMessage = { ...data.assistant_message, streaming: false };
          if (index >= 0) {
            messages.value.splice(index, 1, assistantMessage);
          } else {
            messages.value.push(assistantMessage);
          }
          await loadSessions();
          await scrollToBottom();
        },
        async onPendingNotice(data) {
          messages.value.push({
            tempId: `pending-${Date.now()}`,
            role: "system",
            content: data.message || "系统已提交候选知识结点，等待教师审核。",
            facts: [],
            reasoning_trace: [],
            retrieval_trace: [],
            streaming: false,
          });
          await scrollToBottom();
        },
      },
    );
  } catch (error) {
    const userIndex = messages.value.findIndex((item) => item.tempId === tempUserId);
    const index = messages.value.findIndex((item) => item.tempId === tempAssistantId);
    if (userIndex >= 0) {
      messages.value.splice(userIndex, 1);
    }
    if (index >= 0) {
      messages.value.splice(index, 1);
    }
    content.value = draftContent;
    await nextTick();
    syncComposerHeight();
    handleApiError(error, "发送失败，请检查后端日志。");
  } finally {
    sending.value = false;
  }
}

function handleApiError(error, fallbackMessage) {
  const status = error?.response?.status ?? error?.status;
  if (status === 401 || status === 403) {
    logout();
    return;
  }
  errorMessage.value = error?.response?.data?.detail || error?.message || fallbackMessage;
}

function logout() {
  authStore.logout();
  router.push("/login");
}

async function scrollToBottom() {
  await nextTick();
  if (!messageScroller.value) return;
  messageScroller.value.scrollTop = messageScroller.value.scrollHeight;
}
</script>

<style scoped>
.app-shell {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 0;
  height: 100%;
  min-height: 0;
  min-width: 0;
}

.app-shell.embedded {
  grid-template-columns: minmax(0, 1fr);
  height: 100%;
  min-height: 0;
}

.chat-stage {
  position: relative;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
  min-height: 0;
  background: transparent;
}

.embedded .chat-stage {
  height: 100%;
  min-height: 0;
}

.topbar {
  display: grid;
  grid-template-columns: minmax(28px, 1fr) minmax(0, 760px) minmax(28px, 1fr);
  padding: 18px 0 10px;
  min-width: 0;
}

.embedded .topbar {
  padding: 16px;
}

.topbar-copy h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 500;
  color: var(--app-text);
}

.topbar-copy p {
  margin: 6px 0 0;
  color: var(--app-text-muted);
  font-size: 13px;
}

.topbar-copy {
  grid-column: 2;
}

.message-stream {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 8px 0 196px;
  scrollbar-gutter: stable;
  scrollbar-width: thin;
  scrollbar-color: #d8e2ee transparent;
  min-width: 0;
}

.embedded .message-stream {
  padding: 18px 16px 150px;
}

.message-stream::-webkit-scrollbar {
  width: 10px;
}

.message-stream::-webkit-scrollbar-track {
  background: transparent;
}

.message-stream::-webkit-scrollbar-thumb {
  background: #dbe4ef;
  border-radius: 999px;
  border: 2px solid #ffffff;
}

.message-row {
  display: grid;
  grid-template-columns: minmax(28px, 1fr) minmax(0, 760px) minmax(28px, 1fr);
  margin-bottom: 26px;
}

.assistant-row {
  justify-content: center;
}

.user-row {
  justify-content: flex-end;
}

.system-row {
  justify-content: center;
}

.message-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
  grid-column: 2;
}

.assistant-stack {
  align-items: stretch;
  width: 100%;
}

.embedded .assistant-stack,
.embedded .system-stack {
  width: 100%;
}

.embedded .user-stack {
  max-width: 88%;
}

.user-stack {
  align-items: flex-end;
  width: 100%;
}

.system-stack {
  width: 100%;
  align-items: stretch;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--app-text-muted);
  font-size: 13px;
}

.streaming-flag {
  color: #2563eb;
}

.message-body {
  width: 100%;
}

.assistant-body {
  padding: 0;
  border: none;
  background: transparent;
  box-shadow: none;
  color: #1e293b;
  line-height: 1.9;
}

.user-body {
  padding: 14px 18px;
  width: fit-content;
  max-width: 80%;
  border-radius: 20px;
  background: var(--app-primary);
  color: #ffffff;
  text-align: left;
  box-shadow: 0 12px 26px rgba(47, 103, 246, 0.18);
}

.system-body {
  padding: 14px 18px;
  border-radius: 20px;
  background: #f8fbff;
  color: #5b6880;
  border: 1px solid var(--app-line);
}

.plain-text {
  margin: 0;
  line-height: 1.7;
  white-space: pre-wrap;
}

.trace-box {
  width: 100%;
  padding: 4px 2px 0;
  color: var(--app-text-muted);
}

.trace-box summary {
  cursor: pointer;
}

.trace-group {
  margin-top: 10px;
}

.trace-group ul {
  margin: 8px 0 0 18px;
  padding: 0;
}

.composer-shell {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  display: grid;
  grid-template-columns: minmax(28px, 1fr) minmax(0, 760px) minmax(28px, 1fr);
  padding: 18px 0 24px;
  pointer-events: none;
  z-index: 4;
  min-width: 0;
}

.embedded .composer-shell {
  padding: 12px 14px 14px;
}

.embedded .composer-shell::before {
  right: 14px;
  left: 14px;
}

.composer-shell::before {
  content: "";
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 120px;
  background: linear-gradient(180deg, rgba(245, 247, 251, 0) 0%, rgba(245, 247, 251, 0.94) 34%, rgba(245, 247, 251, 0.98) 100%);
  pointer-events: none;
  z-index: 0;
}

.composer-card {
  position: relative;
  z-index: 1;
  width: 100%;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 13px 16px;
  border: 1px solid var(--app-line);
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: var(--app-shadow-strong);
  pointer-events: auto;
  box-sizing: border-box;
  grid-column: 2;
}

.embedded .composer-card {
  width: 100%;
  border-radius: var(--app-radius-md);
}

.composer-card:focus-within {
  border-color: var(--app-line);
  box-shadow: var(--app-shadow-strong);
}

.composer-card textarea {
  width: 100%;
  min-height: 28px;
  max-height: 50vh;
  border: none;
  outline: none;
  resize: none;
  background: transparent;
  box-shadow: none;
  color: #1f2937;
  overflow-y: auto;
  line-height: 1.7;
}

.composer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.composer-submit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 50%;
  background: var(--app-primary);
  color: #fff;
  cursor: pointer;
  box-shadow: 0 12px 24px rgba(47, 103, 246, 0.22);
  transition: transform 0.18s ease, box-shadow 0.18s ease, opacity 0.18s ease;
}

.composer-submit svg {
  width: 30px;
  height: 30px;
}

.composer-submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 14px 28px rgba(47, 103, 246, 0.26);
}

.submit-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: currentColor;
}

.composer-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  box-shadow: none;
}

.error-banner {
  color: #b91c1c;
}

@media (max-width: 980px) {
  .app-shell {
    grid-template-columns: 1fr;
    height: 100%;
  }

  .chat-stage {
    height: 100%;
  }

  .message-stack {
    max-width: 100%;
  }

  .assistant-stack {
    width: 100%;
  }

  .topbar {
    grid-template-columns: 16px minmax(0, 1fr) 16px;
  }

  .message-stream {
    padding: 18px 0 180px;
  }

  .composer-shell {
    grid-template-columns: 16px minmax(0, 1fr) 16px;
    padding: 14px 0 18px;
  }

  .composer-shell::before {
    right: 0;
    left: 0;
  }

  .composer-card {
    width: 100%;
  }
}
</style>
