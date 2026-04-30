<template>
  <aside class="sidebar">
    <div class="brand-card">
      <div class="brand-avatar">知</div>
      <div>
        <h3>知识辅导</h3>
      </div>
    </div>

    <button class="new-chat-btn" @click="$emit('create-session')">
      <span class="plus">＋</span>
      <span>新对话</span>
    </button>

    <div class="session-list">
      <div
        v-for="session in sessions"
        :key="session.id"
        class="session-row"
        :class="{ active: session.id === activeSessionId }"
        @mouseenter="hoveredSessionId = session.id"
        @mouseleave="hoveredSessionId = menuSessionId === session.id ? session.id : null"
      >
        <button class="session-main" @click="$emit('select-session', session.id)">
          <span class="session-title">
            <AnimatedTitle :text="session.title" />
          </span>
        </button>

        <button
          v-if="hoveredSessionId === session.id || menuSessionId === session.id"
          class="menu-trigger"
          @click.stop="toggleMenu(session.id)"
        >
          ⋯
        </button>

        <div v-if="menuSessionId === session.id" class="menu-panel">
          <button @click.stop="startRename(session)">重命名</button>
          <button class="danger" @click.stop="openDeleteConfirm(session)">删除</button>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="renameSessionId !== null" class="dialog-backdrop" @click.self="closeRename">
        <div class="dialog-card">
          <h4>重命名对话</h4>
          <input
            v-model.trim="renameTitle"
            class="dialog-input"
            maxlength="120"
            placeholder="输入新的对话标题"
            @keydown.enter.prevent="submitRename"
          />
          <div class="dialog-actions">
            <button class="ghost-btn" @click="closeRename">取消</button>
            <button class="primary-btn" :disabled="!renameTitle" @click="submitRename">保存</button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="deleteTarget" class="dialog-backdrop" @click.self="closeDeleteConfirm">
        <div class="dialog-card">
          <h4>删除对话</h4>
          <p>删除后该对话及其历史消息将无法恢复。</p>
          <div class="dialog-actions">
            <button class="ghost-btn" @click="closeDeleteConfirm">取消</button>
            <button class="danger-btn" @click="confirmDelete">确认删除</button>
          </div>
        </div>
      </div>
    </Teleport>
  </aside>
</template>

<script setup>
import { ref } from "vue";

import AnimatedTitle from "./AnimatedTitle.vue";

const props = defineProps({
  sessions: { type: Array, default: () => [] },
  activeSessionId: { type: Number, default: null },
});

const emit = defineEmits(["create-session", "select-session", "rename-session", "delete-session"]);

const hoveredSessionId = ref(null);
const menuSessionId = ref(null);
const renameSessionId = ref(null);
const renameTitle = ref("");
const deleteTarget = ref(null);

function toggleMenu(sessionId) {
  menuSessionId.value = menuSessionId.value === sessionId ? null : sessionId;
  hoveredSessionId.value = sessionId;
}

function startRename(session) {
  renameSessionId.value = session.id;
  renameTitle.value = session.title;
  menuSessionId.value = null;
}

function closeRename() {
  renameSessionId.value = null;
  renameTitle.value = "";
}

function submitRename() {
  if (!renameTitle.value || renameSessionId.value === null) return;
  emit("rename-session", { sessionId: renameSessionId.value, title: renameTitle.value });
  closeRename();
}

function openDeleteConfirm(session) {
  deleteTarget.value = session;
  menuSessionId.value = null;
}

function closeDeleteConfirm() {
  deleteTarget.value = null;
}

function confirmDelete() {
  if (!deleteTarget.value) return;
  emit("delete-session", deleteTarget.value.id);
  closeDeleteConfirm();
}
</script>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100vh;
  padding: 16px 12px;
  background: #ffffff;
  border-right: 1px solid var(--app-line);
  overflow-x: hidden;
  font-size: 13px;
}

.brand-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 6px 2px;
}

.brand-avatar {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 14px;
  background: linear-gradient(135deg, #2f67f6 0%, #7ca7ff 100%);
  color: #fff;
  font-weight: 700;
}

.brand-card h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 400;
  color: var(--app-text);
}

.new-chat-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--app-line);
  border-radius: 16px;
  background: #ffffff;
  color: var(--app-primary);
  cursor: pointer;
  box-shadow: 0 10px 24px rgba(20, 34, 53, 0.05);
}

.plus {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: rgba(47, 103, 246, 0.1);
}

.session-list {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 6px;
  overflow: auto;
  overflow-x: hidden;
  padding-right: 4px;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.session-list::-webkit-scrollbar {
  width: 0;
  height: 0;
}

.session-row {
  position: relative;
  display: flex;
  align-items: center;
  border-radius: 12px;
}

.session-row.active {
  background: #ffffff;
  box-shadow: inset 0 0 0 1px rgba(47, 103, 246, 0.16);
}

.session-main {
  flex: 1;
  padding: 10px 34px 10px 12px;
  border: none;
  border-radius: 16px;
  background: transparent;
  text-align: left;
  color: #31445f;
  cursor: pointer;
}

.session-title {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.menu-trigger {
  position: absolute;
  right: 8px;
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 10px;
  background: #ffffff;
  color: var(--app-text-muted);
  cursor: pointer;
}

.menu-panel {
  position: absolute;
  top: calc(100% + 6px);
  right: 8px;
  z-index: 10;
  min-width: 108px;
  padding: 6px;
  border: 1px solid var(--app-line);
  border-radius: 18px;
  background: #ffffff;
  box-shadow: var(--app-shadow-strong);
}

.menu-panel button {
  width: 100%;
  padding: 8px 10px;
  border: none;
  border-radius: 10px;
  background: transparent;
  text-align: left;
  color: #243b53;
  cursor: pointer;
}

.menu-panel button:hover {
  background: #ffffff;
}

.menu-panel .danger {
  color: #c2410c;
}

.dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: grid;
  place-items: center;
  background: rgba(9, 19, 33, 0.46);
}

.dialog-card {
  width: min(92vw, 340px);
  padding: 18px;
  border-radius: 24px;
  background: #fff;
  box-shadow: 0 28px 70px rgba(15, 23, 42, 0.28);
}

.dialog-card h4 {
  margin: 0 0 10px;
  color: var(--app-text);
}

.dialog-card p {
  margin: 0 0 16px;
  color: var(--app-text-muted);
  line-height: 1.45;
}

.dialog-input {
  width: 100%;
  margin-bottom: 16px;
  padding: 10px 12px;
  border: 1px solid #d9e2ec;
  border-radius: 14px;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.ghost-btn,
.primary-btn,
.danger-btn {
  padding: 8px 12px;
  border: none;
  border-radius: 12px;
  cursor: pointer;
}

.ghost-btn {
  background: #f4f7fb;
  color: #475569;
}

.primary-btn {
  background: var(--app-primary);
  color: #fff;
}

.danger-btn {
  background: #ef4444;
  color: #fff;
}
</style>
