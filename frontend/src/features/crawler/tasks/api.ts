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

export function deleteTask(id: string, mode: "normal" | "complete" = "normal"): Promise<{ deleted: boolean; mode: string; movies_affected: number; magnets_deleted: number }> {
  return client.delete(`/crawler/tasks/${id}`, { params: { mode } }).then((res) => res.data);
}

export function runTask(id: string): Promise<TaskRun> {
  return client.post(`/crawler/tasks/${id}/run`).then((res) => res.data);
}

export function extractName(url: string, url_type: string): Promise<{ name: string }> {
  return client.post("/crawler/tasks/extract-name", { url, url_type }).then((res) => res.data);
}
