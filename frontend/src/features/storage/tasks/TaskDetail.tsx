import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "@tanstack/react-router";
import {
  Button,
  Card,
  Descriptions,
  Progress,
  Space,
  Tag,
  Tooltip,
  Typography,
  message,
} from "antd";
import { ArrowLeftOutlined, CheckOutlined, CopyOutlined } from "@ant-design/icons";
import { fetchTask, fetchTaskLogs } from "./api";
import { statusColors, statusLabels, stepLabels } from "./constants";
import FilesTable from "./components/FilesTable";
import LogsPanel from "./components/LogsPanel";
import StepTimeline from "./components/StepTimeline";
import type { Task, TaskLogEntry } from "./types";
import FullPageSpinner from "@/shared/components/FullPageSpinner";
import { getErrorMessage } from "@/shared/hooks/useErrorMessage";
import { usePolling } from "@/shared/hooks/usePolling";
import styles from "@/shared/styles/pages.module.css";

function formatTime(value?: string | null): string {
  return value ? new Date(value).toLocaleString() : "-";
}

function formatFileSize(bytes?: number): string {
  if (bytes == null) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function maskMagnet(url: string): string {
  if (!url) return "-";
  if (url.length <= 40) return url;
  return `${url.slice(0, 20)}...${url.slice(-15)}`;
}

function CopyableText({ text, display }: { text: string; display?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Space size="small">
      <Typography.Text code style={{ fontSize: 12 }}>
        {display || text}
      </Typography.Text>
      <Tooltip title={copied ? "已复制" : "复制"}>
        <Button
          type="text"
          size="small"
          icon={copied ? <CheckOutlined style={{ color: "green" }} /> : <CopyOutlined />}
          onClick={handleCopy}
          style={{ padding: "0 4px" }}
        />
      </Tooltip>
    </Space>
  );
}

export default function TaskDetail() {
  const { id } = useParams({ strict: false }) as { id?: string };
  const navigate = useNavigate();
  const [task, setTask] = useState<Task | null>(null);
  const [logs, setLogs] = useState<TaskLogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const [taskData, logData] = await Promise.all([
        fetchTask(id),
        fetchTaskLogs(id),
      ]);
      setTask(taskData);
      setLogs(logData);
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const isActive = task && (
    task.status === "running" ||
    task.status === "pending" ||
    task.status === "waiting_download" ||
    task.status === "waiting_retry"
  );
  usePolling(load, 3000, Boolean(isActive));

  if (loading) return <FullPageSpinner />;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate({ to: "/storage/tasks" })}>
          返回
        </Button>
      </Space>

      {task && (
        <>
          <Card title="基本信息" className={styles.detailCard}>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="任务ID">
                <CopyableText text={task.task_id} />
              </Descriptions.Item>
              <Descriptions.Item label="番号">
                <Typography.Text code>{task.code || "-"}</Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label="标题" span={2}>{task.title || "-"}</Descriptions.Item>
              <Descriptions.Item label="来源">{task.source || "-"}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={statusColors[task.status]}>
                  {statusLabels[task.status] || task.status}
                  {isActive && "..."}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="当前步骤">
                {stepLabels[task.current_step] || task.current_step || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="失败步骤">
                {task.failed_step ? <Tag color="red">{stepLabels[task.failed_step] || task.failed_step}</Tag> : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">{formatTime(task.created_at)}</Descriptions.Item>
              <Descriptions.Item label="开始时间">{formatTime(task.started_at)}</Descriptions.Item>
              <Descriptions.Item label="完成时间">{formatTime(task.completed_at)}</Descriptions.Item>
              <Descriptions.Item label="目标文件夹">{task.target_folder || "-"}</Descriptions.Item>
            </Descriptions>

            {task.error?.message && (
              <div className={styles.resultCard}>
                <Card title="错误信息" size="small" className={styles.errorCard}>
                  <pre className={styles.errorPre}>{task.error.message}</pre>
                  {task.error.code && (
                    <Typography.Text type="secondary">错误代码: {task.error.code}</Typography.Text>
                  )}
                </Card>
              </div>
            )}
          </Card>

          <Card title="磁力信息" className={styles.detailCard}>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="磁力链接" span={2}>
                <CopyableText text={task.magnet?.url || ""} display={maskMagnet(task.magnet?.url || "")} />
              </Descriptions.Item>
              <Descriptions.Item label="Info Hash">
                <CopyableText text={task.magnet?.info_hash || ""} />
              </Descriptions.Item>
              <Descriptions.Item label="大小">
                {task.magnet?.size || formatFileSize(task.magnet?.size_bytes)}
              </Descriptions.Item>
              {task.magnet?.selected_reason && (
                <Descriptions.Item label="选择原因" span={2}>
                  {task.magnet.selected_reason}
                </Descriptions.Item>
              )}
              <Descriptions.Item label="下载进度">
                {task.download?.progress != null && task.download.progress > 0 ? (
                  <Progress
                    percent={Math.round(task.download.progress)}
                    size="small"
                    status={task.download.status === "error" ? "exception" : "active"}
                    style={{ width: 200 }}
                  />
                ) : (
                  <Typography.Text type="secondary">-</Typography.Text>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="下载状态">{task.download?.status || "-"}</Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="步骤时间线" className={styles.detailCard}>
            <StepTimeline task={task} />
          </Card>

          {task.scanned_files && task.scanned_files.length > 0 && (
            <Card title="扫描文件" className={styles.detailCard}>
              <FilesTable files={task.scanned_files} />
            </Card>
          )}

          {task.final_files && task.final_files.length > 0 && (
            <Card title="最终文件" className={styles.detailCard}>
              <Space direction="vertical" style={{ width: "100%" }}>
                {task.final_files.map((filePath) => (
                  <CopyableText key={filePath} text={filePath} />
                ))}
              </Space>
            </Card>
          )}

          <Card title="执行日志" className={styles.detailCard}>
            <LogsPanel logs={logs} isActive={Boolean(isActive)} />
          </Card>
        </>
      )}
    </div>
  );
}
