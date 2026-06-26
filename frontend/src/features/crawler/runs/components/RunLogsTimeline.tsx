import { Timeline, Typography } from "antd";
import { logLevelColors } from "../constants";
import type { RunLogEntry } from "../types";

interface RunLogsTimelineProps {
  logs: RunLogEntry[];
  isActive: boolean;
}

export default function RunLogsTimeline({ logs, isActive }: RunLogsTimelineProps) {
  if (logs.length === 0) {
    return (
      <Typography.Text type="secondary">
        {isActive ? "等待日志..." : "无日志"}
      </Typography.Text>
    );
  }

  return (
    <Timeline
      items={logs.slice().reverse().map((entry, idx) => ({
        key: idx,
        color: logLevelColors[entry.level] || "gray",
        children: (
          <div>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {new Date(entry.timestamp).toLocaleTimeString()}
            </Typography.Text>
            <Typography.Text
              type={entry.level === "ERROR" ? "danger" : undefined}
              style={{ marginLeft: 8 }}
            >
              {entry.message}
            </Typography.Text>
          </div>
        ),
      }))}
    />
  );
}
