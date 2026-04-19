import axios from "axios";
import { getAccessToken } from "../utils/authStorage";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:9000";

const http = axios.create({
  baseURL: API_BASE_URL,
});

http.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default http;
