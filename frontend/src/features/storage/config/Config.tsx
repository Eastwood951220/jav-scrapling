import { useEffect, useState } from "react";
import {
  Form,
  Input,
  InputNumber,
  Switch,
  Button,
  Card,
  Tag,
  Space,
  message,
  Alert,
  Descriptions,
} from "antd";
import {
  CloudOutlined,
  ApiOutlined,
  FolderOutlined,
  FileOutlined,
  ClockCircleOutlined,
  FilterOutlined,
} from "@ant-design/icons";
import {
  fetchConfig,
  updateConfig,
  testConnection,
  type Config as ConfigType,
  type TestResult,
} from "./api";
import { getErrorMessage } from "@/shared/hooks/useErrorMessage";
import FullPageSpinner from "@/shared/components/FullPageSpinner";
import styles from "@/shared/styles/pages.module.css";

function TestResultCard({ result }: { result: TestResult }) {
  const items = [
    { label: "gRPC 连接", value: result.grpc_reachable, error: result.grpc_error },
    { label: "API 授权", value: result.api_authorized, error: result.api_error },
    { label: "下载目录", value: result.download_root_exists, error: result.download_root_error },
    { label: "目标文件夹", value: result.target_folder_accessible, error: result.target_folder_error },
  ];

  const allPassed = items.every((item) => item.value);

  return (
    <Card title="测试结果" className={styles.resultCard} size="small">
      <Descriptions column={2} size="small">
        {items.map((item) => (
          <Descriptions.Item key={item.label} label={item.label}>
            <Tag color={item.value ? "success" : "error"}>
              {item.value ? "通过" : "失败"}
            </Tag>
          </Descriptions.Item>
        ))}
      </Descriptions>
      {items.some((item) => !item.value && item.error) && (
        <Alert
          type="error"
          message="错误详情"
          description={
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {items
                .filter((item) => !item.value && item.error)
                .map((item) => (
                  <li key={item.label}>
                    {item.label}: {item.error}
                  </li>
                ))}
            </ul>
          }
          style={{ marginTop: 12 }}
          showIcon
        />
      )}
      {allPassed && (
        <Alert
          type="success"
          message="所有测试通过"
          style={{ marginTop: 12 }}
          showIcon
        />
      )}
    </Card>
  );
}

