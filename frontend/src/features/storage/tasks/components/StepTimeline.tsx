import { Space, Tag, Timeline, Typography } from "antd";
import { stepLabels } from "../constants";
import type { Task } from "../types";

const ALL_STEPS = [
  "prepare",
  "submit_magnet",
  "waiting_download",
  "scan_files",
  "select_videos",
  "rename_files",
  "move_files",
  "verify_result",
  "cleanup_files",
  "completed",
];

const STEP_STATUS_COLORS: Record<string, string> = {
  pending: "gray",
  running: "blue",
  success: "green",
  failed: "red",
  skipped: "default",
};

const STEP_STATUS_LABELS: Record<string, string> = {
  pending: "待执行",
  running: "执行中",
  success: "成功",
  failed: "失败",
  skipped: "跳过",
};

function formatTime(value?: string | null): string {
  return value ? new Date(value).toLocaleString() : "-";
}

function formatDuration(seconds?: number): string {
  if (seconds == null) return "-";
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

export default function StepTimeline({ task }: { task: Task }) {
  if (task.steps && task.steps.length > 0) {
    return (
      <Timeline
        items={task.steps.map((step) => ({
          color: STEP_STATUS_COLORS[step.status] || "gray",
          children: (
            <div>
              <Space>
                <Typography.Text strong>{stepLabels[step.name] || step.name}</Typography.Text>
                <Tag color={STEP_STATUS_COLORS[step.status]}>{STEP_STATUS_LABELS[step.status]}</Tag>
                {step.attempt != null && step.attempt > 1 && (
                  <Typography.Text type="secondary">尝试 #{step.attempt}</Typography.Text>
                )}
              </Space>
              <div style={{ marginTop: 4 }}>
                {step.started_at && (
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    开始: {formatTime(step.started_at)}
                  </Typography.Text>
                )}
                {step.completed_at && (
                  <Typography.Text type="secondary" style={{ fontSize: 12, marginLeft: 12 }}>
                    结束: {formatTime(step.completed_at)}
                  </Typography.Text>
                )}
                {step.duration_seconds != null && (
                  <Typography.Text type="secondary" style={{ fontSize: 12, marginLeft: 12 }}>
                    耗时: {formatDuration(step.duration_seconds)}
                  </Typography.Text>
                )}
              </div>
              {step.error && (
                <Typography.Text type="danger" style={{ fontSize: 12, display: "block", marginTop: 4 }}>
                  {step.error}
                </Typography.Text>
              )}
            </div>
          ),
        }))}
      />
    );
  }

  const currentIdx = ALL_STEPS.indexOf(task.current_step);
  const failedIdx = task.failed_step ? ALL_STEPS.indexOf(task.failed_step) : -1;

  return (
    <Timeline
      items={ALL_STEPS.map((stepName, idx) => {
        let status: string;
        if (task.status === "completed" && stepName === "completed") {
          status = "success";
        } else if (failedIdx >= 0 && idx === failedIdx) {
          status = "failed";
        } else if (failedIdx >= 0 && idx > failedIdx) {
          status = "pending";
        } else if (idx < currentIdx) {
          status = "success";
        } else if (idx === currentIdx) {
          status = task.status === "running" ? "running" : "success";
        } else {
          status = "pending";
        }

        return {
          color: STEP_STATUS_COLORS[status],
          children: (
            <Space>
              <Typography.Text>{stepLabels[stepName] || stepName}</Typography.Text>
              <Tag color={STEP_STATUS_COLORS[status]}>{STEP_STATUS_LABELS[status]}</Tag>
            </Space>
          ),
        };
      })}
    />
  );
}
