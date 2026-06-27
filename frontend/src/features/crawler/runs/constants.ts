import type { RunStatus } from "@/shared/types/common";
import type { DetailTaskStatus } from "./types";

export const statusColors: Record<RunStatus, string> = {
  queued: "default",
  running: "processing",
  completed: "success",
  failed: "error",
  stopped: "warning",
};

export const statusLabels: Record<RunStatus, string> = {
  queued: "排队中",
  running: "运行中",
  completed: "已完成",
  failed: "失败",
  stopped: "已停止",
};

export const detailTaskStatusColors: Record<DetailTaskStatus, string> = {
  pending_crawl: "default",
  crawled: "processing",
  crawl_failed: "error",
  saved: "success",
  save_failed: "error",
  skipped: "warning",
};

export const detailTaskStatusLabels: Record<DetailTaskStatus, string> = {
  pending_crawl: "待爬取",
  crawled: "已爬取",
  crawl_failed: "爬取失败",
  saved: "已入库",
  save_failed: "入库失败",
  skipped: "已跳过",
};

export const logLevelColors: Record<string, string> = {
  INFO: "blue",
  WARNING: "orange",
  ERROR: "red",
};
