import client from "./client";
import type { PaginatedResponse, RunStatus } from "../types/common";

export const statusColors: Record<RunStatus, string> = {
  queued: "default",
  running: "processing",
  completed: "success",
  failed: "error",
};

export const statusLabels: Record<RunStatus, string> = {
  queued: "排队中",
  running: "运行中",
  completed: "已完成",
  failed: "失败",
};

export interface RunLogEntry {
  timestamp: string;
  level: string;
  message: string;
}

export interface TaskRun {
  _id: string;
  task_id: string;
  task_name: string | null;
  status: RunStatus;
  queued_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  /** Dynamic result payload — shape varies by task type. */
  result: Record<string, unknown> | null;
  error: string | null;
  logs: RunLogEntry[];
}

export interface QueueStatus {
  queue_size: number;
  is_running: boolean;
  current_run_id: string | null;
  stop_requested?: boolean;
}

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
