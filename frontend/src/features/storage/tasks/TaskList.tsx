import { useEffect, useState, useCallback, useMemo } from "react";
import { useNavigate } from "@tanstack/react-router";
import {
  Table,
  Tag,
  Button,
  Space,
  Select,
  Input,
  Card,
  Statistic,
  Row,
  Col,
  message,
  Popconfirm,
  Tooltip,
  DatePicker,
} from "antd";
import {
  ReloadOutlined,
  DeleteOutlined,
  RedoOutlined,
  StopOutlined,
  SearchOutlined,
  CopyOutlined,
  CheckOutlined,
  EyeOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import {
  fetchTasks,
  fetchTaskStats,
  retryTask,
  cancelTask,
  deleteTask,
  batchRetryTasks,
  batchCancelTasks,
  batchDeleteTasks,
} from "./api";
import { statusColors, statusLabels, stepLabels } from "./constants";
import type { Task, TaskStats } from "./types";
import { getErrorMessage } from "@/shared/hooks/useErrorMessage";
import { usePolling } from "@/shared/hooks/usePolling";
import EmptyState from "@/shared/components/EmptyState";
import styles from "@/shared/styles/pages.module.css";

const { RangePicker } = DatePicker;

// ── Status filter options ───────────────────────────────
const statusOptions = Object.entries(statusLabels).map(([value, label]) => ({
  value,
  label,
}));

const stepOptions = Object.entries(stepLabels).map(([value, label]) => ({
  value,
  label,
}));

// ── Copyable text component ─────────────────────────────
function CopyableText({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textArea = document.createElement("textarea");
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <Tooltip title={copied ? "已复制" : "点击复制"}>
      <Button
        type="text"
        size="small"
        icon={copied ? <CheckOutlined style={{ color: "green" }} /> : <CopyOutlined />}
        onClick={handleCopy}
        style={{ padding: "0 4px" }}
      />
    </Tooltip>
  );
}

// ── Main component ──────────────────────────────────────
export default function TaskList() {
  const navigate = useNavigate();

  // Data state
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<TaskStats>({
    pending: 0,
    waiting_download: 0,
    running: 0,
    waiting_retry: 0,
    failed: 0,
    completed: 0,
  });

  // Filter state
  const [searchText, setSearchText] = useState("");
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [stepFilter, setStepFilter] = useState<string | undefined>(undefined);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null]>([null, null]);

  // Pagination state
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [pageSize, setPageSize] = useState(20);

  // Selection state
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  // Active polling state
  const [hasActiveTasks, setHasActiveTasks] = useState(false);

  // Load tasks
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {
        page,
        limit: pageSize,
      };

      if (searchText) params.search = searchText;
      if (statusFilter) params.status = statusFilter;
      if (stepFilter) params.step = stepFilter;
      if (dateRange[0]) params.start_date = dateRange[0].toISOString();
      if (dateRange[1]) params.end_date = dateRange[1].toISOString();

      const data = await fetchTasks(params);
      setTasks(data.items);
      setTotal(data.total);

      // Check for active tasks
      const active = data.items.some(
        (t) => t.status === "pending" || t.status === "running" || t.status === "waiting_download"
      );
      setHasActiveTasks(active);
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [searchText, statusFilter, stepFilter, dateRange, page, pageSize]);

  // Load stats
  const loadStats = useCallback(async () => {
    try {
      const data = await fetchTaskStats();
      setStats(data);
    } catch {
      // Stats loading is non-critical, silently fail
    }
  }, []);

  // Initial load and filter changes
  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  // Poll every 5 seconds while there are active tasks
  usePolling(() => {
    load();
    loadStats();
  }, 5000, hasActiveTasks);

  // ── Actions ────────────────────────────────────────────
  const handleRetry = useCallback(async (taskId: string) => {
    try {
      await retryTask(taskId);
      message.success("重试任务已提交");
      load();
      loadStats();
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  }, [load, loadStats]);

  const handleCancel = useCallback(async (taskId: string) => {
    try {
      await cancelTask(taskId);
      message.success("任务已取消");
      load();
      loadStats();
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  }, [load, loadStats]);

  const handleDelete = useCallback(async (taskId: string) => {
    try {
      await deleteTask(taskId);
      message.success("任务已删除");
      load();
      loadStats();
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  }, [load, loadStats]);

  // ── Batch actions ──────────────────────────────────────
  const handleBatchRetry = useCallback(async () => {
    if (selectedRowKeys.length === 0) return;
    try {
      const result = await batchRetryTasks(selectedRowKeys as string[]);
      message.success(`批量重试完成: 成功 ${result.retried} 个, 跳过 ${result.skipped} 个`);
      setSelectedRowKeys([]);
      load();
      loadStats();
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  }, [selectedRowKeys, load, loadStats]);

  const handleBatchCancel = useCallback(async () => {
    if (selectedRowKeys.length === 0) return;
    try {
      const result = await batchCancelTasks(selectedRowKeys as string[]);
      message.success(`批量取消完成: ${result.cancelled} 个任务已取消`);
      setSelectedRowKeys([]);
      await load();
      await loadStats();
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  }, [selectedRowKeys, load, loadStats]);

  const handleBatchDelete = useCallback(async () => {
    if (selectedRowKeys.length === 0) return;
    try {
      const result = await batchDeleteTasks(selectedRowKeys as string[]);
      message.success(`批量删除完成: ${result.deleted} 个任务已删除`);
      setSelectedRowKeys([]);
      await load();
      await loadStats();
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  }, [selectedRowKeys, load, loadStats]);

  // ── Filter handlers ────────────────────────────────────
  const handleSearch = useCallback((value: string) => {
    setSearchText(value);
    setPage(1);
  }, []);

  const handleStatusChange = useCallback((value: string | undefined) => {
    setStatusFilter(value);
    setPage(1);
  }, []);

  const handleStepChange = useCallback((value: string | undefined) => {
    setStepFilter(value);
    setPage(1);
  }, []);

  const handleDateChange = useCallback((dates: [dayjs.Dayjs | null, dayjs.Dayjs | null] | null) => {
    setDateRange(dates || [null, null]);
    setPage(1);
  }, []);

  // ── Table columns ──────────────────────────────────────
  const columns: ColumnsType<Task> = useMemo(
    () => [
      {
        title: "任务ID",
        dataIndex: "task_id",
        key: "task_id",
        width: 180,
        render: (taskId: string) => (
          <Space size="small">
            <span style={{ fontFamily: "monospace", fontSize: "12px" }}>
              {taskId.length > 12 ? `${taskId.slice(0, 12)}...` : taskId}
            </span>
            <CopyableText text={taskId} />
          </Space>
        ),
      },
      {
        title: "番号",
        dataIndex: "code",
        key: "code",
        width: 120,
        render: (code: string, record) => (
          <a
            href={`/movies?id=${record.movie_id}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            {code}
          </a>
        ),
      },
      {
        title: "标题",
        dataIndex: "title",
        key: "title",
        width: 200,
        ellipsis: true,
      },
      {
        title: "来源",
        dataIndex: "source",
        key: "source",
        width: 100,
        ellipsis: true,
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
        title: "当前步骤",
        dataIndex: "current_step",
        key: "current_step",
        width: 120,
        render: (step: string) => stepLabels[step] || step,
      },
      {
        title: "下载进度",
        dataIndex: ["download", "progress"],
        key: "download_progress",
        width: 100,
        render: (progress: number) => (
          <span style={{ fontFamily: "monospace" }}>
            {progress ? `${(progress * 100).toFixed(1)}%` : "-"}
          </span>
        ),
      },
      {
        title: "重试次数",
        key: "retry_count",
        width: 100,
        render: (_: unknown, record: Task) => (
          <span>
            {record.retry?.total_attempts ?? record.retry_count ?? 0}/{record.retry?.max_step_retries ?? record.max_retries ?? 3}
          </span>
        ),
      },
      {
        title: "目标文件夹",
        dataIndex: "target_folder",
        key: "target_folder",
        width: 150,
        ellipsis: true,
      },
      {
        title: "创建时间",
        dataIndex: "created_at",
        key: "created_at",
        width: 160,
        render: (t: string) => (t ? new Date(t).toLocaleString() : "-"),
      },
      {
        title: "操作",
        key: "actions",
        width: 250,
        fixed: "right",
        render: (_: unknown, record: Task) => (
          <Space size="small">
            {/* Detail button - always show */}
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => navigate({ to: "/storage/tasks/$id", params: { id: record.task_id } })}
            >
              详情
            </Button>

            {/* Retry button - show if retryable or failed */}
            {(record.status === "failed" || record.status === "waiting_retry" || record.retryable) && (
              <Popconfirm
                title="确认重试此任务?"
                onConfirm={() => handleRetry(record.task_id)}
                okText="重试"
                cancelText="取消"
              >
                <Button type="link" size="small" icon={<RedoOutlined />}>
                  重试
                </Button>
              </Popconfirm>
            )}

            {/* Cancel button - show if pending or waiting */}
            {(record.status === "pending" || record.status === "waiting_download") && (
              <Popconfirm
                title="确认取消此任务?"
                onConfirm={() => handleCancel(record.task_id)}
                okText="取消任务"
                cancelText="返回"
                okButtonProps={{ danger: true }}
              >
                <Button type="link" size="small" danger icon={<StopOutlined />}>
                  取消
                </Button>
              </Popconfirm>
            )}

            {/* Delete button - show if completed, failed, or cancelled */}
            {(record.status === "completed" || record.status === "failed" || record.status === "cancelled") && (
              <Popconfirm
                title="确认删除此任务?"
                description="删除后无法恢复"
                onConfirm={() => handleDelete(record.task_id)}
                okText="删除"
                cancelText="取消"
                okButtonProps={{ danger: true }}
              >
                <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                  删除
                </Button>
              </Popconfirm>
            )}
          </Space>
        ),
      },
    ],
    [handleRetry, handleCancel, handleDelete],
  );

  // ── Row selection ──────────────────────────────────────
  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelectedRowKeys(keys),
  };

  // ── Stats cards data ───────────────────────────────────
  const statsCards = [
    { title: "待处理", value: stats.pending, color: "#d9d9d9" },
    { title: "等待下载", value: stats.waiting_download, color: "#1890ff" },
    { title: "运行中", value: stats.running, color: "#1890ff" },
    { title: "等待重试", value: stats.waiting_retry, color: "#faad14" },
    { title: "失败", value: stats.failed, color: "#ff4d4f" },
    { title: "已完成", value: stats.completed, color: "#52c41a" },
  ];

  return (
    <div>
      {/* Statistics cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {statsCards.map((stat) => (
          <Col xs={12} sm={8} md={4} key={stat.title}>
            <Card size="small" hoverable>
              <Statistic
                title={stat.title}
                value={stat.value}
                valueStyle={{ color: stat.color }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      {/* Filter bar */}
      <div className={styles.toolbar}>
        <Space wrap>
          <Input
            placeholder="搜索任务ID、番号、标题"
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => handleSearch(e.target.value)}
            style={{ width: 250 }}
            allowClear
          />
          <Select
            style={{ width: 150 }}
            placeholder="筛选状态"
            allowClear
            value={statusFilter}
            onChange={handleStatusChange}
            options={statusOptions}
          />
          <Select
            style={{ width: 150 }}
            placeholder="筛选步骤"
            allowClear
            value={stepFilter}
            onChange={handleStepChange}
            options={stepOptions}
          />
          <RangePicker
            showTime
            format="YYYY-MM-DD HH:mm"
            placeholder={["开始时间", "结束时间"]}
            value={dateRange as [dayjs.Dayjs, dayjs.Dayjs]}
            onChange={(dates) => handleDateChange(dates as [dayjs.Dayjs | null, dayjs.Dayjs | null] | null)}
          />
          <Button icon={<ReloadOutlined />} onClick={() => { load(); loadStats(); }}>
            刷新
          </Button>
        </Space>
      </div>

      {/* Batch actions */}
      {selectedRowKeys.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Space>
            <span>已选择 {selectedRowKeys.length} 项</span>
            <Popconfirm
              title={`确认批量重试 ${selectedRowKeys.length} 个任务?`}
              onConfirm={handleBatchRetry}
              okText="重试"
              cancelText="取消"
            >
              <Button icon={<RedoOutlined />}>批量重试</Button>
            </Popconfirm>
            <Popconfirm
              title={`确认批量取消 ${selectedRowKeys.length} 个任务?`}
              onConfirm={handleBatchCancel}
              okText="取消任务"
              cancelText="返回"
              okButtonProps={{ danger: true }}
            >
              <Button icon={<StopOutlined />}>批量取消</Button>
            </Popconfirm>
            <Popconfirm
              title={`确认批量删除 ${selectedRowKeys.length} 个任务?`}
              description="删除后无法恢复"
              onConfirm={handleBatchDelete}
              okText="删除"
              cancelText="取消"
              okButtonProps={{ danger: true }}
            >
              <Button danger icon={<DeleteOutlined />}>批量删除</Button>
            </Popconfirm>
          </Space>
        </div>
      )}

      {/* Main table */}
      <Table
        columns={columns}
        dataSource={tasks}
        rowKey="task_id"
        loading={loading}
        rowSelection={rowSelection}
        scroll={{ x: 1500 }}
        pagination={{
          current: page,
          total,
          pageSize,
          onChange: (newPage, newPageSize) => {
            setPage(newPage);
            if (newPageSize !== pageSize) {
              setPageSize(newPageSize);
              setPage(1);
            }
          },
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          pageSizeOptions: ["10", "20", "50", "100"],
        }}
        locale={{ emptyText: <EmptyState /> }}
      />
    </div>
  );
}
