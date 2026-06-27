import type { RunStatus } from "@/shared/types/common";

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
  | "save_failed"
  | "skipped";

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
