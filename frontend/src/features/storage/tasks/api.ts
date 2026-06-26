import client from "@/shared/api/client";
import type {
  Task,
  TaskListResponse,
  TaskLogEntry,
  TaskStats,
} from "./types";

function mapTask(raw: Record<string, unknown>): Task {
  return {
    ...raw,
    // Field name mappings: backend → frontend
    code: raw.code ?? raw.movie_code ?? "",
    current_step: raw.current_step ?? raw.step ?? "",
    target_folder: raw.target_folder ?? raw.target_path ?? "",
    failed_step: raw.failed_step ?? raw.step ?? null,
    // Magnet info: backend stores flat, frontend expects nested
    magnet: raw.magnet ?? {
      url: raw.magnet_url ?? "",
      info_hash: raw.info_hash ?? "",
      size: raw.size ?? "",
      size_bytes: raw.size_bytes ?? 0,
    },
    // Download: progress is already 0-100 in backend
    download: raw.download ?? {
      progress: raw.progress ?? 0,
      status: raw.download_status ?? "",
    },
    // Retry info
    retry: raw.retry ?? {
      step_attempt: 0,
      total_attempts: raw.retry_count ?? 0,
      max_step_retries: raw.max_retries ?? 3,
    },
  } as Task;
}

export function fetchTasks(params?: Record<string, unknown>): Promise<TaskListResponse> {
  return client.get("/storage/tasks", { params }).then((res) => ({
    ...res.data,
    items: res.data.items.map(mapTask),
  }));
}

export function fetchTask(taskId: string): Promise<Task> {
  return client.get(`/storage/tasks/${taskId}`).then((res) => mapTask(res.data));
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

export async function batchCancelTasks(taskIds: string[]): Promise<{ cancelled: number }> {
  const res = await client.post("/storage/tasks/batch-cancel", {task_ids: taskIds});
  return res.data;
}

export function batchDeleteTasks(taskIds: string[]): Promise<{ deleted: number }> {
  return client.post("/storage/tasks/batch", { task_ids: taskIds }).then((res) => res.data);
}
