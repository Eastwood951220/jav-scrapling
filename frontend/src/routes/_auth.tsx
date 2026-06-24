import { Outlet, createFileRoute } from "@tanstack/react-router";
import AuthLayout from "../shared/components/AuthLayout";

export const Route = createFileRoute("/_auth")({
  component: () => (
    <AuthLayout>
      <Outlet />
    </AuthLayout>
  ),
});
