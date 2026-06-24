import { createFileRoute } from "@tanstack/react-router";
import TaskForm from "../../../features/tasks/TaskForm";

export const Route = createFileRoute("/_app/tasks/new")({
  component: TaskForm,
});
