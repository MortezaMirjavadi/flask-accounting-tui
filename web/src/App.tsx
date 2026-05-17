import { RouterProvider } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/context/auth-context";
import { router } from "@/router";
import { Toaster } from "@/components/ui/sonner";
import { AppErrorBoundary } from "@/components/shared/AppErrorBoundary";
import "@/i18n";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <AppErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <RouterProvider router={router} />
          <Toaster richColors position="top-center" />
        </AuthProvider>
      </QueryClientProvider>
    </AppErrorBoundary>
  );
}
