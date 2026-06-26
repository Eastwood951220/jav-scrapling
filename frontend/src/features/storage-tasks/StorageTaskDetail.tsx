import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useNavigate } from "@tanstack/react-router";
import {
  Card,
  Descriptions,
  Tag,
  Timeline,
  Typography,
  Space,
  Button,
  message,
  Table,
  Tooltip,
  Input,
  Select,
  Switch,
  Progress,
} from "antd";
import {
  ArrowLeftOutlined,
  CopyOutlined,
  CheckOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  fetchStorageTask,
  fetchStorageTaskLogs,
  statusColors,
  statusLabels,
  stepLabels,
  type StorageTask,
  type StorageTaskLogEntry,
  type StorageTaskFile,
} from "./api";
import { getErrorMessage } from "@/shared/hooks/useErrorMessage";
import { usePolling } from "@/shared/hooks/usePolling";
import FullPageSpinner from "@/shared/components/FullPageSpinner";
import styles from "@/shared/styles/pages.module.css";

// ── Constants ─────────────────────────────────────────────
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

const LOG_LEVEL_COLORS: Record<string, string> = {
  INFO: "blue",
  WARNING: "orange",
  ERROR: "red",
};

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

const LOG_LEVEL_OPTIONS = [
  { value: "INFO", label: "INFO" },
  { value: "WARNING", label: "WARNING" },
  { value: "ERROR", label: "ERROR" },
];

// ── Helpers ───────────────────────────────────────────────
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

// ── Copyable text ─────────────────────────────────────────
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

