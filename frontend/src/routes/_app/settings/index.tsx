import { createFileRoute } from "@tanstack/react-router";
import Settings from "../../../features/settings/Settings";

export const Route = createFileRoute("/_app/settings/")({
  component: Settings,
});
