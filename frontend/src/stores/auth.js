import { defineStore } from "pinia";

import { loginApi, meApi, registerApi } from "../api/auth";
import { clearAuthSession, getAccessToken, getUserRole, setAuthSession, setStoredUserRole } from "../utils/authStorage";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null,
    token: getAccessToken() || "",
    role: getUserRole() || "",
  }),
  actions: {
    async login(payload) {
      const { data } = await loginApi(payload);
      this.token = data.access_token;
      this.user = data.user;
      this.role = data.user?.role || "";
      setAuthSession(data.access_token, this.role);
    },
    async register(payload) {
      const { data } = await registerApi(payload);
      this.token = data.access_token;
      this.user = data.user;
      this.role = data.user?.role || "";
      setAuthSession(data.access_token, this.role);
    },
    async fetchMe() {
      if (!this.token) return;
      const { data } = await meApi();
      this.user = data;
      this.role = data?.role || "";
      setStoredUserRole(this.role);
    },
    logout() {
      this.user = null;
      this.token = "";
      this.role = "";
      clearAuthSession();
    },
  },
});
