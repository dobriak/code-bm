import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { useUserStore } from "./stores/userStore";
import PlayerPage from "./pages/PlayerPage";
import CreatePage from "./pages/CreatePage";
import AdminPage from "./pages/AdminPage";
import AdminLoginPage from "./pages/AdminLoginPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

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
          width: "8px",
          height: "8px",
          borderRadius: "50%",
          backgroundColor:
            isLoading ? "#f59e0b" : error ? "#ef4444" : "#22c55e",
        }}
      />
      <span style={{ fontSize: "0.75rem", opacity: 0.5 }}>
        {isLoading
          ? "checking…"
          : error
            ? "offline"
            : `v${data?.version}`}
      </span>
    </span>
  );
}

function UserIdentity() {
  const label = useUserStore((s) => s.label);
  const reroll = useUserStore((s) => s.reroll);

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.5rem",
        fontSize: "0.75rem",
        color: "#888",
        cursor: "pointer",
      }}
      onClick={reroll}
      title="Click to get a new name"
    >
      🎧 {label}
      <span style={{ fontSize: "0.625rem", opacity: 0.5 }}>↻</span>
    </span>
  );
}

function NavLayout() {
  return (
    <div style={{ position: "fixed", bottom: "1rem", right: "1rem", zIndex: 100 }}>
      <HealthIndicator />
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<PlayerPage />} />
          <Route path="/create" element={<CreatePage />} />
          <Route path="/admin/login" element={<AdminLoginPage />} />
          <Route path="/admin" element={<AdminPage />} />
        </Routes>
        <NavLayout />
        <UserIdentity />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
