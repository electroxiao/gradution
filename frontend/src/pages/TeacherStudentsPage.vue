<template>
  <section v-if="!isInitialLoading" class="students-page content-ready">
    <PageHeader title="学生薄弱点" title-tag="h2" />

    <p v-if="errorMessage" class="feedback error">{{ errorMessage }}</p>

    <section v-if="consultationHotspots.length" class="detail-section hotspot-section">
      <div class="section-head">
        <h4>班级咨询热点</h4>
        <span>聊天关注点，不等同薄弱点</span>
      </div>
      <div class="weak-cards">
        <article
          v-for="item in consultationHotspots"
          :key="item.knowledge_node_id"
          class="weak-card consultation-card"
        >
          <strong>{{ item.node_name }}</strong>
          <span>{{ item.student_count }} 人 · {{ item.mention_count }} 次</span>
        </article>
      </div>
    </section>

    <div class="students-layout">
      <aside class="student-list">
        <template v-if="!isStudentsLoading">
          <button
            v-for="student in students"
            :key="student.id"
            class="student-item"
            :class="{ active: student.id === activeStudentId }"
            @click="selectStudent(student.id)"
          >
            <strong>{{ student.username }}</strong>
            <span>{{ student.class_name || "未分班" }} · {{ student.weak_point_count }} 个薄弱点</span>
          </button>
        </template>
      </aside>

      <section class="student-detail">
        <div v-if="!isStudentsLoading && activeStudent" class="detail-header">
          <div>
            <h3>{{ activeStudent.username }}</h3>
            <p>{{ activeStudent.class_name || "未分班" }} · 当前未掌握 {{ studentWeakPoints.length }} 个节点</p>
          </div>
        </div>

        <section class="detail-section">
          <div class="section-head">
            <h4>当前未掌握节点</h4>
            <span>{{ studentWeakPoints.length }} 个</span>
          </div>
          <div v-if="!isStudentsLoading && !isWeakPointsLoading && studentWeakPoints.length" class="weak-cards">
            <article v-for="item in studentWeakPoints" :key="item.id" class="weak-card">
              <strong>{{ item.node_name }}</strong>
              <span>最近出现 {{ formatDate(item.last_seen_at) }}</span>
            </article>
          </div>
          <div v-else-if="hasStudentsLoaded" class="empty">该学生当前没有未掌握薄弱点。</div>
        </section>

        <section class="detail-section">
          <div class="section-head">
            <h4>最近咨询知识点</h4>
            <span>{{ studentConsultations.length }} 个</span>
          </div>
          <div v-if="!isStudentsLoading && !isWeakPointsLoading && studentConsultations.length" class="weak-cards">
            <article
              v-for="item in studentConsultations"
              :key="item.knowledge_node_id"
              class="weak-card consultation-card"
            >
              <strong>{{ item.node_name }}</strong>
              <span>{{ item.mention_count }} 次咨询</span>
            </article>
          </div>
          <div v-else-if="hasStudentsLoaded" class="empty">该学生暂时没有聊天咨询知识点记录。</div>
        </section>

      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import {
  listTeacherConsultationHotspotsApi,
  listTeacherStudentConsultationsApi,
  listTeacherStudentWeakPointsApi,
  listTeacherStudentsApi,
} from "../api/teacher";
import PageHeader from "../components/PageHeader.vue";
import { clearAuthSession } from "../utils/authStorage";

const router = useRouter();
const students = ref([]);
const activeStudentId = ref(null);
const studentWeakPoints = ref([]);
const consultationHotspots = ref([]);
const studentConsultations = ref([]);
const errorMessage = ref("");
const isInitialLoading = ref(true);
const isStudentsLoading = ref(true);
const hasStudentsLoaded = ref(false);
const isWeakPointsLoading = ref(false);
let activeRequestId = 0;

const activeStudent = computed(() =>
  students.value.find((student) => student.id === activeStudentId.value) || null,
);

onMounted(async () => {
  await loadStudents();
});

