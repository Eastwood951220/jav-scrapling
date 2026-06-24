import { createFileRoute } from "@tanstack/react-router";
import TaskList from "../../../features/tasks/TaskList";

export const Route = createFileRoute("/_app/tasks/")({
  component: TaskList,
});
