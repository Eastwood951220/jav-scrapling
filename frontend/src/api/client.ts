import axios from "axios";

const client = axios.create({
  baseURL: "/api",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || "请求失败";
    return Promise.reject(new Error(message));
  }
);

export default client;
