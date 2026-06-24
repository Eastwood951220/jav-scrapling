import { useEffect, useState } from "react";
import { useNavigate, useParams } from "@tanstack/react-router";
import { Form, Input, InputNumber, Switch, Select, Button, Card, message } from "antd";
import { createTask, fetchTask, updateTask } from "./api";
import FullPageSpinner from "../../shared/components/FullPageSpinner";
import { getErrorMessage } from "../../shared/hooks/useErrorMessage";

export default function TaskForm() {
  const { id } = useParams({ strict: false }) as { id?: string };
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!isEdit || !id) return;

    setLoading(true);
    fetchTask(id)
      .then((task) => {
        form.setFieldsValue({
          name: task.name,
          url: task.url,
          url_type: task.url_type,
          is_skip: task.is_skip,
          max_list_pages: task.max_list_pages,
          only_chinese: task.filter?.only_chinese ?? false,
          exclude_multi_person: task.filter?.exclude_multi_person ?? false,
        });
      })
      .catch((e) => message.error(getErrorMessage(e)))
      .finally(() => setLoading(false));
  }, [id, isEdit, form]);

  const handleSubmit = async (values: Record<string, unknown>) => {
    setSubmitting(true);
    try {
      const payload = {
        name: values.name as string,
        url: values.url as string,
        url_type: values.url_type as string,
        is_skip: values.is_skip as boolean,
        max_list_pages: values.max_list_pages as number,
        filter: {
          only_chinese: (values.only_chinese as boolean) ?? false,
          exclude_multi_person: (values.exclude_multi_person as boolean) ?? false,
        },
      };

      if (isEdit && id) {
        await updateTask(id, payload);
        message.success("任务已更新");
      } else {
        await createTask(payload);
        message.success("任务已创建");
      }
      navigate({ to: "/tasks" });
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <FullPageSpinner />;

  return (
    <Card title={isEdit ? "编辑任务" : "新建任务"} style={{ maxWidth: 700 }}>
      <Form form={form} layout="vertical" onFinish={handleSubmit} initialValues={{
        url_type: "actors",
        is_skip: false,
        max_list_pages: 50,
        only_chinese: false,
        exclude_multi_person: false,
      }}>
        <Form.Item name="name" label="任务名称" rules={[{ required: true, message: "请输入任务名称" }]}>
          <Input placeholder="例如：某演员名称" />
        </Form.Item>

        <Form.Item name="url" label="URL" rules={[{ required: true, message: "请输入URL" }]}>
          <Input placeholder="https://javdb.com/actors/..." />
        </Form.Item>

        <Form.Item name="url_type" label="URL类型" rules={[{ required: true }]}>
          <Select
            options={[
              { value: "actors", label: "演员 (actors)" },
              { value: "search", label: "搜索 (search)" },
              { value: "tags", label: "标签 (tags)" },
              { value: "lists", label: "列表 (lists)" },
            ]}
          />
        </Form.Item>

        <Form.Item name="max_list_pages" label="最大翻页数">
          <InputNumber min={1} max={100} />
        </Form.Item>

        <Form.Item name="is_skip" label="禁用此任务" valuePropName="checked">
          <Switch />
        </Form.Item>

        <Card title="过滤条件" size="small" style={{ marginBottom: 24 }}>
          <Form.Item name="only_chinese" label="仅中文字幕" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="exclude_multi_person" label="排除多人作品" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Card>

        <Form.Item>
          <Button type="primary" htmlType="submit" loading={submitting}>
            {isEdit ? "更新" : "创建"}
          </Button>
          <Button style={{ marginLeft: 8 }} onClick={() => navigate({ to: "/tasks" })}>
            取消
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
}