async function loadStudents() {
  isStudentsLoading.value = true;
  try {
    const [studentsResponse, hotspotsResponse] = await Promise.all([
      listTeacherStudentsApi(),
      listTeacherConsultationHotspotsApi({ limit: 8 }),
    ]);
    students.value = studentsResponse.data;
    consultationHotspots.value = hotspotsResponse.data || [];
    if (students.value.length) {
      await selectStudent(students.value[0].id);
    }
  } catch (error) {
    handleApiError(error, "加载学生列表失败。");
  } finally {
    hasStudentsLoaded.value = true;
    isStudentsLoading.value = false;
    isInitialLoading.value = false;
  }
}

async function selectStudent(studentId) {
  const requestId = ++activeRequestId;
  activeStudentId.value = studentId;
  studentWeakPoints.value = [];
  studentConsultations.value = [];
  isWeakPointsLoading.value = true;
  errorMessage.value = "";

  try {
    const [weakPointsResponse, consultationsResponse] = await Promise.all([
      listTeacherStudentWeakPointsApi(studentId),
      listTeacherStudentConsultationsApi(studentId, 12),
    ]);
    if (requestId !== activeRequestId) return;
    studentWeakPoints.value = weakPointsResponse.data;
    studentConsultations.value = consultationsResponse.data || [];
  } catch (error) {
    if (requestId === activeRequestId) {
      handleApiError(error, "加载学生知识画像失败。");
    }
    return;
  } finally {
    if (requestId === activeRequestId) {
      isWeakPointsLoading.value = false;
    }
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
  gap: 16px;
  font-size: var(--compact-body);
}

.students-layout {
  display: grid;
  grid-template-columns: minmax(210px, 240px) minmax(0, 1fr);
  gap: 14px;
}

.student-list,
.student-detail {
  border: 1px solid var(--app-line);
  border-radius: var(--app-radius-xl);
  background: var(--app-panel);
  box-shadow: var(--app-shadow);
}

.student-list {
  padding: 12px;
  display: grid;
  gap: 8px;
  align-self: start;
}

.student-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: #ffffff;
  text-align: left;
  cursor: pointer;
}

.student-item strong {
  color: var(--app-text);
  font-weight: 400;
}

.student-item span {
  color: var(--app-text-muted);
  font-size: var(--compact-caption);
}

.student-item.active {
  background: var(--app-primary-soft);
  border-color: #cfdcf3;
}

.student-detail {
  padding: 16px;
  display: grid;
  gap: 14px;
  align-self: start;
  align-content: start;
}

.detail-header h3 {
  margin: 0;
  font-size: var(--compact-section-title);
  font-weight: 500;
  color: var(--app-text);
}

.detail-header p,
.section-head span {
  margin: 6px 0 0;
  color: var(--app-text-muted);
}

.detail-section {
  display: grid;
  gap: 10px;
  align-content: start;
}

.section-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.section-head h4 {
  margin: 0;
  color: var(--app-text);
  font-size: 15px;
  font-weight: 500;
}

.weak-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
  min-width: 0;
  align-items: start;
  align-content: start;
}

.weak-card,
.feedback.error,
.empty {
  padding: 12px;
  border-radius: 8px;
  background: #ffffff;
  color: var(--app-text-muted);
}

.weak-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px 12px;
  align-items: center;
  border: 1px solid #edf1f6;
}

.weak-card strong {
  min-width: 0;
  color: var(--app-text);
  font-weight: 400;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.weak-card span {
  justify-self: end;
  color: var(--app-text-muted);
  font-size: var(--compact-caption);
  white-space: nowrap;
}

.feedback.error {
  background: #fff5f5;
  color: #b42318;
  border: 1px solid #f0d3d3;
}

.hotspot-section {
  padding: 16px;
  border: 1px solid var(--app-line);
  border-radius: var(--app-radius-xl);
  background: var(--app-panel);
  box-shadow: var(--app-shadow);
}

.consultation-card {
  border-color: #dbeafe;
  background: #f8fbff;
}

@media (max-width: 960px) {
  .students-layout {
    grid-template-columns: minmax(180px, 220px) minmax(0, 1fr);
  }
}

@media (max-width: 680px) {
  .students-layout {
    grid-template-columns: 1fr;
  }

  .weak-card {
    grid-template-columns: 1fr;
  }

  .weak-card span {
    justify-self: start;
    white-space: normal;
  }
}
</style>
