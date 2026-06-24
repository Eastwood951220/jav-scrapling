import { useEffect, useState, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Tag, Button, Space, Select, message, Modal } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { TaskRun, fetchRuns, stopRun, statusColors, statusLabels } from "../api/runs";
import type { RunStatus } from "../types/common";
import { getErrorMessage } from "../hooks/useErrorMessage";
import { usePolling } from "../hooks/usePolling";
import EmptyState from "../components/EmptyState";
import styles from "../styles/pages.module.css";

export default function RunList() {
  const [runs, setRuns] = useState<TaskRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchRuns({ status: statusFilter, page, limit: 20 });
      setRuns(data.items);
      setTotal(data.total);
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => {
    load();
  }, [load]);

  // Poll every 3 seconds to update running/queued statuses
  usePolling(load, 3000, true);

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
            <Button type="link" onClick={() => navigate(`/runs/${record._id}`)}>
              详情
            </Button>
            {record.status === "running" && (
              <Button
                type="link"
                danger
                onClick={() => {
                  Modal.confirm({
                    title: "确认停止任务?",
                    content: "已抓取的数据会被保存",
                    okText: "停止",
                    cancelText: "取消",
                    okButtonProps: { danger: true },
                    onOk: async () => {
                      try {
                        await stopRun(record._id);
                        message.success("停止信号已发送");
                      } catch (e) {
                        message.error(getErrorMessage(e));
                      }
                    },
                  });
                }}
              >
                停止
              </Button>
            )}
          </Space>
        ),
      },
    ],
    [navigate],
  );

  return (
    <div>
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
