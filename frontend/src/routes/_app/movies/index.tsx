import { createFileRoute } from "@tanstack/react-router";
import Movies from "../../../features/movies/Movies";

export const Route = createFileRoute("/_app/movies/")({
  component: Movies,
});
