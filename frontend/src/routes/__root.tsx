import { Outlet, createRootRoute } from "@tanstack/react-router";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import ErrorBoundary from "../shared/components/ErrorBoundary";
import { lightTheme } from "../theme";

export const Route = createRootRoute({
  component: () => (
    <ConfigProvider locale={zhCN} theme={lightTheme}>
      <ErrorBoundary>
        <Outlet />
      </ErrorBoundary>
    </ConfigProvider>
  ),
});
