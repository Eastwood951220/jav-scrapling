import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Tag, Button, Space, Select, message } from "antd";
import { ReloadOutlined, EyeOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { TaskRun, fetchRuns, statusColors, statusLabels } from "../api/runs";

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
      message.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => {
    load();
    // Poll every 3 seconds to update running/queued statuses
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [load]);

  const columns: ColumnsType<TaskRun> = [
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
      render: (status: string) => (
        <Tag color={statusColors[status] || "default"}>
          {statusLabels[status] || status}
        </Tag>
      ),
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
      width: 80,
      render: (_: unknown, record: TaskRun) => (
        <Button
          icon={<EyeOutlined />}
          size="small"
          onClick={() => navigate(`/runs/${record._id}`)}
        >
          详情
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
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
      />
    </div>
  );
}
