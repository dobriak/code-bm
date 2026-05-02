import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { PlayerAudio } from "./components/PlayerAudio";
import "./App.css";

function App() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await fetch("/api/v1/health");
      if (!res.ok) throw new Error("Backend unavailable");
      return res.json();
    },
  });

  return (
    <div className="app">
      <nav className="main-nav">
        <Link to="/">Player</Link>
        <Link to="/browse">Browse</Link>
        <Link to="/create">Create Playlist</Link>
        <Link to="/admin">Admin</Link>
      </nav>
      <h1>Raidio</h1>
      <div className="status">
        {isLoading ? (
          <span className="loading">Checking backend...</span>
        ) : isError ? (
          <span className="error">Backend unavailable</span>
        ) : (
          <span className="ok">Backend ok ({data?.version})</span>
        )}
      </div>
      <PlayerAudio />
    </div>
  );
}

export default App;