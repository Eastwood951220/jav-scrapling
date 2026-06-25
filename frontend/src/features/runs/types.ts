import type { RunStatus } from "@/shared/types/common";

/** Display colors for each run status. */
export const statusColors: Record<RunStatus, string> = {
  queued: "default",
  running: "processing",
  completed: "success",
  failed: "error",
  stopped: "warning",
};

/** Chinese labels for each run status. */
export const statusLabels: Record<RunStatus, string> = {
  queued: "排队中",
  running: "运行中",
  completed: "已完成",
  failed: "失败",
  stopped: "已停止",
};

/** A single log entry from a task run. */
export interface RunLogEntry {
  timestamp: string;
  level: string;
  message: string;
}

/** A task run document. */
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

/** Queue status response. */
export interface QueueStatus {
  queue_size: number;
  is_running: boolean;
  current_run_id: string | null;
  stop_requested?: boolean;
}

/** Detail-task status values. */
export type DetailTaskStatus =
  | "pending_crawl"
  | "crawled"
  | "crawl_failed"
  | "saved"
  | "save_failed";

/** A single detail task within a run. */
export interface RunDetailTask {
  _id: string;
  run_id: string;
  task_name: string;
  code?: string;
  source_url?: string;
  source_name?: string;
  status: DetailTaskStatus;
  error?: string | null;
  created_at?: string;
  crawled_at?: string;
  saved_at?: string;
}

/** Display colors for each detail-task status. */
export const detailTaskStatusColors: Record<DetailTaskStatus, string> = {
  pending_crawl: "default",
  crawled: "processing",
  crawl_failed: "error",
  saved: "success",
  save_failed: "error",
};

/** Chinese labels for each detail-task status. */
export const detailTaskStatusLabels: Record<DetailTaskStatus, string> = {
  pending_crawl: "待爬取",
  crawled: "已爬取",
  crawl_failed: "爬取失败",
  saved: "已入库",
  save_failed: "入库失败",
};
