import { Component, ErrorInfo, ReactNode, type MouseEvent } from "react";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";
import { AlertTriangle, RefreshCw, Copy } from "lucide-react";
import api, { type ErrorReportCreateRequest } from "@/lib/api";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error?: Error;
}

/**
 * ErrorBoundary provides a way to catch JavaScript errors anywhere in the child component tree
 */
export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  private lastLoggedErrorSignature: string | null = null;

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);

    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    const signature = `${error.name}:${error.message}:${error.stack ?? ""}`;
    if (signature !== this.lastLoggedErrorSignature) {
      this.lastLoggedErrorSignature = signature;
      this.reportError(error, errorInfo);
    }
  }

  private handleRetry = () => {
    this.setState({ hasError: false, error: undefined });
    this.lastLoggedErrorSignature = null;
  };

  private handleCopyError = (event: MouseEvent<HTMLButtonElement>) => {
    if (this.state.error) {
      const errorText = `Error: ${this.state.error.message}\n\nStack trace:\n${this.state.error.stack}`;
      navigator.clipboard.writeText(errorText)
        .then(() => {
          // Show brief success feedback
          const originalText = event.currentTarget.innerHTML;
          event.currentTarget.innerHTML = "Copied!";
          setTimeout(() => {
            event.currentTarget.innerHTML = originalText;
          }, 2000);
        })
        .catch((err) => {
          console.error("Failed to copy error text: ", err);
        });
    }
  };

  private reportError(error: Error, errorInfo: ErrorInfo) {
    const payload: ErrorReportCreateRequest = {
      message: error.message,
      name: error.name,
      stack: error.stack ?? undefined,
      componentStack: errorInfo.componentStack || undefined,
      url: typeof window !== "undefined" ? window.location.href : undefined,
      userAgent: typeof navigator !== "undefined" ? navigator.userAgent : undefined,
      metadata: {
        boundary: "ErrorBoundary",
        locale: typeof navigator !== "undefined" ? navigator.language : undefined,
        timezone:
          typeof Intl !== "undefined" && typeof Intl.DateTimeFormat === "function"
            ? Intl.DateTimeFormat().resolvedOptions().timeZone
            : undefined,
      },
    };

    void api.errorReports
      .create(payload)
      .catch((reportError) => {
        console.warn("Failed to persist error report", reportError);
      });
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-[520px] items-center justify-center bg-[#E2E8F0] px-4 py-16">
          <div className="relative w-full max-w-2xl overflow-hidden rounded-3xl border border-white/20 bg-gradient-to-b from-[#0f1f30] via-[#091525] to-[#1d2734] shadow-[0_24px_80px_rgba(8,145,178,0.32)]">
            <div
              className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(8,145,178,0.35),_transparent_65%)] opacity-90"
              aria-hidden="true"
            />
            <div className="relative z-10 flex flex-col items-center gap-6 px-6 py-12 text-center sm:px-12">
              <div className="relative flex flex-col items-center gap-6">
                <div className="absolute inset-0 -z-10 flex items-center justify-center">
                  <div className="h-52 w-52 rounded-full bg-brand-primaryTeal/20 blur-[110px]" aria-hidden="true" />
                </div>
                <Logo
                  variant="light"
                  animated
                  className="h-32 w-auto drop-shadow-[0_28px_60px_rgba(8,145,178,0.35)]"
                />
                <div className="flex items-center justify-center rounded-full bg-brand-accentOrange/15 p-4 shadow-inner shadow-brand-accentOrange/25">
                  <AlertTriangle className="h-10 w-10 text-brand-accentOrange" />
                </div>
              </div>

              <div className="space-y-3">
                <h2 className="text-3xl font-semibold text-slate-50">Something went wrong</h2>
                <p className="mx-auto max-w-xl text-base text-slate-200/80">
                  An unexpected error occurred. You can try refreshing the page or return to the previous view. If the issue keeps happening, please reach out to support with the details below.
                </p>
              </div>

              {process.env.NODE_ENV === "development" && this.state.error && (
                <div className="w-full space-y-3 rounded-2xl border border-white/15 bg-white/5 p-5 text-left shadow-inner">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-brand-accentOrange/90">
                      Error details · Development only
                    </h3>
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-medium text-slate-100/70">
                        {new Date().toLocaleTimeString()}
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={this.handleCopyError}
                        className="flex items-center gap-2 border-white/20 bg-white/10 text-xs text-slate-200 hover:bg-white/20"
                      >
                        <Copy className="h-3 w-3" />
                        Copy
                      </Button>
                    </div>
                  </div>
                  <div className="max-h-48 overflow-auto rounded-xl border border-white/10 bg-black/50 p-4 text-xs font-mono text-brand-mint/80">
                    <pre className="whitespace-pre-wrap break-words">
                      {this.state.error.message}
                      {"\n\n"}
                      {this.state.error.stack}
                    </pre>
                  </div>
                </div>
              )}

              <div className="mt-2 flex w-full flex-col gap-3 sm:flex-row">
                <Button
                  variant="outline"
                  onClick={() => window.location.reload()}
                  className="flex w-full items-center justify-center gap-2 bg-brand-primaryTeal text-white shadow-lg shadow-brand-primaryTeal/30 hover:bg-brand-primaryTeal/90"
                >
                  <RefreshCw className="h-4 w-4" />
                  Refresh Page
                </Button>
                <Button
                  onClick={this.handleRetry}
                  className="flex w-full items-center justify-center gap-2 bg-brand-accentOrange text-white shadow-lg shadow-brand-accentOrange/30 hover:bg-brand-accentOrange/90"
                >
                  Try Again
                </Button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
