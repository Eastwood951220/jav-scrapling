import client from "@/shared/api/client";
import type { PaginatedResponse } from "@/shared/types/common";
import type { TaskRun, QueueStatus, RunDetailTask } from "./types";

export { statusColors, statusLabels, detailTaskStatusColors, detailTaskStatusLabels } from "./types";
export type { TaskRun, QueueStatus, RunLogEntry, RunDetailTask, DetailTaskStatus } from "./types";

export function fetchRuns(params?: {
  status?: string;
  page?: number;
  limit?: number;
}): Promise<PaginatedResponse<TaskRun>> {
  return client.get("/runs", { params }).then((res) => res.data);
}

export function fetchRun(id: string): Promise<TaskRun> {
  return client.get(`/runs/${id}`).then((res) => res.data);
}

export function fetchQueueStatus(): Promise<QueueStatus> {
  return client.get("/runs/queue-status").then((res) => res.data);
}

export function stopRun(id: string): Promise<{ success: boolean; message: string }> {
  return client.post(`/runs/${id}/stop`).then((res) => res.data);
}

export function deleteRun(id: string): Promise<{ deleted: boolean }> {
  return client.delete(`/runs/${id}`).then((res) => res.data);
}

export function fetchRunDetailTasks(
  runId: string,
  params?: { page?: number; limit?: number },
): Promise<{ items: RunDetailTask[]; total: number; page: number; limit: number; total_pages: number }> {
  return client.get(`/runs/${runId}/tasks`, { params }).then((res) => res.data);
}

export function retryCrawl(runId: string, taskId: string): Promise<{ success: boolean; message?: string }> {
  return client.post(`/runs/${runId}/tasks/${taskId}/retry-crawl`).then((res) => res.data);
}

export function retrySave(runId: string, taskId: string): Promise<{ success: boolean; message?: string }> {
  return client.post(`/runs/${runId}/tasks/${taskId}/retry-save`).then((res) => res.data);
}
