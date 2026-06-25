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
