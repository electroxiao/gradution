import axios from "axios";
import { getAccessToken } from "../utils/authStorage";

const http = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

http.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default http;
