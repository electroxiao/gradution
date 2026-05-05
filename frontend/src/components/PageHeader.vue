<template>
  <header class="page-header">
    <div class="page-header-copy">
      <p v-if="eyebrow" class="page-eyebrow">{{ eyebrow }}</p>
      <component :is="titleTag" class="page-title">
        {{ title }}
      </component>
      <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
    </div>

    <div v-if="showStatus || $slots.actions" class="page-header-right">
      <span v-if="showStatus" class="auth-pill" :class="roleClass">
        <span class="auth-dot" />
        <span>{{ roleText }}</span>
      </span>

      <div v-if="$slots.actions" class="page-header-actions">
        <slot name="actions" />
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from "vue";

import { useAuthStore } from "../stores/auth";

const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  subtitle: {
    type: String,
    default: "",
  },
  eyebrow: {
    type: String,
    default: "",
  },
  titleTag: {
    type: String,
    default: "h1",
  },
  showStatus: {
    type: Boolean,
    default: true,
  },
});

const authStore = useAuthStore();

const roleText = computed(() => {
  if (authStore.role === "teacher") return "教师已登录";
  if (authStore.role === "student") return "学生已登录";
  return "已登录";
});

const roleClass = computed(() => {
  if (authStore.role === "teacher") return "teacher";
  if (authStore.role === "student") return "student";
  return "unknown";
});
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.page-header-copy {
  min-width: 0;
  display: grid;
  gap: 6px;
}

.page-eyebrow {
  margin: 0;
  color: #6e86a6;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.page-title {
  margin: 0;
  color: var(--app-text);
  font-size: var(--compact-page-title);
  line-height: 1.08;
  font-weight: 500;
}

.page-subtitle {
  margin: 0;
  color: var(--app-text-muted);
  font-size: var(--compact-body);
  line-height: 1.7;
}

.page-header-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
  margin-left: auto;
}

.auth-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid var(--app-line);
  border-radius: 999px;
  background: #ffffff;
  color: #405571;
  font-size: 13px;
  white-space: nowrap;
}

.auth-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #2f67f6;
}

.auth-pill.teacher .auth-dot {
  background: #1f4fd0;
}

.auth-pill.student .auth-dot {
  background: #0f9f62;
}

.page-header-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

@media (max-width: 640px) {
  .page-header {
    flex-direction: column;
  }

  .page-header-right {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
