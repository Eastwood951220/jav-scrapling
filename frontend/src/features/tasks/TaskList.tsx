import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Table, Button, Space, Popconfirm, message, Switch, Tag, Typography } from "antd";
import { PlusOutlined, PlayCircleOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { CrawlTask, fetchTasks, deleteTask, runTask, updateTask } from "./api";
import { fetchQueueStatus, QueueStatus } from "@/features/runs/api";
import { getErrorMessage } from "@/shared/hooks/useErrorMessage";

export default function TaskList() {
  const [tasks, setTasks] = useState<CrawlTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  const navigate = useNavigate();

  const loadTasks = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchTasks();
      setTasks(data);
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadQueueStatus = useCallback(async () => {
    try {
      const status = await fetchQueueStatus();
      setQueueStatus(status);
    } catch {
      // Silently ignore queue status failures
    }
  }, []);

  useEffect(() => {
    loadTasks();
    loadQueueStatus();
    const interval = setInterval(loadQueueStatus, 3000);
    return () => clearInterval(interval);
  }, [loadTasks, loadQueueStatus]);

  const handleDelete = async (id: string) => {
    try {
      await deleteTask(id);
      message.success("任务已删除");
      loadTasks();
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  };

  const handleRun = async (id: string) => {
    try {
      message.loading({ content: "正在加入队列...", key: "run" });
      const runDoc = await runTask(id);
      message.success({ content: `已加入队列 (${runDoc.status})`, key: "run", duration: 2 });
      navigate({ to: "/runs" });
    } catch (e: unknown) {
      message.error({ content: getErrorMessage(e), key: "run" });
    }
  };

  const handleToggleSkip = async (task: CrawlTask) => {
    try {
      await updateTask(task._id, { is_skip: !task.is_skip });
      message.success(task.is_skip ? "任务已启用" : "任务已禁用");
      loadTasks();
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  };

  const columns: ColumnsType<CrawlTask> = [
    { title: "名称", dataIndex: "name", key: "name", width: 150 },
    { title: "URL类型", dataIndex: "url_type", key: "url_type", width: 100 },
    {
      title: "URL",
      dataIndex: "url",
      key: "url",
      ellipsis: true,
      render: (url: string) => (
        <a href={url} target="_blank" rel="noopener noreferrer">
          {url}
        </a>
      ),
    },
    {
      title: "状态",
      dataIndex: "is_skip",
      key: "is_skip",
      width: 80,
      render: (_: boolean, record: CrawlTask) => (
        <Switch
          checked={!record.is_skip}
          onChange={() => handleToggleSkip(record)}
          checkedChildren="启用"
          unCheckedChildren="禁用"
        />
      ),
    },
    {
      title: "最大页数",
      dataIndex: "max_list_pages",
      key: "max_list_pages",
      width: 100,
    },
    {
      title: "操作",
      key: "actions",
      width: 260,
      render: (_: unknown, record: CrawlTask) => (
        <Space>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            size="small"
            onClick={() => handleRun(record._id)}
          >
            执行
          </Button>
          <Button
            icon={<EditOutlined />}
            size="small"
            onClick={() => navigate({ to: "/tasks/$id/edit", params: { id: record._id } })}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除此任务？"
            onConfirm={() => handleDelete(record._id)}
          >
            <Button danger icon={<DeleteOutlined />} size="small">
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate({ to: "/tasks/new" })}>
          新建任务
        </Button>
        {queueStatus && (
          <Space>
            <Typography.Text type="secondary">队列状态:</Typography.Text>
            {queueStatus.is_running ? (
              <Tag color="processing">运行中</Tag>
            ) : (
              <Tag>空闲</Tag>
            )}
            <Typography.Text>
              队列: {queueStatus.queue_size} 个任务等待中
            </Typography.Text>
          </Space>
        )}
      </div>
      <Table
        columns={columns}
        dataSource={tasks}
        rowKey="_id"
        loading={loading}
        pagination={{ pageSize: 20 }}
      />
    </div>
  );
}
