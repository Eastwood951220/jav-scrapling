import client from "./client";

export interface RunLogEntry {
  timestamp: string;
  level: string;
  message: string;
}

export interface TaskRun {
  _id: string;
  task_id: string;
  task_name: string | null;
  status: "queued" | "running" | "completed" | "failed";
  queued_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
  logs: RunLogEntry[];
}

export interface RunListResponse {
  items: TaskRun[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface QueueStatus {
  queue_size: number;
  is_running: boolean;
  current_run_id: string | null;
}

export function fetchRuns(params?: {
  status?: string;
  page?: number;
  limit?: number;
}): Promise<RunListResponse> {
  return client.get("/runs", { params }).then((res) => res.data);
}

export function fetchRun(id: string): Promise<TaskRun> {
  return client.get(`/runs/${id}`).then((res) => res.data);
}

export function fetchQueueStatus(): Promise<QueueStatus> {
  return client.get("/runs/queue-status").then((res) => res.data);
}
