import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/context/auth-context";
import { WalletProvider, useWalletContext } from "@/context/wallet-context";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { TopBar } from "@/components/layout/TopBar";
import { MobileNav } from "@/components/layout/MobileNav";
import { SidebarProvider } from "@/components/ui/sidebar";
import LoadingPage from "@/components/shared/LoadingPage";

const ONBOARDING_KEY = "onboarding_done";

function AppContent() {
  const { needsSetup, isLoading } = useWalletContext();
  const location = useLocation();

  if (isLoading) {
    return <LoadingPage />;
  }

  if (needsSetup && location.pathname !== "/setup") {
    return <Navigate to="/setup" replace />;
  }

  return (
    <SidebarProvider className="h-svh overflow-hidden">
      <div className="flex h-full min-h-0 w-full flex-col overflow-hidden">
        <TopBar />
        <div className="flex min-h-0 flex-1 overflow-hidden">
          <AppSidebar />
          <main className="min-h-0 min-w-0 flex-1 overflow-y-auto p-4 pb-20 md:p-6 md:pb-6">
            <Outlet />
          </main>
        </div>
        <MobileNav />
      </div>
    </SidebarProvider>
  );
}

export default function RootLayout() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <LoadingPage />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Check onboarding completion
  const onboardingDone = localStorage.getItem(ONBOARDING_KEY) === "true";
  if (!onboardingDone) {
    return <Navigate to="/intro" replace />;
  }

  return (
    <WalletProvider>
      <AppContent />
    </WalletProvider>
  );
}
