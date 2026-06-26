import client from "@/shared/api/client";

export interface StorageTask {
  _id: string;
  task_id: string;
  movie_id: string;
  code: string;
  title: string;
  source: string;
  status: string;
  current_step: string;
  failed_step: string | null;
  retryable: boolean;
  magnet: { url: string; info_hash: string; size: string; size_bytes: number };
  download: { progress: number; status: string };
  target_folder: string;
  retry: { step_attempt: number; total_attempts: number; max_step_retries: number };
  error: { code: string | null; message: string | null };
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface StorageTaskListResponse {
  items: StorageTask[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface StorageTaskStats {
  pending: number;
  waiting_download: number;
  running: number;
  waiting_retry: number;
  failed: number;
  completed: number;
}

export function fetchStorageTasks(params?: Record<string, unknown>): Promise<StorageTaskListResponse> {
  return client.get("/storage/tasks", { params }).then((res) => res.data);
}

export function fetchStorageTaskStats(): Promise<StorageTaskStats> {
  return client.get("/storage/tasks/stats").then((res) => res.data);
}

export function retryStorageTask(taskId: string): Promise<void> {
  return client.post(`/storage/tasks/${taskId}/retry`).then(() => undefined);
}

export function cancelStorageTask(taskId: string): Promise<void> {
  return client.post(`/storage/tasks/${taskId}/cancel`).then(() => undefined);
}

export function deleteStorageTask(taskId: string): Promise<void> {
  return client.delete(`/storage/tasks/${taskId}`).then(() => undefined);
}

export function batchRetryStorageTasks(taskIds: string[]): Promise<{ retried: number; skipped: number }> {
  return client.post("/storage/tasks/batch-retry", { task_ids: taskIds }).then((res) => res.data);
}

export function batchCancelStorageTasks(taskIds: string[]): Promise<{ cancelled: number }> {
  return client.post("/storage/tasks/batch-cancel", { task_ids: taskIds }).then((res) => res.data);
}

export function batchDeleteStorageTasks(taskIds: string[]): Promise<{ deleted: number }> {
  return client.post("/storage/tasks/batch", { task_ids: taskIds }).then((res) => res.data);
}

export const statusColors: Record<string, string> = {
  pending: "default",
  running: "processing",
  waiting_download: "processing",
  waiting_retry: "warning",
  retryable: "warning",
  completed: "success",
  failed: "error",
  cancelled: "default",
};

export const statusLabels: Record<string, string> = {
  pending: "待处理",
  running: "运行中",
  waiting_download: "等待下载",
  waiting_retry: "等待重试",
  retryable: "可重试",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

export const stepLabels: Record<string, string> = {
  prepare: "准备任务",
  submit_magnet: "提交磁力",
  waiting_download: "云端下载",
  scan_files: "扫描文件",
  select_videos: "识别主视频",
  rename_files: "重命名",
  move_files: "移动文件",
  verify_result: "校验结果",
  cleanup_files: "清理临时文件",
  completed: "完成",
};
