import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Space, Popconfirm, message, Switch } from "antd";
import { PlusOutlined, PlayCircleOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { CrawlTask, fetchTasks, deleteTask, runTask, updateTask } from "../api/tasks";

export default function TaskList() {
  const [tasks, setTasks] = useState<CrawlTask[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetchTasks();
      setTasks(data);
    } catch (e: unknown) {
      message.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleDelete = async (id: string) => {
    try {
      await deleteTask(id);
      message.success("任务已删除");
      load();
    } catch (e: unknown) {
      message.error((e as Error).message);
    }
  };

  const handleRun = async (id: string) => {
    try {
      message.loading({ content: "正在加入队列...", key: "run" });
      const runDoc = await runTask(id);
      message.success({ content: `已加入队列 (${runDoc.status})`, key: "run", duration: 2 });
      navigate("/runs");
    } catch (e: unknown) {
      message.error({ content: (e as Error).message, key: "run" });
    }
  };

  const handleToggleSkip = async (task: CrawlTask) => {
    try {
      await updateTask(task._id, { is_skip: !task.is_skip });
      message.success(task.is_skip ? "任务已启用" : "任务已禁用");
      load();
    } catch (e: unknown) {
      message.error((e as Error).message);
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
            onClick={() => navigate(`/tasks/${record._id}/edit`)}
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
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/tasks/new")}>
          新建任务
        </Button>
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
