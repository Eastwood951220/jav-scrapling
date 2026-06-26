import client from "@/shared/api/client";
import type { CrawlTask, TaskCreatePayload } from "./types";
import type { TaskRun } from "@/features/crawler/runs/types";

export type { CrawlTask, TaskCreatePayload } from "./types";

export function fetchTasks(): Promise<CrawlTask[]> {
  return client.get("/crawler/tasks").then((res) => res.data);
}

export function fetchTask(id: string): Promise<CrawlTask> {
  return client.get(`/crawler/tasks/${id}`).then((res) => res.data);
}

export function createTask(data: TaskCreatePayload): Promise<CrawlTask> {
  return client.post("/crawler/tasks", data).then((res) => res.data);
}

export function updateTask(id: string, data: Partial<TaskCreatePayload>): Promise<CrawlTask> {
  return client.put(`/crawler/tasks/${id}`, data).then((res) => res.data);
}

export function deleteTask(id: string): Promise<{ deleted: boolean }> {
  return client.delete(`/crawler/tasks/${id}`).then((res) => res.data);
}

export function runTask(id: string): Promise<TaskRun> {
  return client.post(`/crawler/tasks/${id}/run`).then((res) => res.data);
}
