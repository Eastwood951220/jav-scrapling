import { useEffect, useState } from "react";
import { Table, Button, Modal, Form, Input, Select, Switch, Space, Popconfirm, message, Tag } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { Schedule, fetchSchedules, createSchedule, updateSchedule, deleteSchedule } from "./api";
import { CrawlTask, fetchTasks } from "@/features/tasks/api";
import { getErrorMessage } from "@/shared/hooks/useErrorMessage";

export default function Schedules() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [tasks, setTasks] = useState<CrawlTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Schedule | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try {
      const [s, t] = await Promise.all([fetchSchedules(), fetchTasks()]);
      setSchedules(s);
      setTasks(t);
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleSubmit = async (values: Record<string, unknown>) => {
    setSubmitting(true);
    try {
      const payload = {
        name: values.name as string,
        task_ids: (values.task_ids as string[]) || [],
        cron_expression: values.cron_expression as string,
        enabled: (values.enabled as boolean) ?? true,
      };

      if (editing) {
        await updateSchedule(editing._id, payload);
        message.success("定时任务已更新");
      } else {
        await createSchedule(payload);
        message.success("定时任务已创建");
      }
      setModalOpen(false);
      setEditing(null);
      form.resetFields();
      load();
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteSchedule(id);
      message.success("已删除");
      load();
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    }
  };

  const openEdit = (schedule: Schedule) => {
    setEditing(schedule);
    form.setFieldsValue(schedule);
    setModalOpen(true);
  };

  const columns: ColumnsType<Schedule> = [
    { title: "名称", dataIndex: "name", key: "name" },
    { title: "Cron表达式", dataIndex: "cron_expression", key: "cron_expression" },
    {
      title: "关联任务",
      dataIndex: "task_ids",
      key: "task_ids",
      render: (ids: string[]) =>
        ids.map((id) => {
          const task = tasks.find((t) => t._id === id);
          return <Tag key={id}>{task?.name || id}</Tag>;
        }),
    },
    {
      title: "状态",
      dataIndex: "enabled",
      key: "enabled",
      render: (enabled: boolean) => (
        <Tag color={enabled ? "green" : "red"}>{enabled ? "启用" : "禁用"}</Tag>
      ),
    },
    {
      title: "操作",
      key: "actions",
      render: (_: unknown, record: Schedule) => (
        <Space>
          <Button icon={<EditOutlined />} size="small" onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record._id)}>
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
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            setEditing(null);
            form.resetFields();
            form.setFieldsValue({ enabled: true, task_ids: [], cron_expression: "0 2 * * *" });
            setModalOpen(true);
          }}
        >
          新建定时任务
        </Button>
      </div>

      <Table columns={columns} dataSource={schedules} rowKey="_id" loading={loading} />

      <Modal
        title={editing ? "编辑定时任务" : "新建定时任务"}
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false);
          setEditing(null);
        }}
        onOk={() => form.submit()}
        confirmLoading={submitting}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="每日凌晨爬取" />
          </Form.Item>
          <Form.Item name="cron_expression" label="Cron表达式" rules={[{ required: true }]}>
            <Input placeholder="0 2 * * *" />
          </Form.Item>
          <Form.Item name="task_ids" label="关联任务">
            <Select
              mode="multiple"
              placeholder="选择要执行的任务"
              options={tasks.map((t) => ({ value: t._id, label: t.name }))}
            />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
