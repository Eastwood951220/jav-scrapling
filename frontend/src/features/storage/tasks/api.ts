import client from "@/shared/api/client";
import type {
  Task,
  TaskListResponse,
  TaskLogEntry,
  TaskStats,
} from "./types";

export function fetchTasks(params?: Record<string, unknown>): Promise<TaskListResponse> {
  return client.get("/storage/tasks", { params }).then((res) => res.data);
}

export function fetchTask(taskId: string): Promise<Task> {
  return client.get(`/storage/tasks/${taskId}`).then((res) => res.data);
}

export function fetchTaskLogs(taskId: string): Promise<TaskLogEntry[]> {
  return client.get(`/storage/tasks/${taskId}/logs`).then((res) => res.data.logs ?? []);
}

export function fetchTaskStats(): Promise<TaskStats> {
  return client.get("/storage/tasks/stats").then((res) => res.data);
}

export function retryTask(taskId: string): Promise<void> {
  return client.post(`/storage/tasks/${taskId}/retry`).then(() => undefined);
}

export function cancelTask(taskId: string): Promise<void> {
  return client.post(`/storage/tasks/${taskId}/cancel`).then(() => undefined);
}

export function deleteTask(taskId: string): Promise<void> {
  return client.delete(`/storage/tasks/${taskId}`).then(() => undefined);
}

export function batchRetryTasks(taskIds: string[]): Promise<{ retried: number; skipped: number }> {
  return client.post("/storage/tasks/batch-retry", { task_ids: taskIds }).then((res) => res.data);
}

export function batchCancelTasks(taskIds: string[]): Promise<{ cancelled: number }> {
  return client.post("/storage/tasks/batch-cancel", { task_ids: taskIds }).then((res) => res.data);
}

export function batchDeleteTasks(taskIds: string[]): Promise<{ deleted: number }> {
  return client.post("/storage/tasks/batch", { task_ids: taskIds }).then((res) => res.data);
}
