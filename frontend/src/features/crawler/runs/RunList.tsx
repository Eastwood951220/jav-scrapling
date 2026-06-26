import { useEffect, useState, useCallback, useMemo } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Table, Tag, Button, Space, Select, message, Modal, Popconfirm } from "antd";
import { ReloadOutlined, DeleteOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { fetchRuns, stopRun, deleteRun } from "./api";
import { statusColors, statusLabels } from "./constants";
import type { TaskRun } from "./types";
import type { RunStatus } from "@/shared/types/common";
import { getErrorMessage } from "@/shared/hooks/useErrorMessage";
import { usePolling } from "@/shared/hooks/usePolling";
import EmptyState from "@/shared/components/EmptyState";
import styles from "@/shared/styles/pages.module.css";

export default function RunList() {
  const [runs, setRuns] = useState<TaskRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [hasActiveRuns, setHasActiveRuns] = useState(false);
  const navigate = useNavigate();
  const [modal, contextHolder] = Modal.useModal();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchRuns({ status: statusFilter, page, limit: 20 });
      setRuns(data.items);
      setTotal(data.total);
      const active = data.items.some(
        (r) => r.status === "queued" || r.status === "running",
      );
      setHasActiveRuns(active);
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => {
    load();
  }, [load]);

  // Poll every 3 seconds only while there are active (queued/running) runs
  usePolling(load, 3000, hasActiveRuns);

  const handleStopRun = useCallback((run: TaskRun) => {
    modal.confirm({
      title: "确认停止任务?",
      content: "已抓取的数据会被保存",
      okText: "停止",
      cancelText: "取消",
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await stopRun(run._id);
          message.success("停止信号已发送");
          load();
        } catch (e) {
          message.error(getErrorMessage(e));
        }
      },
    });
  }, [load, modal]);

  const columns: ColumnsType<TaskRun> = useMemo(
    () => [
      {
        title: "任务名称",
        dataIndex: "task_name",
        key: "task_name",
        width: 160,
        render: (name: string | null) => name || "-",
      },
      {
        title: "状态",
        dataIndex: "status",
        key: "status",
        width: 100,
        render: (status: string) => {
          const s = status as RunStatus;
          return (
            <Tag color={statusColors[s] || "default"}>
              {statusLabels[s] || status}
            </Tag>
          );
        },
      },
      {
        title: "排队时间",
        dataIndex: "queued_at",
        key: "queued_at",
        width: 180,
        render: (t: string | null) => (t ? new Date(t).toLocaleString() : "-"),
      },
      {
        title: "开始时间",
        dataIndex: "started_at",
        key: "started_at",
        width: 180,
        render: (t: string | null) => (t ? new Date(t).toLocaleString() : "-"),
      },
      {
        title: "完成时间",
        dataIndex: "finished_at",
        key: "finished_at",
        width: 180,
        render: (t: string | null) => (t ? new Date(t).toLocaleString() : "-"),
      },
      {
        title: "操作",
        key: "actions",
        width: 160,
        render: (_: unknown, record: TaskRun) => (
          <Space>
            <Button type="link" onClick={() => navigate({ to: "/runs/$id", params: { id: record._id } })}>
              详情
            </Button>
            {record.status === "running" && (
              <Button
                type="link"
                danger
                onClick={() => handleStopRun(record)}
              >
                停止
              </Button>
            )}
            {record.status !== "running" && record.status !== "queued" && (
              <Popconfirm
                title="确认删除此运行记录？"
                description="将同时删除日志和结果文件"
                onConfirm={async () => {
                  try {
                    await deleteRun(record._id);
                    message.success("已删除");
                    load();
                  } catch (e) {
                    message.error(getErrorMessage(e));
                  }
                }}
                okText="删除"
                cancelText="取消"
                okButtonProps={{ danger: true }}
              >
                <Button type="link" danger icon={<DeleteOutlined />} size="small">
                  删除
                </Button>
              </Popconfirm>
            )}
          </Space>
        ),
      },
    ],
    [handleStopRun, load, navigate],
  );

  return (
    <div>
      {contextHolder}
      <div className={styles.toolbarLeft}>
        <Space>
          <Select
            style={{ width: 150 }}
            placeholder="筛选状态"
            allowClear
            value={statusFilter}
            onChange={(v) => {
              setStatusFilter(v);
              setPage(1);
            }}
            options={[
              { value: "queued", label: "排队中" },
              { value: "running", label: "运行中" },
              { value: "completed", label: "已完成" },
              { value: "failed", label: "失败" },
              { value: "stopped", label: "已停止" },
            ]}
          />
          <Button icon={<ReloadOutlined />} onClick={load}>
            刷新
          </Button>
        </Space>
      </div>
      <Table
        columns={columns}
        dataSource={runs}
        rowKey="_id"
        loading={loading}
        pagination={{
          current: page,
          total,
          pageSize: 20,
          onChange: setPage,
          showTotal: (t) => `共 ${t} 条`,
        }}
        locale={{ emptyText: <EmptyState /> }}
      />
    </div>
  );
}
