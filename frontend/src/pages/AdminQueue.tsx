import { useState } from "react";
import { useAdminQueue, useDeleteQueueItem, useSkipQueue } from "../api/admin";

export function AdminQueue() {
  const { data, isLoading, error } = useAdminQueue();
  const deleteItem = useDeleteQueueItem();
  const skip = useSkipQueue();
  const [undoItem, setUndoItem] = useState<{ id: number; position: number } | null>(null);

  if (isLoading) return <div className="loading">Loading queue...</div>;
  if (error) return <div className="error">Failed to load queue</div>;
  if (!data) return null;

  const handleSkip = async () => {
    try {
      await skip.mutateAsync();
    } catch {
      // error
    }
  };

  const handleDelete = async (itemId: number, position: number) => {
    setUndoItem({ id: itemId, position });
    await deleteItem.mutateAsync(itemId);
    setTimeout(() => setUndoItem(null), 2000);
  };

  return (
    <div className="admin-queue">
      <h2>Live Queue</h2>
      <div className="queue-actions">
        <button onClick={handleSkip} disabled={skip.isPending}>
          Skip Current
        </button>
      </div>

      {undoItem && (
        <div className="undo-toast">
          Item removed. <button onClick={() => handleDelete(undoItem.id, undoItem.position)}>Undo</button>
        </div>
      )}

      <div className="queue-list">
        {data.queue?.length === 0 && <p>Queue is empty</p>}
        {data.queue?.map((item: { id: number; position: number; track_id: number | null; jingle_id: number | null; state: string }) => (
          <div key={item.id} className="queue-item">
            <span className="queue-position">{item.position}</span>
            <span className="queue-state">{item.state}</span>
            <button
              className="delete-btn"
              onClick={() => handleDelete(item.id, item.position)}
              disabled={deleteItem.isPending}
            >
              Remove
            </button>
          </div>
        ))}
      </div>

      {data.active_playlists && data.active_playlists.length > 0 && (
        <div className="active-playlists">
          <h3>Active Playlists</h3>
          {data.active_playlists.map((p: { id: number; name: string; owner_label: string | null }) => (
            <div key={p.id} className="playlist-card">
              <span>{p.name}</span>
              {p.owner_label && <span className="owner">{p.owner_label}</span>}
            </div>
          ))}
        </div>
      )}

      <div className="insert-jingle">
        <h3>Insert Jingle</h3>
        <p>Jingle insertion available via admin interface</p>
      </div>
    </div>
  );
}
