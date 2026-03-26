import { createRouter, createWebHistory } from "vue-router";

import ChatPage from "../pages/ChatPage.vue";
import LoginPage from "../pages/LoginPage.vue";
import WeakPointsPage from "../pages/WeakPointsPage.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: LoginPage, meta: { public: true } },
    { path: "/", component: ChatPage },
    { path: "/weak-points", component: WeakPointsPage },
  ],
});

router.beforeEach((to) => {
  const token = localStorage.getItem("access_token");
  if (!to.meta.public && !token) {
    return "/login";
  }
  if (to.path === "/login" && token) {
    return "/";
  }
  return true;
});

export default router;
