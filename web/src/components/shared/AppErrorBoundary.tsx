import { ErrorBoundary, type FallbackProps } from "react-error-boundary";
import { AlertTriangle, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function ErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  const message = error instanceof Error ? error.message : "Something went wrong.";

  return (
    <div className="flex min-h-svh items-center justify-center bg-background p-4 text-foreground">
      <Card className="w-full max-w-xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-5 w-5" />
            Unexpected application error
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            The app caught this error so the whole UI does not crash.
          </p>
          <pre className="max-h-48 overflow-auto rounded-md bg-muted p-3 text-xs text-muted-foreground">
            {message}
          </pre>
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={resetErrorBoundary}>
              <RotateCcw className="h-4 w-4" />
              Try again
            </Button>
            <Button type="button" variant="outline" onClick={() => window.location.assign("/dashboard")}>
              Go to dashboard
            </Button>
            <Button type="button" variant="ghost" onClick={() => window.location.reload()}>
              Reload page
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export function AppErrorBoundary({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary
      FallbackComponent={ErrorFallback}
      onError={(error, info) => {
        console.error("Application error boundary caught an error", error, info);
      }}
    >
      {children}
    </ErrorBoundary>
  );
}
