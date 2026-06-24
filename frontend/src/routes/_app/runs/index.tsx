import { createFileRoute } from "@tanstack/react-router";
import RunList from "../../../features/runs/RunList";

export const Route = createFileRoute("/_app/runs/")({
  component: RunList,
});
