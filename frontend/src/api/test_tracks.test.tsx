import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi } from "vitest";
import { useTracks, useArtists, useGenres } from "./tracks";

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

interface MockResponse<T> {
  ok: boolean;
  json: () => Promise<T>;
}

describe("tracks API hooks", () => {
  it("useTracks returns data shape", async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ tracks: [], total: 0, next_cursor: null }),
      }) as MockResponse<{ tracks: unknown[]; total: number; next_cursor: string | null }>,
    );

    const { result } = renderHook(() => useTracks({}), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveProperty("tracks");
    expect(result.current.data).toHaveProperty("total");
  });

  it("useArtists returns artists array", async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ artists: [{ name: "Beatles", track_count: 10 }] }),
      }) as MockResponse<{ artists: Array<{ name: string; track_count: number }> }>,
    );

    const { result } = renderHook(() => useArtists(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.artists).toHaveLength(1);
    expect(result.current.data?.artists[0].name).toBe("Beatles");
  });

  it("useGenres returns genres array", async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ genres: [{ name: "Rock", track_count: 5 }] }),
      }) as MockResponse<{ genres: Array<{ name: string; track_count: number }> }>,
    );

    const { result } = renderHook(() => useGenres(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.genres).toHaveLength(1);
  });
});