import { createFileRoute } from "@tanstack/react-router";
import RunDetail from "../../../features/runs/RunDetail";

export const Route = createFileRoute("/_app/runs/$id")({
  component: RunDetail,
});
