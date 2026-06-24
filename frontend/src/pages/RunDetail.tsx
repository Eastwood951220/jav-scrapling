import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card, Descriptions, Tag, Timeline, Typography, Space, Button, message, Modal,
} from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { TaskRun, fetchRun, stopRun, statusColors, statusLabels } from "../api/runs";
import { getErrorMessage } from "../hooks/useErrorMessage";
import { usePolling } from "../hooks/usePolling";
import FullPageSpinner from "../components/FullPageSpinner";
import styles from "../styles/pages.module.css";

const logLevelColors: Record<string, string> = {
  INFO: "blue",
  WARNING: "orange",
  ERROR: "red",
};

export default function RunDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [run, setRun] = useState<TaskRun | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const data = await fetchRun(id);
      setRun(data);
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

  if (loading) return <FullPageSpinner />;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/runs")}>
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
                      onClick={() => {
                        Modal.confirm({
                          title: "确认停止任务?",
                          content: "已抓取的数据会被保存",
                          okText: "停止",
                          cancelText: "取消",
                          okButtonProps: { danger: true },
                          onOk: async () => {
                            try {
                              await stopRun(run._id);
                              message.success("停止信号已发送");
                            } catch (e) {
                              message.error((e as Error).message);
                            }
                          },
                        });
                      }}
                    >
                      停止任务
                    </Button>
                  )}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="排队时间">
                {run.queued_at ? new Date(run.queued_at).toLocaleString() : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="开始时间">
                {run.started_at ? new Date(run.started_at).toLocaleString() : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="完成时间">
                {run.finished_at ? new Date(run.finished_at).toLocaleString() : "-"}
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

          <Card title="运行日志">
            {run.logs.length === 0 ? (
              <Typography.Text type="secondary">
                {isActive ? "等待日志..." : "无日志"}
              </Typography.Text>
            ) : (
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
            )}
          </Card>
        </>
      )}
    </div>
  );
}
