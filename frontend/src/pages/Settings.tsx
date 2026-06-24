import { useEffect, useState } from "react";
import { Form, Input, InputNumber, Switch, Button, Card, message } from "antd";
import { fetchSettings, updateSettings, AppSettings } from "../api/settings";
import { getErrorMessage } from "../hooks/useErrorMessage";
import FullPageSpinner from "../components/FullPageSpinner";
import styles from "../styles/pages.module.css";

export default function Settings() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSettings()
      .then((data: AppSettings) => {
        form.setFieldsValue(data);
      })
      .catch((e: unknown) => message.error(getErrorMessage(e)))
      .finally(() => setLoading(false));
  }, [form]);

  const handleSave = async (values: AppSettings) => {
    setSaving(true);
    try {
      await updateSettings(values);
      message.success("设置已保存");
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <FullPageSpinner />;

  return (
    <div className={styles.formContainer}>
      <Form form={form} layout="vertical" onFinish={handleSave}>
        <Card title="数据库连接" className={styles.formCard}>
          <Form.Item name="MONGO_URI" label="MongoDB URI">
            <Input placeholder="mongodb://admin:admin123@mongo:27017/" />
          </Form.Item>
          <Form.Item name="MONGO_DB_NAME" label="数据库名称">
            <Input placeholder="jav" />
          </Form.Item>
          <Form.Item name="MONGO_CONNECT_TIMEOUT_MS" label="连接超时 (ms)">
            <InputNumber min={1000} max={30000} style={{ width: "100%" }} />
          </Form.Item>
        </Card>

        <Card title="爬取参数" className={styles.formCard}>
          <Form.Item name="MAX_LIST_PAGES" label="最大翻页数">
            <InputNumber min={1} max={100} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="LIST_PAGE_DELAY_MIN" label="列表页最小延迟 (秒)">
            <InputNumber min={0} max={60} step={0.5} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="LIST_PAGE_DELAY_MAX" label="列表页最大延迟 (秒)">
            <InputNumber min={0} max={60} step={0.5} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="DETAIL_PAGE_DELAY_MIN" label="详情页最小延迟 (秒)">
            <InputNumber min={0} max={60} step={0.5} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="DETAIL_PAGE_DELAY_MAX" label="详情页最大延迟 (秒)">
            <InputNumber min={0} max={60} step={0.5} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="SECURITY_WAIT_SECONDS" label="安全验证等待 (秒)">
            <InputNumber min={10} max={600} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="REQUEST_TIMEOUT" label="请求超时 (秒)">
            <InputNumber min={5} max={120} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="USE_DYNAMIC_FETCHER" label="动态抓取" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="BATCH_SAVE_SIZE" label="批量写入大小 (条)">
            <InputNumber min={1} max={1000} style={{ width: "100%" }} />
          </Form.Item>
        </Card>

        <Form.Item>
          <Button type="primary" htmlType="submit" loading={saving}>
            保存设置
          </Button>
        </Form.Item>
      </Form>
    </div>
  );
}
