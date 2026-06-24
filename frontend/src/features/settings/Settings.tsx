import { useCallback, useEffect, useRef, useState } from "react";
import { Form, Input, InputNumber, Switch, Button, Card, message, Typography } from "antd";
import Editor, { type OnMount } from "@monaco-editor/react";
import { fetchSettings, updateSettings, fetchCookiesConfig, updateCookiesConfig, type AppSettings, type CookiesConfig } from "./api";
import { getErrorMessage } from "@/shared/hooks/useErrorMessage";
import FullPageSpinner from "@/shared/components/FullPageSpinner";
import styles from "@/shared/styles/pages.module.css";

const DEFAULT_COOKIE_JSON = `[
  {
    "domain": "javdb.com",
    "name": "",
    "value": "",
    "path": "/"
  }
]`;

export default function Settings() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [cookieSaving, setCookieSaving] = useState(false);
  const [cookieJson, setCookieJson] = useState("");
  const [cookieLoading, setCookieLoading] = useState(true);
  const [jsonError, setJsonError] = useState<string | null>(null);
  const editorRef = useRef<Parameters<OnMount>[0] | null>(null);

  // Load app settings
  useEffect(() => {
    fetchSettings()
      .then((data: AppSettings) => {
        form.setFieldsValue(data);
      })
      .catch((e: unknown) => message.error(getErrorMessage(e)))
      .finally(() => setLoading(false));
  }, [form]);

  // Load cookies config
  useEffect(() => {
    fetchCookiesConfig()
      .then((data: CookiesConfig) => {
        setCookieJson(JSON.stringify(data.cookies, null, 2));
      })
      .catch(() => {
        // No cookie file yet — show default template
        setCookieJson(DEFAULT_COOKIE_JSON);
      })
      .finally(() => setCookieLoading(false));
  }, []);

  const handleEditorMount: OnMount = useCallback((editor) => {
    editorRef.current = editor;
  }, []);

  const validateJson = (value: string): boolean => {
    try {
      const parsed = JSON.parse(value);
      if (!Array.isArray(parsed)) {
        setJsonError("Cookie 配置必须是 JSON 数组格式");
        return false;
      }
      setJsonError(null);
      return true;
    } catch (e: unknown) {
      const msg = e instanceof SyntaxError ? e.message : "无效的 JSON 格式";
      setJsonError(msg);
      return false;
    }
  };

  const handleCookieChange = (value: string | undefined) => {
    const text = value ?? "";
    setCookieJson(text);
    if (text.trim()) {
      validateJson(text);
    } else {
      setJsonError(null);
    }
  };

  const handleSaveSettings = async (values: AppSettings) => {
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

  const handleSaveCookies = async () => {
    if (!validateJson(cookieJson)) {
      message.error("请先修复 JSON 格式错误再保存");
      return;
    }
    setCookieSaving(true);
    try {
      const cookies = JSON.parse(cookieJson);
      await updateCookiesConfig({ cookies });
      message.success("Cookie 配置已保存");
    } catch (e: unknown) {
      message.error(getErrorMessage(e));
    } finally {
      setCookieSaving(false);
    }
  };

  const handleFormatJson = () => {
    try {
      const parsed = JSON.parse(cookieJson);
      const formatted = JSON.stringify(parsed, null, 2);
      setCookieJson(formatted);
      setJsonError(null);
    } catch {
      // Can't format invalid JSON — do nothing
    }
  };

  if (loading) return <FullPageSpinner />;

  return (
    <div className={styles.formContainer}>
      <Form form={form} layout="vertical" onFinish={handleSaveSettings}>
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

      {/* Cookie configuration card */}
      <Card
        title="Cookie 配置"
        className={styles.formCard}
        extra={
          <div style={{ display: "flex", gap: 8 }}>
            <Button onClick={handleFormatJson} disabled={!!jsonError && cookieJson.trim() !== ""}>
              格式化
            </Button>
            <Button type="primary" onClick={handleSaveCookies} loading={cookieSaving}>
              保存 Cookie
            </Button>
          </div>
        }
      >
        {cookieLoading ? (
          <FullPageSpinner />
        ) : (
          <>
            <div style={{ border: "1px solid #d9d9d9", borderRadius: 6, overflow: "hidden" }}>
              <Editor
                height="400px"
                defaultLanguage="json"
                value={cookieJson}
                onChange={handleCookieChange}
                onMount={handleEditorMount}
                options={{
                  minimap: { enabled: false },
                  lineNumbers: "on",
                  scrollBeyondLastLine: false,
                  wordWrap: "on",
                  tabSize: 2,
                  formatOnPaste: true,
                }}
              />
            </div>
            {jsonError && (
              <Typography.Text type="danger" style={{ display: "block", marginTop: 8 }}>
                JSON 格式错误: {jsonError}
              </Typography.Text>
            )}
          </>
        )}
      </Card>
    </div>
  );
}
