import { defineStore } from "pinia";

import { loginApi, meApi, registerApi } from "../api/auth";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null,
    token: localStorage.getItem("access_token") || "",
  }),
  actions: {
    async login(payload) {
      const { data } = await loginApi(payload);
      this.token = data.access_token;
      this.user = data.user;
      localStorage.setItem("access_token", data.access_token);
    },
    async register(payload) {
      const { data } = await registerApi(payload);
      this.token = data.access_token;
      this.user = data.user;
      localStorage.setItem("access_token", data.access_token);
    },
    async fetchMe() {
      if (!this.token) return;
      const { data } = await meApi();
      this.user = data;
    },
    logout() {
      this.user = null;
      this.token = "";
      localStorage.removeItem("access_token");
    },
  },
});
