import client from "@/shared/api/client";
import type { CrawlTask, TaskCreatePayload } from "./types";
import type { TaskRun } from "@/features/runs/types";

export type { CrawlTask, TaskCreatePayload, FilterConfig } from "./types";

export function fetchTasks(): Promise<CrawlTask[]> {
  return client.get("/tasks").then((res) => res.data);
}

export function fetchTask(id: string): Promise<CrawlTask> {
  return client.get(`/tasks/${id}`).then((res) => res.data);
}

export function createTask(data: TaskCreatePayload): Promise<CrawlTask> {
  return client.post("/tasks", data).then((res) => res.data);
}

export function updateTask(id: string, data: Partial<TaskCreatePayload>): Promise<CrawlTask> {
  return client.put(`/tasks/${id}`, data).then((res) => res.data);
}

export function deleteTask(id: string): Promise<{ deleted: boolean }> {
  return client.delete(`/tasks/${id}`).then((res) => res.data);
}

export function runTask(id: string): Promise<TaskRun> {
  return client.post(`/tasks/${id}/run`).then((res) => res.data);
}
