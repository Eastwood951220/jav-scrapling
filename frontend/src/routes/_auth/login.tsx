import { createFileRoute } from "@tanstack/react-router";
import { Card, Result } from "antd";

export const Route = createFileRoute("/_auth/login")({
  component: LoginPage,
});

function LoginPage() {
  return (
    <Card>
      <Result
        status="info"
        title="登录功能开发中"
        subTitle="此功能将在后续版本中实现"
      />
    </Card>
  );
}
