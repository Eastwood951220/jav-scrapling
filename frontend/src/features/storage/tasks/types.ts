export interface TaskStep {
  name: string;
  status: "pending" | "running" | "success" | "failed" | "skipped";
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  attempt?: number;
  error?: string;
}

export interface TaskFile {
  filename: string;
  path: string;
  size?: number;
  extension?: string;
  category?: string;
  result?: string;
}

export interface Task {
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
  magnet: { url: string; info_hash: string; size: string; size_bytes: number; selected_reason?: string };
  download: { progress: number; status: string };
  target_folder: string;
  retry: { step_attempt: number; total_attempts: number; max_step_retries: number };
  error: { code: string | null; message: string | null };
  created_at: string;
  started_at?: string | null;
  updated_at: string;
  completed_at: string | null;
  steps?: TaskStep[];
  scanned_files?: TaskFile[];
  final_files?: string[];
}

export interface TaskListResponse {
  items: Task[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface TaskStats {
  pending: number;
  waiting_download: number;
  running: number;
  waiting_retry: number;
  failed: number;
  completed: number;
}

export interface TaskLogEntry {
  timestamp: string;
  level: string;
  step?: string;
  message: string;
  data?: Record<string, unknown>;
}
