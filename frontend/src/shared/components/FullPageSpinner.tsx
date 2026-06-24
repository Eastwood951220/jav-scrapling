import { Spin } from "antd";

/**
 * Full-page centered spinner. Replaces the duplicated pattern:
 * `<Spin size="large" style={{ display: "block", margin: "100px auto" }} />`
 */
export default function FullPageSpinner() {
  return (
    <Spin
      size="large"
      style={{ display: "block", margin: "100px auto" }}
      aria-label="加载中"
    />
  );
}
