import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useNavigate } from "@tanstack/react-router";
import {
  Card, Descriptions, Tag, Timeline, Typography, Space, Button, message, Modal, Table, Tooltip,
} from "antd";
import { ArrowLeftOutlined, RedoOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  TaskRun,
  RunDetailTask,
  fetchRun,
  fetchRunDetailTasks,
  stopRun,
  retryCrawl,
  retrySave,
  statusColors,
  statusLabels,
  detailTaskStatusColors,
  detailTaskStatusLabels,
} from "./api";
import { getErrorMessage } from "@/shared/hooks/useErrorMessage";
import { usePolling } from "@/shared/hooks/usePolling";
import FullPageSpinner from "@/shared/components/FullPageSpinner";
import styles from "@/shared/styles/pages.module.css";

const logLevelColors: Record<string, string> = {
  INFO: "blue",
  WARNING: "orange",
  ERROR: "red",
};

function formatTime(value?: string | null): string {
  return value ? new Date(value).toLocaleString() : "-";
}

export default function RunDetail() {
  const { id } = useParams({ strict: false }) as { id?: string };
  const navigate = useNavigate();
  const [run, setRun] = useState<TaskRun | null>(null);
  const [tasks, setTasks] = useState<RunDetailTask[]>([]);
  const [loading, setLoading] = useState(true);
  const logEndRef = useRef<HTMLDivElement>(null);
  const [modal, contextHolder] = Modal.useModal();

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const [runData, taskData] = await Promise.all([
        fetchRun(id),
        fetchRunDetailTasks(id),
      ]);
      setRun(runData);
      setTasks(taskData.items);
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [id]);

  // Initial load
  useEffect(() => {
    load();
  }, [load]);

  // Poll while active
  const isActive = run && (run.status === "running" || run.status === "queued");
  usePolling(load, 3000, Boolean(isActive));

  // Auto-scroll to latest log during active runs
  useEffect(() => {
    if (run?.logs?.length && isActive) {
      logEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [run?.logs?.length, isActive]);

  const handleRetryCrawl = useCallback(async (taskId: string) => {
    if (!id) return;
    try {
      await retryCrawl(id, taskId);
      message.success("重新爬取已提交");
      load();
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  }, [id, load]);

  const handleRetrySave = useCallback(async (taskId: string) => {
    if (!id) return;
    try {
      await retrySave(id, taskId);
      message.success("重新入库已提交");
      load();
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  }, [id, load]);

  const handleStopRun = useCallback((targetRun: TaskRun) => {
    modal.confirm({
      title: "确认停止任务?",
      content: "已抓取的数据会被保存",
      okText: "停止",
      cancelText: "取消",
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await stopRun(targetRun._id);
          message.success("停止信号已发送");
          load();
        } catch (e) {
          message.error(getErrorMessage(e));
        }
      },
    });
  }, [load, modal]);

  const taskColumns: ColumnsType<RunDetailTask> = [
    {
      title: "番号",
      dataIndex: "code",
      key: "code",
      width: 120,
      render: (val: string) => val || "-",
    },
    {
      title: "名称",
      dataIndex: "task_name",
      key: "task_name",
      ellipsis: true,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (status: RunDetailTask["status"]) => (
        <Tag color={detailTaskStatusColors[status]}>
          {detailTaskStatusLabels[status]}
        </Tag>
      ),
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 170,
      render: formatTime,
    },
    {
      title: "爬取时间",
      dataIndex: "crawled_at",
      key: "crawled_at",
      width: 170,
      render: formatTime,
    },
    {
      title: "入库时间",
      dataIndex: "saved_at",
      key: "saved_at",
      width: 170,
      render: formatTime,
    },
    {
      title: "错误",
      dataIndex: "error",
      key: "error",
      ellipsis: true,
      render: (val: string | null) =>
        val ? (
          <Tooltip title={val}>
            <Typography.Text type="danger" ellipsis style={{ maxWidth: 200 }}>
              {val}
            </Typography.Text>
          </Tooltip>
        ) : "-",
    },
    {
      title: "操作",
      key: "action",
      width: 120,
      render: (_: unknown, record: RunDetailTask) => (
        <Space size="small">
          {record.status === "crawl_failed" && (
            <Button
              type="link"
              size="small"
              icon={<RedoOutlined />}
              onClick={() => handleRetryCrawl(record._id)}
            >
              重试爬取
            </Button>
          )}
          {record.status === "save_failed" && (
            <Button
              type="link"
              size="small"
              icon={<RedoOutlined />}
              onClick={() => handleRetrySave(record._id)}
            >
              重试入库
            </Button>
          )}
        </Space>
      ),
    },
  ];

  if (loading) return <FullPageSpinner />;

  return (
    <div>
      {contextHolder}
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate({ to: "/runs" })}>
          返回
        </Button>
      </Space>

      {run && (
        <>
          <Card className={styles.detailCard}>
            <Descriptions title="运行详情" bordered column={2} size="small">
              <Descriptions.Item label="任务名称">
                {run.task_name || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Space>
                  <Tag color={statusColors[run.status]}>
                    {statusLabels[run.status]}
                    {isActive && "..."}
                  </Tag>
                  {run.status === "running" && (
                    <Button
                      danger
                      size="small"
                      onClick={() => handleStopRun(run)}
                    >
                      停止任务
                    </Button>
                  )}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="排队时间">
                {formatTime(run.queued_at)}
              </Descriptions.Item>
              <Descriptions.Item label="开始时间">
                {formatTime(run.started_at)}
              </Descriptions.Item>
              <Descriptions.Item label="完成时间">
                {formatTime(run.finished_at)}
              </Descriptions.Item>
              <Descriptions.Item label="任务ID">
                <Typography.Text code>{run.task_id}</Typography.Text>
              </Descriptions.Item>
            </Descriptions>

            {run.error && (
              <div className={styles.resultCard}>
                <Card title="错误信息" size="small" className={styles.errorCard}>
                  <pre className={styles.errorPre}>
                    {run.error}
                  </pre>
                </Card>
              </div>
            )}

            {run.result && (
              <div className={styles.resultCard}>
                <Card title="执行结果" size="small">
                  <Descriptions column={2} size="small">
                    <Descriptions.Item label="列表页数">
                      {String(run.result.total_tasks ?? "-")}
                    </Descriptions.Item>
                    <Descriptions.Item label="已完成">
                      {String(run.result.completed_tasks ?? "-")}
                    </Descriptions.Item>
                    <Descriptions.Item label="失败">
                      {String(run.result.failed_tasks ?? "-")}
                    </Descriptions.Item>
                    <Descriptions.Item label="已保存">
                      {String(run.result.saved ?? "-")}
                    </Descriptions.Item>
                    <Descriptions.Item label="任务名">
                      {String(run.result.task_name ?? "-")}
                    </Descriptions.Item>
                    {/* Fallback: render any fields not explicitly listed above */}
                    {Object.entries(run.result)
                      .filter(([key]) =>
                        !["total_tasks", "completed_tasks", "failed_tasks", "saved", "task_name"].includes(key)
                      )
                      .map(([key, value]) => (
                        <Descriptions.Item key={key} label={key}>
                          {String(value ?? "-")}
                        </Descriptions.Item>
                      ))}
                  </Descriptions>
                </Card>
              </div>
            )}
          </Card>

          <Card title="子任务列表" style={{ marginTop: 16 }}>
            <Table<RunDetailTask>
              rowKey="_id"
              columns={taskColumns}
              dataSource={tasks}
              size="small"
              pagination={false}
              scroll={{ x: 1100 }}
            />
          </Card>

          <Card title="运行日志" style={{ marginTop: 16 }}>
            {run.logs.length === 0 ? (
              <Typography.Text type="secondary">
                {isActive ? "等待日志..." : "无日志"}
              </Typography.Text>
            ) : (
              <>
                <Timeline
                  items={run.logs.map((entry, idx) => ({
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
                <div ref={logEndRef} />
              </>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
