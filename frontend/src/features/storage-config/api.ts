import client from "@/shared/api/client";

export interface StorageConfig {
  enabled: boolean;
  grpc_host: string;
  api_token_configured: boolean;
  api_token_masked: string;
  request_timeout_seconds: number;
  connect_timeout_seconds: number;
  download_root_folder: string;
  target_folder: string;
  use_task_subfolder: boolean;
  auto_create_target_folder: boolean;
  single_filename_template: string;
  multi_filename_template: string;
  operation_delay_min: number;
  operation_delay_max: number;
  download_poll_interval_min: number;
  download_poll_interval_max: number;
  retry_delay_min: number;
  retry_delay_max: number;
  max_step_retries: number;
  minimum_video_size_mb: number;
  video_extensions: string[];
  excluded_filename_keywords: string[];
  keep_subtitles: boolean;
  keep_cover_images: boolean;
  delete_empty_folders: boolean;
}

export interface StorageTestResult {
  connection: boolean;
  token_valid: boolean;
  temp_dir_exists: boolean;
  target_dir_exists: boolean;
  download_capable: boolean;
  file_ops_capable: boolean;
  message: string;
}

export function fetchStorageConfig(): Promise<StorageConfig> {
  return client.get("/storage/config").then((res) => res.data);
}

export function updateStorageConfig(
  config: Partial<StorageConfig>,
): Promise<void> {
  return client.put("/storage/config", config).then(() => undefined);
}

export function testStorageConnection(): Promise<StorageTestResult> {
  return client.post("/storage/config/test").then((res) => res.data);
}
