import { defineStore } from "pinia";

import { loginApi, meApi, registerApi } from "../api/auth";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null,
    token: localStorage.getItem("access_token") || "",
    role: localStorage.getItem("user_role") || "",
  }),
  actions: {
    async login(payload) {
      const { data } = await loginApi(payload);
      this.token = data.access_token;
      this.user = data.user;
      this.role = data.user?.role || "";
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("user_role", this.role);
    },
    async register(payload) {
      const { data } = await registerApi(payload);
      this.token = data.access_token;
      this.user = data.user;
      this.role = data.user?.role || "";
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("user_role", this.role);
    },
    async fetchMe() {
      if (!this.token) return;
      const { data } = await meApi();
      this.user = data;
      this.role = data?.role || "";
      localStorage.setItem("user_role", this.role);
    },
    logout() {
      this.user = null;
      this.token = "";
      this.role = "";
      localStorage.removeItem("access_token");
      localStorage.removeItem("user_role");
    },
  },
});
