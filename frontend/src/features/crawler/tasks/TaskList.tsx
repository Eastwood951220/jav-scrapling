import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Table, Button, Space, Dropdown, Modal, message, Switch, Tag, Typography } from "antd";
import { PlusOutlined, PlayCircleOutlined, EditOutlined, DeleteOutlined, DownOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { CrawlTask, fetchTasks, deleteTask, runTask, updateTask } from "./api";
import { fetchQueueStatus } from "@/features/crawler/runs/api";
import type { QueueStatus } from "@/features/crawler/runs/types";
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

  const handleDelete = async (id: string, mode: "normal" | "complete") => {
    const modeLabel = mode === "complete" ? "彻底删除" : "普通删除";
    try {
      const result = await deleteTask(id, mode);
      let msg = `任务已${modeLabel}`;
      if (result.movies_affected > 0) {
        msg += `，影响 ${result.movies_affected} 部电影`;
      }
      if (result.magnets_deleted > 0) {
        msg += `，删除 ${result.magnets_deleted} 条磁力链接`;
      }
      message.success(msg);
      await loadTasks();
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  };

  const handleRun = async (id: string) => {
    try {
      message.loading({ content: "正在加入队列...", key: "run" });
      const runDoc = await runTask(id);
      message.success({ content: `已加入队列 (${runDoc.status})`, key: "run", duration: 2 });
      await navigate({to: "/crawler/runs"});
    } catch (e: unknown) {
      message.error({ content: getErrorMessage(e), key: "run" });
    }
  };

  const handleToggleSkip = async (task: CrawlTask) => {
    try {
      await updateTask(task._id, { is_skip: !task.is_skip });
      message.success(task.is_skip ? "任务已启用" : "任务已禁用");
      await loadTasks();
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  };

  const columns: ColumnsType<CrawlTask> = [
    {
      title: "名称",
      dataIndex: "name",
      key: "name",
      width: 200,
    },
    {
      title: "URL数量",
      key: "url_count",
      width: 100,
      render: (_: unknown, record: CrawlTask) => (
        <Tag>{record.urls?.length ?? 0} 个URL</Tag>
      ),
    },
    {
      title: "URL名称",
      key: "url_names",
      width: 250,
      render: (_: unknown, record: CrawlTask) => {
        const names = record.urls?.filter((u) => u.url_name).map((u) => u.url_name) ?? [];
        if (names.length === 0) {
          return <Typography.Text type="secondary">-</Typography.Text>;
        }
        return (
          <Space size={4} wrap>
            {names.map((name, i) => (
              <Tag key={i}>{name}</Tag>
            ))}
          </Space>
        );
      },
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
            onClick={() => navigate({ to: "/crawler/tasks/$id/edit", params: { id: record._id } })}
          >
            编辑
          </Button>
          <Dropdown
            menu={{
              items: [
                {
                  key: "normal",
                  label: "普通删除",
                  danger: false,
                  onClick: () => {
                    Modal.confirm({
                      title: "普通删除",
                      content: "将删除任务配置和运行记录，并从相关电影中移除此任务名称。电影和磁力链接数据将保留。",
                      onOk: () => handleDelete(record._id, "normal"),
                    });
                  },
                },
                {
                  key: "complete",
                  label: "彻底删除",
                  danger: true,
                  onClick: () => {
                    Modal.confirm({
                      title: "彻底删除",
                      content: "将删除任务配置、运行记录，以及由此任务爬取的所有电影和磁力链接。此操作不可恢复！",
                      okType: "danger",
                      onOk: () => handleDelete(record._id, "complete"),
                    });
                  },
                },
              ],
            }}
          >
            <Button danger icon={<DeleteOutlined />} size="small">
              删除 <DownOutlined />
            </Button>
          </Dropdown>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate({ to: "/crawler/tasks/new" })}>
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
