<template>
  <div class="page-shell chat-page">
    <SessionSidebar
      :sessions="sessions"
      :active-session-id="activeSessionId"
      @create-session="createSession"
      @select-session="selectSession"
    />

    <main class="card chat-main">
      <header class="chat-header">
        <div>
          <h2>知识图谱辅导</h2>
          <p>按用户保存对话历史与薄弱点。</p>
        </div>
        <router-link to="/weak-points">查看薄弱点</router-link>
      </header>

      <section class="controls">
        <label>推理深度 <input v-model.number="ragDepth" type="range" min="1" max="4" /></label>
        <label>候选宽度 <input v-model.number="ragWidth" type="range" min="1" max="8" /></label>
      </section>

      <section class="messages">
        <article v-for="message in messages" :key="message.id" class="message">
          <strong>{{ message.role === "user" ? "你" : "助手" }}</strong>
          <p>{{ message.content }}</p>
        </article>
        <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
      </section>

      <form class="composer" @submit.prevent="sendMessage">
        <textarea v-model="content" rows="4" placeholder="请输入你的问题..." />
        <button type="submit" :disabled="sending">{{ sending ? "发送中..." : "发送" }}</button>
      </form>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { createSessionApi, listMessagesApi, listSessionsApi, sendMessageApi } from "../api/chat";
import SessionSidebar from "../components/SessionSidebar.vue";

const router = useRouter();
const sessions = ref([]);
const messages = ref([]);
const activeSessionId = ref(null);
const content = ref("");
const ragDepth = ref(2);
const ragWidth = ref(3);
const errorMessage = ref("");
const sending = ref(false);

onMounted(async () => {
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

async function selectSession(sessionId) {
  activeSessionId.value = sessionId;
  const { data } = await listMessagesApi(sessionId);
  messages.value = data;
}

async function sendMessage() {
  if (!content.value.trim() || !activeSessionId.value) return;
  errorMessage.value = "";
  sending.value = true;
  try {
    const payload = {
      content: content.value,
      rag_depth: ragDepth.value,
      rag_width: ragWidth.value,
    };
    const { data } = await sendMessageApi(activeSessionId.value, payload);
    messages.value.push(data.user_message, data.assistant_message);
    content.value = "";
    await loadSessions();
  } catch (error) {
    handleApiError(error, "发送失败，请检查后端日志。");
  } finally {
    sending.value = false;
  }
}

function handleApiError(error, fallbackMessage) {
  const status = error?.response?.status;
  if (status === 401 || status === 403) {
    localStorage.removeItem("access_token");
    router.push("/login");
    return;
  }
  errorMessage.value = error?.response?.data?.detail || fallbackMessage;
}
</script>

<style scoped>
.chat-page {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 20px;
}

.chat-main {
  padding: 20px;
}

.chat-header,
.controls,
.composer {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.messages {
  margin: 20px 0;
  display: grid;
  gap: 12px;
}

.message {
  padding: 14px;
  border-radius: 12px;
  background: #f8fbff;
}

.error {
  color: #b91c1c;
}

textarea {
  flex: 1;
  padding: 12px;
  border-radius: 12px;
}
</style>
