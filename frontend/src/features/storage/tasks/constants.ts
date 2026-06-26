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

export const logLevelColors: Record<string, string> = {
  INFO: "blue",
  WARNING: "orange",
  ERROR: "red",
};