export default function Config() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [tokenInput, setTokenInput] = useState("");

  useEffect(() => {
    fetchConfig()
      .then((data: ConfigType) => {
        form.setFieldsValue(data);
      })
      .catch((e: unknown) => message.error(getErrorMessage(e)))
      .finally(() => setLoading(false));
  }, [form]);

  const handleSave = async (values: ConfigType) => {
    setSaving(true);
    try {
      const payload: Partial<ConfigType> = { ...values };
      if (tokenInput) {
        // api_token is not part of the form model, send it separately
        (payload as Record<string, unknown>).api_token = tokenInput;
      }
      await updateConfig(payload);
      message.success("存储配置已保存");
      // Refresh to get updated masked token
      const fresh = await fetchConfig();
      form.setFieldsValue(fresh);
      setTokenInput("");
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testConnection();
      setTestResult(result);
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    } finally {
      setTesting(false);
    }
  };

  const handleReset = () => {
    setLoading(true);
    setTestResult(null);
    setTokenInput("");
    fetchConfig()
      .then((data: ConfigType) => {
        form.setFieldsValue(data);
      })
      .catch((e: unknown) => message.error(getErrorMessage(e)))
      .finally(() => setLoading(false));
  };

  const maskDisplay =
    Form.useWatch("api_token_masked", form) as string | undefined;

  if (loading) return <FullPageSpinner />;

  return (
    <div style={{ maxWidth: 900 }}>
      <Form form={form} layout="vertical" onFinish={handleSave}>
        {/* 服务配置 */}
        <Card
          title={
            <span>
              <CloudOutlined /> 服务配置
            </span>
          }
          className={styles.formCard}
        >
          <Form.Item
            name="enabled"
            label="启用存储模块"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item
            name="grpc_host"
            label="gRPC 主机地址"
            rules={[{ required: true, message: "请输入 gRPC 主机地址" }]}
          >
            <Input placeholder="localhost:50051" />
          </Form.Item>
          <Form.Item label="API Token">
            <Space direction="vertical" style={{ width: "100%" }}>
              {maskDisplay && (
                <Tag color="blue">当前已配置: {maskDisplay}</Tag>
              )}
              <Input.Password
                placeholder="输入新的 API Token（留空则不修改）"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
              />
            </Space>
          </Form.Item>
          <Form.Item
            name="request_timeout_seconds"
            label="请求超时 (秒)"
          >
            <InputNumber min={5} max={300} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            name="connect_timeout_seconds"
            label="连接超时 (秒)"
          >
            <InputNumber min={5} max={60} style={{ width: "100%" }} />
          </Form.Item>
        </Card>

        {/* 目录配置 */}
        <Card
          title={
            <span>
              <FolderOutlined /> 目录配置
            </span>
          }
          className={styles.formCard}
        >
          <Form.Item
            name="download_root_folder"
            label="下载根目录"
            rules={[{ required: true, message: "请输入下载根目录" }]}
          >
            <Input placeholder="/downloads" />
          </Form.Item>
          <Form.Item
            name="target_folder"
            label="目标文件夹"
            rules={[{ required: true, message: "请输入目标文件夹" }]}
          >
            <Input placeholder="/media/movies" />
          </Form.Item>
          <Form.Item
            name="use_task_subfolder"
            label="使用任务子文件夹"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item
            name="auto_create_target_folder"
            label="自动创建目标文件夹"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
        </Card>

        {/* 文件命名 */}
        <Card
          title={
            <span>
              <FileOutlined /> 文件命名
            </span>
          }
          className={styles.formCard}
        >
          <Form.Item
            name="single_filename_template"
            label="单文件命名模板"
          >
            <Input placeholder="{title}.{ext}" />
          </Form.Item>
          <Form.Item
            name="multi_filename_template"
            label="多文件命名模板"
          >
            <Input placeholder="{title}/{filename}.{ext}" />
          </Form.Item>
        </Card>

        {/* 任务执行 */}
        <Card
          title={
            <span>
              <ClockCircleOutlined /> 任务执行
            </span>
          }
          className={styles.formCard}
        >
          <Form.Item name="operation_delay_min" label="操作最小延迟 (秒)">
            <InputNumber min={0} max={60} step={0.5} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="operation_delay_max" label="操作最大延迟 (秒)">
            <InputNumber min={0} max={60} step={0.5} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            name="download_poll_interval_min"
            label="下载轮询最小间隔 (秒)"
          >
            <InputNumber min={1} max={120} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            name="download_poll_interval_max"
            label="下载轮询最大间隔 (秒)"
          >
            <InputNumber min={1} max={120} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="retry_delay_min" label="重试最小延迟 (秒)">
            <InputNumber min={0} max={120} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="retry_delay_max" label="重试最大延迟 (秒)">
            <InputNumber min={0} max={120} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="max_step_retries" label="最大重试次数">
            <InputNumber min={0} max={20} style={{ width: "100%" }} />
          </Form.Item>
        </Card>

        {/* 文件筛选 */}
        <Card
          title={
            <span>
              <FilterOutlined /> 文件筛选
            </span>
          }
          className={styles.formCard}
        >
          <Form.Item
            name="minimum_video_size_mb"
            label="最小视频大小 (MB)"
          >
            <InputNumber min={0} max={10000} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            name="video_extensions"
            label="视频扩展名"
            tooltip="输入扩展名后按回车添加"
          >
            <SelectTags placeholder="例如: .mp4, .mkv" />
          </Form.Item>
          <Form.Item
            name="excluded_filename_keywords"
            label="排除文件名关键词"
            tooltip="输入关键词后按回车添加"
          >
            <SelectTags placeholder="例如: sample, trailer" />
          </Form.Item>
          <Form.Item
            name="keep_subtitles"
            label="保留字幕文件"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item
            name="keep_cover_images"
            label="保留封面图片"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item
            name="delete_empty_folders"
            label="删除空文件夹"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
        </Card>

        {/* 操作按钮 */}
        <Card title="操作" className={styles.formCard}>
          <Space>
            <Button
              icon={<ApiOutlined />}
              onClick={handleTest}
              loading={testing}
            >
              测试连接
            </Button>
            <Button type="primary" htmlType="submit" loading={saving}>
              保存配置
            </Button>
            <Button onClick={handleReset}>重置</Button>
          </Space>
        </Card>
      </Form>

      {testResult && <TestResultCard result={testResult} />}
    </div>
  );
}

/** Simple tag-input component for string arrays. */
function SelectTags({
  value,
  onChange,
  placeholder,
}: {
  value?: string[];
  onChange?: (val: string[]) => void;
  placeholder?: string;
}) {
  const [input, setInput] = useState("");

  const handleInputConfirm = () => {
    const trimmed = input.trim();
    if (trimmed && !value?.includes(trimmed)) {
      onChange?.([...(value ?? []), trimmed]);
    }
    setInput("");
  };

  const handleClose = (removed: string) => {
    onChange?.(value?.filter((v) => v !== removed) ?? []);
  };

  return (
    <div>
      <Space wrap style={{ marginBottom: 8 }}>
        {value?.map((tag) => (
          <Tag key={tag} closable onClose={() => handleClose(tag)}>
            {tag}
          </Tag>
        ))}
      </Space>
      <Input
        size="small"
        placeholder={placeholder}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onPressEnter={handleInputConfirm}
        onBlur={handleInputConfirm}
      />
    </div>
  );
}