// ── Main Component ────────────────────────────────────────
export default function StorageTaskDetail() {
  const { id } = useParams({ strict: false }) as { id?: string };
  const navigate = useNavigate();

  const [task, setTask] = useState<StorageTask | null>(null);
  const [logs, setLogs] = useState<StorageTaskLogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  // Log filters
  const [logLevelFilter, setLogLevelFilter] = useState<string | undefined>(undefined);
  const [logStepFilter, setLogStepFilter] = useState<string | undefined>(undefined);
  const [logSearch, setLogSearch] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const logEndRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const [taskData, logData] = await Promise.all([
        fetchStorageTask(id),
        fetchStorageTaskLogs(id),
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

  // Poll while task is active
  const isActive = task && (task.status === "running" || task.status === "pending" || task.status === "waiting_download" || task.status === "waiting_retry");
  usePolling(load, 3000, Boolean(isActive));

  // Auto-scroll logs
  useEffect(() => {
    if (autoScroll && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, autoScroll]);

  // ── Build timeline from steps or derive from step labels ──
  const buildTimeline = () => {
    const steps = task?.steps;

    // If backend provides step history, use it
    if (steps && steps.length > 0) {
      return (
        <Timeline
          items={steps.map((step) => ({
            color: STEP_STATUS_COLORS[step.status] || "gray",
            children: (
              <div>
                <Space>
                  <Typography.Text strong>
                    {stepLabels[step.name] || step.name}
                  </Typography.Text>
                  <Tag color={STEP_STATUS_COLORS[step.status]}>
                    {STEP_STATUS_LABELS[step.status]}
                  </Tag>
                  {step.attempt != null && step.attempt > 1 && (
                    <Typography.Text type="secondary">
                      尝试 #{step.attempt}
                    </Typography.Text>
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

    // Fallback: derive from current_step / failed_step
    if (!task) return null;
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
                <Typography.Text>
                  {stepLabels[stepName] || stepName}
                </Typography.Text>
                <Tag color={STEP_STATUS_COLORS[status]}>
                  {STEP_STATUS_LABELS[status]}
                </Tag>
              </Space>
            ),
          };
        })}
      />
    );
  };

  // ── Scanned files table ──
  const fileColumns: ColumnsType<StorageTaskFile> = [
    { title: "文件名", dataIndex: "filename", key: "filename", ellipsis: true },
    { title: "路径", dataIndex: "path", key: "path", ellipsis: true },
    {
      title: "大小",
      dataIndex: "size",
      key: "size",
      width: 100,
      render: (v?: number) => formatFileSize(v),
    },
    { title: "扩展名", dataIndex: "extension", key: "extension", width: 80 },
    { title: "分类", dataIndex: "category", key: "category", width: 100 },
    { title: "结果", dataIndex: "result", key: "result", width: 100 },
  ];

  // ── Filtered logs ──
  const filteredLogs = logs.filter((entry) => {
    if (logLevelFilter) {
      const levels = ["INFO", "WARNING", "ERROR"];
      const minIdx = levels.indexOf(logLevelFilter);
      const entryIdx = levels.indexOf(entry.level);
      if (entryIdx < minIdx) return false;
    }
    if (logStepFilter && entry.step !== logStepFilter) return false;
    if (logSearch && !entry.message.toLowerCase().includes(logSearch.toLowerCase())) return false;
    return true;
  });

  // ── Unique steps from logs for filter dropdown ──
  const logSteps = Array.from(new Set(logs.map((l) => l.step).filter(Boolean))) as string[];
  const logStepOptions = logSteps.map((s) => ({
    value: s,
    label: stepLabels[s] || s,
  }));

  if (loading) return <FullPageSpinner />;

  return (
    <div>
      {/* Back button */}
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate({ to: "/storage/tasks" })}>
          返回
        </Button>
      </Space>

      {task && (
        <>
          {/* ── Section 1: Basic Info ── */}
          <Card title="基本信息" className={styles.detailCard}>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="任务ID">
                <CopyableText text={task.task_id} />
              </Descriptions.Item>
              <Descriptions.Item label="番号">
                <Typography.Text code>{task.code || "-"}</Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label="标题" span={2}>
                {task.title || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="来源">
                {task.source || "-"}
              </Descriptions.Item>
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
                {task.failed_step ? (
                  <Tag color="red">{stepLabels[task.failed_step] || task.failed_step}</Tag>
                ) : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {formatTime(task.created_at)}
              </Descriptions.Item>
              <Descriptions.Item label="开始时间">
                {formatTime(task.started_at)}
              </Descriptions.Item>
              <Descriptions.Item label="完成时间">
                {formatTime(task.completed_at)}
              </Descriptions.Item>
              <Descriptions.Item label="目标文件夹">
                {task.target_folder || "-"}
              </Descriptions.Item>
            </Descriptions>

            {/* Error message */}
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

          {/* ── Section 2: Magnet Info ── */}
          <Card title="磁力信息" className={styles.detailCard}>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="磁力链接" span={2}>
                <CopyableText
                  text={task.magnet?.url || ""}
                  display={maskMagnet(task.magnet?.url || "")}
                />
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
                    percent={Math.round(task.download.progress * 100)}
                    size="small"
                    status={task.download.status === "error" ? "exception" : "active"}
                    style={{ width: 200 }}
                  />
                ) : (
                  <Typography.Text type="secondary">-</Typography.Text>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="下载状态">
                {task.download?.status || "-"}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {/* ── Section 3: Steps Timeline ── */}
          <Card title="步骤时间线" className={styles.detailCard}>
            {buildTimeline()}
          </Card>

          {/* ── Section 4: Files ── */}
          {task.scanned_files && task.scanned_files.length > 0 && (
            <Card title="扫描文件" className={styles.detailCard}>
              <Table<StorageTaskFile>
                rowKey="path"
                columns={fileColumns}
                dataSource={task.scanned_files}
                size="small"
                pagination={{ pageSize: 20, showSizeChanger: true }}
                scroll={{ x: 800 }}
              />
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

          {/* ── Section 5: Logs ── */}
          <Card title="执行日志" className={styles.detailCard}>
            {/* Log filters */}
            <Space wrap style={{ marginBottom: 16 }}>
              <Select
                style={{ width: 140 }}
                placeholder="日志级别"
                allowClear
                value={logLevelFilter}
                onChange={setLogLevelFilter}
                options={LOG_LEVEL_OPTIONS}
              />
              <Select
                style={{ width: 160 }}
                placeholder="筛选步骤"
                allowClear
                value={logStepFilter}
                onChange={setLogStepFilter}
                options={logStepOptions}
              />
              <Input
                placeholder="搜索日志"
                prefix={<SearchOutlined />}
                value={logSearch}
                onChange={(e) => setLogSearch(e.target.value)}
                style={{ width: 220 }}
                allowClear
              />
              <Space>
                <Typography.Text type="secondary">自动滚动</Typography.Text>
                <Switch size="small" checked={autoScroll} onChange={setAutoScroll} />
              </Space>
              <Typography.Text type="secondary">
                共 {filteredLogs.length} 条
              </Typography.Text>
            </Space>

            {/* Log entries */}
            {filteredLogs.length === 0 ? (
              <Typography.Text type="secondary">
                {isActive ? "等待日志..." : "无日志"}
              </Typography.Text>
            ) : (
              <div style={{ maxHeight: 500, overflow: "auto" }}>
                <Timeline
                  items={filteredLogs.map((entry, idx) => ({
                    key: idx,
                    color: LOG_LEVEL_COLORS[entry.level] || "gray",
                    children: (
                      <div>
                        <Space size="small">
                          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                            {new Date(entry.timestamp).toLocaleString()}
                          </Typography.Text>
                          <Tag
                            color={LOG_LEVEL_COLORS[entry.level] || "default"}
                            style={{ fontSize: 11 }}
                          >
                            {entry.level}
                          </Tag>
                          {entry.step && (
                            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                              [{stepLabels[entry.step] || entry.step}]
                            </Typography.Text>
                          )}
                        </Space>
                        <Typography.Text
                          type={entry.level === "ERROR" ? "danger" : undefined}
                          style={{ display: "block", marginTop: 2 }}
                        >
                          {entry.message}
                        </Typography.Text>
                        {entry.data && Object.keys(entry.data).length > 0 && (
                          <pre
                            style={{
                              fontSize: 11,
                              background: "#f5f5f5",
                              padding: "4px 8px",
                              borderRadius: 4,
                              marginTop: 4,
                              maxHeight: 120,
                              overflow: "auto",
                            }}
                          >
                            {JSON.stringify(entry.data, null, 2)}
                          </pre>
                        )}
                      </div>
                    ),
                  }))}
                />
                <div ref={logEndRef} />
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
