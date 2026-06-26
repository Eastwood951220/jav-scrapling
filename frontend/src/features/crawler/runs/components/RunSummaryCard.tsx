import { Button, Card, Descriptions, Space, Tag, Typography } from "antd";
import { statusColors, statusLabels } from "../constants";
import type { TaskRun } from "../types";
import styles from "@/shared/styles/pages.module.css";

interface RunSummaryCardProps {
  run: TaskRun;
  isActive: boolean;
  onStop: (run: TaskRun) => void;
}

function formatTime(value?: string | null): string {
  return value ? new Date(value).toLocaleString() : "-";
}

export default function RunSummaryCard({ run, isActive, onStop }: RunSummaryCardProps) {
  return (
    <Card className={styles.detailCard}>
      <Descriptions title="运行详情" bordered column={2} size="small">
        <Descriptions.Item label="任务名称">{run.task_name || "-"}</Descriptions.Item>
        <Descriptions.Item label="状态">
          <Space>
            <Tag color={statusColors[run.status]}>
              {statusLabels[run.status]}
              {isActive && "..."}
            </Tag>
            {run.status === "running" && (
              <Button danger size="small" onClick={() => onStop(run)}>
                停止任务
              </Button>
            )}
          </Space>
        </Descriptions.Item>
        <Descriptions.Item label="排队时间">{formatTime(run.queued_at)}</Descriptions.Item>
        <Descriptions.Item label="开始时间">{formatTime(run.started_at)}</Descriptions.Item>
        <Descriptions.Item label="完成时间">{formatTime(run.finished_at)}</Descriptions.Item>
        <Descriptions.Item label="任务ID">
          <Typography.Text code>{run.task_id}</Typography.Text>
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
}
