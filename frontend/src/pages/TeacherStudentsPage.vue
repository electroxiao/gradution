<template>
  <section class="students-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Students</p>
        <h2>学生薄弱点</h2>
        <p class="page-copy">按学生查看当前未掌握节点，快速了解谁卡在什么知识点上。</p>
      </div>
    </header>

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <div class="students-layout">
      <aside class="student-list">
        <button
          v-for="student in students"
          :key="student.id"
          class="student-item"
          :class="{ active: student.id === activeStudentId }"
          @click="selectStudent(student.id)"
        >
          <strong>{{ student.username }}</strong>
          <span>{{ student.weak_point_count }} 个薄弱点</span>
        </button>
      </aside>

      <section class="student-detail">
        <div v-if="activeStudent" class="detail-header">
          <div>
            <h3>{{ activeStudent.username }}</h3>
            <p>当前未掌握 {{ studentWeakPoints.length }} 个节点</p>
          </div>
        </div>

        <div v-if="studentWeakPoints.length" class="weak-cards">
          <article v-for="item in studentWeakPoints" :key="item.id" class="weak-card">
            <strong>{{ item.node_name }}</strong>
            <span>最近出现 {{ formatDate(item.last_seen_at) }}</span>
          </article>
        </div>
        <div v-else class="empty">该学生当前没有未掌握薄弱点。</div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { listTeacherStudentWeakPointsApi, listTeacherStudentsApi } from "../api/teacher";
import { clearAuthSession } from "../utils/authStorage";

const router = useRouter();
const students = ref([]);
const activeStudentId = ref(null);
const studentWeakPoints = ref([]);
const errorMessage = ref("");

const activeStudent = computed(() =>
  students.value.find((student) => student.id === activeStudentId.value) || null,
);

onMounted(async () => {
  await loadStudents();
});

async function loadStudents() {
  try {
    const { data } = await listTeacherStudentsApi();
    students.value = data;
    if (students.value.length) {
      await selectStudent(students.value[0].id);
    }
  } catch (error) {
    handleApiError(error, "加载学生列表失败。");
  }
}

async function selectStudent(studentId) {
  activeStudentId.value = studentId;
  try {
    const { data } = await listTeacherStudentWeakPointsApi(studentId);
    studentWeakPoints.value = data;
  } catch (error) {
    handleApiError(error, "加载学生薄弱点失败。");
  }
}

function formatDate(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
  });
}

function handleApiError(error, fallbackMessage) {
  const status = error?.response?.status;
  if (status === 401 || status === 403) {
    clearAuthSession();
    router.push("/login");
    return;
  }
  errorMessage.value = error?.response?.data?.detail || fallbackMessage;
}
</script>

<style scoped>
.students-page {
  display: grid;
  gap: 22px;
}

.page-header h2 {
  margin: 8px 0 10px;
  font-size: 34px;
  color: #0f2840;
}

.eyebrow {
  margin: 0;
  color: #5b86b3;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.page-copy {
  margin: 0;
  color: #6f8297;
}

.students-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 18px;
}

.student-list,
.student-detail {
  border: 1px solid #e2ebf4;
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.06);
}

.student-list {
  padding: 14px;
  display: grid;
  gap: 8px;
  align-self: start;
}

.student-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px;
  border: none;
  border-radius: 18px;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.student-item strong {
  color: #15314a;
}

.student-item span {
  color: #7990a8;
  font-size: 13px;
}

.student-item.active {
  background: #eff6ff;
}

.student-detail {
  padding: 20px 22px;
}

.detail-header h3 {
  margin: 0;
  font-size: 26px;
  color: #10283d;
}

.detail-header p {
  margin: 6px 0 0;
  color: #6f8297;
}

.weak-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
  margin-top: 18px;
}

.weak-card,
.feedback.error,
.empty {
  padding: 18px;
  border-radius: 20px;
  background: #f8fbff;
  color: #5f7287;
}

.weak-card strong {
  display: block;
  margin-bottom: 8px;
  color: #16314a;
  font-size: 18px;
}

.feedback.error {
  background: #fff8f8;
  color: #b42318;
}

@media (max-width: 960px) {
  .students-layout {
    grid-template-columns: 1fr;
  }
}
</style>
