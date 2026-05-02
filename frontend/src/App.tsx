import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import PlayerAudio from "./components/PlayerAudio";

const queryClient = new QueryClient();

interface HealthResponse {
  status: string;
  version: string;
}

function HealthIndicator() {
  const { data, isLoading, error } = useQuery<HealthResponse>({
    queryKey: ["health"],
    queryFn: () => fetch("/api/v1/health").then((r) => r.json()),
    refetchInterval: 10000,
  });

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.5rem",
      }}
    >
      <span
        style={{
          width: "10px",
          height: "10px",
          borderRadius: "50%",
          backgroundColor:
            isLoading ? "#f59e0b" : error ? "#ef4444" : "#22c55e",
        }}
      />
      <span style={{ fontSize: "0.875rem", opacity: 0.7 }}>
        {isLoading
          ? "checking…"
          : error
            ? "backend unreachable"
            : `backend ok — v${data?.version}`}
      </span>
    </span>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "system-ui, -apple-system, sans-serif",
          backgroundColor: "#0f0f0f",
          color: "#fafafa",
          gap: "2rem",
        }}
      >
        <h1 style={{ fontSize: "3rem", fontWeight: 700, letterSpacing: "-0.02em" }}>
          Raidio
        </h1>
        <p>
          <HealthIndicator />
        </p>
        <PlayerAudio />
      </div>
    </QueryClientProvider>
  );
}

export default App;
