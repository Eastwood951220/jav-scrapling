import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import Layout from "./components/Layout";
import TaskList from "./pages/TaskList";
import TaskForm from "./pages/TaskForm";
import Settings from "./pages/Settings";
import Schedules from "./pages/Schedules";
import Movies from "./pages/Movies";
import RunList from "./pages/RunList";
import RunDetail from "./pages/RunDetail";

export default function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Navigate to="/tasks" replace />} />
            <Route path="/tasks" element={<TaskList />} />
            <Route path="/tasks/new" element={<TaskForm />} />
            <Route path="/tasks/:id/edit" element={<TaskForm />} />
            <Route path="/schedules" element={<Schedules />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/runs" element={<RunList />} />
            <Route path="/runs/:id" element={<RunDetail />} />
            <Route path="/movies" element={<Movies />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}
