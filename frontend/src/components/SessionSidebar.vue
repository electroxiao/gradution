<template>
  <aside class="card sidebar">
    <div class="sidebar-header">
      <h3>对话列表</h3>
      <button @click="$emit('create-session')">新建</button>
    </div>
    <button
      v-for="session in sessions"
      :key="session.id"
      class="session-item"
      :class="{ active: session.id === activeSessionId }"
      @click="$emit('select-session', session.id)"
    >
      {{ session.title }}
    </button>
  </aside>
</template>

<script setup>
defineProps({
  sessions: { type: Array, default: () => [] },
  activeSessionId: { type: Number, default: null },
});

defineEmits(["create-session", "select-session"]);
</script>

<style scoped>
.sidebar {
  padding: 16px;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.session-item {
  width: 100%;
  margin-top: 8px;
  padding: 10px 12px;
  border: none;
  border-radius: 10px;
  text-align: left;
  background: #eef4ff;
}

.session-item.active {
  background: #cfe1ff;
}
</style>
