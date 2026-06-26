import { Button, Card, Space, Table, Tag, Tooltip, Typography } from "antd";
import { RedoOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { detailTaskStatusColors, detailTaskStatusLabels } from "../constants";
import type { RunDetailTask } from "../types";

interface RunDetailTasksTableProps {
  tasks: RunDetailTask[];
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number, pageSize: number) => void;
  onRetryCrawl: (taskId: string) => void;
  onRetrySave: (taskId: string) => void;
}

function formatTime(value?: string | null): string {
  return value ? new Date(value).toLocaleString() : "-";
}

export default function RunDetailTasksTable({
  tasks,
  page,
  pageSize,
  total,
  onPageChange,
  onRetryCrawl,
  onRetrySave,
}: RunDetailTasksTableProps) {
  const columns: ColumnsType<RunDetailTask> = [
    { title: "番号", dataIndex: "code", key: "code", width: 120, render: (val: string) => val || "-" },
    { title: "名称", dataIndex: "task_name", key: "task_name", ellipsis: true },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (status: RunDetailTask["status"]) => (
        <Tag color={detailTaskStatusColors[status]}>{detailTaskStatusLabels[status]}</Tag>
      ),
    },
    { title: "创建时间", dataIndex: "created_at", key: "created_at", width: 170, render: formatTime },
    { title: "爬取时间", dataIndex: "crawled_at", key: "crawled_at", width: 170, render: formatTime },
    { title: "入库时间", dataIndex: "saved_at", key: "saved_at", width: 170, render: formatTime },
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
            <Button type="link" size="small" icon={<RedoOutlined />} onClick={() => onRetryCrawl(record._id)}>
              重试爬取
            </Button>
          )}
          {record.status === "save_failed" && (
            <Button type="link" size="small" icon={<RedoOutlined />} onClick={() => onRetrySave(record._id)}>
              重试入库
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Card title="子任务列表" style={{ marginTop: 16 }}>
      <Table<RunDetailTask>
        rowKey="_id"
        columns={columns}
        dataSource={tasks}
        size="small"
        pagination={{
          current: page,
          total,
          pageSize,
          showSizeChanger: true,
          pageSizeOptions: ["20", "50", "100"],
          showTotal: (count) => `共 ${count} 条`,
          onChange: onPageChange,
        }}
        scroll={{ x: 1100 }}
      />
    </Card>
  );
}
