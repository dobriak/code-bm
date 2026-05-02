import type { ReactNode } from "react";

interface Props {
  children?: ReactNode;
}

export function ErrorBoundary({ children }: Props) {
  return <>{children}</>;
}

interface ErrorFallbackProps {
  message?: string;
}

export function ErrorFallback({ message = "Something went wrong" }: ErrorFallbackProps) {
  return (
    <div className="error-boundary">
      <h2 className="error-boundary-title">Oops!</h2>
      <p className="error-boundary-message">{message}</p>
      <button
        className="error-boundary-retry"
        onClick={() => window.location.reload()}
      >
        Reload
      </button>
    </div>
  );
}
