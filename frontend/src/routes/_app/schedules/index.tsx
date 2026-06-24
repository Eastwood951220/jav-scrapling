import { createFileRoute } from "@tanstack/react-router";
import Schedules from "../../../features/schedules/Schedules";

export const Route = createFileRoute("/_app/schedules/")({
  component: Schedules,
});
