import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "@tanstack/react-router";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { Button, Card, Descriptions, message, Modal, Space } from "antd";
import { fetchRun, fetchRunDetailTasks, retryCrawl, retrySave, stopRun } from "./api";
import RunDetailTasksTable from "./components/RunDetailTasksTable";
import RunLogsTimeline from "./components/RunLogsTimeline";
import RunSummaryCard from "./components/RunSummaryCard";
import type { RunDetailTask, TaskRun } from "./types";
import FullPageSpinner from "@/shared/components/FullPageSpinner";
import { getErrorMessage } from "@/shared/hooks/useErrorMessage";
import { usePolling } from "@/shared/hooks/usePolling";
import styles from "@/shared/styles/pages.module.css";

export default function RunDetail() {
  const { id } = useParams({ strict: false }) as { id?: string };
  const navigate = useNavigate();
  const [run, setRun] = useState<TaskRun | null>(null);
  const [tasks, setTasks] = useState<RunDetailTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [taskPage, setTaskPage] = useState(1);
  const [taskPageSize, setTaskPageSize] = useState(20);
  const [taskTotal, setTaskTotal] = useState(0);
  const [modal, contextHolder] = Modal.useModal();

  const loadTasks = useCallback(async () => {
    if (!id) return;
    try {
      const taskData = await fetchRunDetailTasks(id, { page: taskPage, limit: taskPageSize });
      setTasks(taskData.items);
      setTaskTotal(taskData.total);
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  }, [id, taskPage, taskPageSize]);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const runData = await fetchRun(id);
      setRun(runData);
      await loadTasks();
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [id, loadTasks]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  const isActive = run && (run.status === "running" || run.status === "queued");
  usePolling(load, 3000, Boolean(isActive));

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
          <RunSummaryCard run={run} isActive={Boolean(isActive)} onStop={handleStopRun} />

          {run.error && (
            <div className={styles.resultCard}>
              <Card title="错误信息" size="small" className={styles.errorCard}>
                <pre className={styles.errorPre}>{run.error}</pre>
              </Card>
            </div>
          )}

          {run.result && (
            <div className={styles.resultCard}>
              <Card title="执行结果" size="small">
                <Descriptions column={2} size="small">
                  <Descriptions.Item label="列表页数">{String(run.result.total_tasks ?? "-")}</Descriptions.Item>
                  <Descriptions.Item label="已完成">{String(run.result.completed_tasks ?? "-")}</Descriptions.Item>
                  <Descriptions.Item label="失败">{String(run.result.failed_tasks ?? "-")}</Descriptions.Item>
                  <Descriptions.Item label="已保存">{String(run.result.saved ?? "-")}</Descriptions.Item>
                  <Descriptions.Item label="任务名">{String(run.result.task_name ?? "-")}</Descriptions.Item>
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

          <RunDetailTasksTable
            tasks={tasks}
            page={taskPage}
            pageSize={taskPageSize}
            total={taskTotal}
            onPageChange={(nextPage, nextSize) => {
              if (nextSize !== taskPageSize) {
                setTaskPageSize(nextSize);
                setTaskPage(1);
              } else {
                setTaskPage(nextPage);
              }
            }}
            onRetryCrawl={handleRetryCrawl}
            onRetrySave={handleRetrySave}
          />

          <Card title="运行日志" style={{ marginTop: 16 }}>
            <RunLogsTimeline logs={run.logs} isActive={Boolean(isActive)} />
          </Card>
        </>
      )}
    </div>
  );
}
