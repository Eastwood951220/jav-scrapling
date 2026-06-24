import { useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { Layout as AntLayout, Menu, Typography } from "antd";
import {
  UnorderedListOutlined,
  SettingOutlined,
  ClockCircleOutlined,
  PlayCircleOutlined,
  HistoryOutlined,
} from "@ant-design/icons";

const { Sider, Content, Header } = AntLayout;

const menuItems = [
  { key: "/tasks", icon: <UnorderedListOutlined />, label: "任务配置" },
  { key: "/schedules", icon: <ClockCircleOutlined />, label: "定时任务" },
  { key: "/settings", icon: <SettingOutlined />, label: "系统设置" },
  { key: "/runs", icon: <HistoryOutlined />, label: "运行历史" },
  { key: "/movies", icon: <PlayCircleOutlined />, label: "内容浏览" },
];

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const selectedKey = menuItems.find((item) =>
    location.pathname.startsWith(item.key)
  )?.key || "/tasks";

  return (
    <AntLayout style={{ minHeight: "100vh" }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
      >
        <div
          style={{
            height: 48,
            margin: 16,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Typography.Text
            strong
            style={{ color: "#fff", fontSize: collapsed ? 14 : 18 }}
          >
            {collapsed ? "JS" : "Jav Scrapling"}
          </Typography.Text>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <AntLayout>
        <Header
          style={{
            background: "#fff",
            padding: "0 24px",
            borderBottom: "1px solid #f0f0f0",
          }}
        >
          <Typography.Title level={4} style={{ margin: "16px 0" }}>
            {menuItems.find((item) => location.pathname.startsWith(item.key))?.label || "配置管理"}
          </Typography.Title>
        </Header>
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
