"use client";

import { useRef, useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { Loader2, ChevronsUp, Plus, X, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PaperCard } from "@/components/paper-card";
import { usePapers } from "@/hooks/use-papers";
import { useFeeds, useFeedsFromDb } from "@/hooks/use-feeds";
import { useRunFeedNow } from "@/hooks/use-tasks";
import { useBulkDislike } from "@/hooks/use-favorites";
import { DevDebugPanel } from "@/components/dev-debug-panel";
import { MasonryGrid } from "@/components/masonry-grid";
import { AddFeedDialog } from "@/components/add-feed-dialog";

const ACTIVE_FEED_KEY = "whitenote-active-feed";
const VISIBLE_FEEDS_KEY = "whitenote-visible-feeds";

function getStoredActiveFeed(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(ACTIVE_FEED_KEY);
  } catch {
    return null;
  }
}

function getStoredVisibleFeeds(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const stored = localStorage.getItem(VISIBLE_FEEDS_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function setStoredVisibleFeeds(feedIds: string[]) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(VISIBLE_FEEDS_KEY, JSON.stringify(feedIds));
  } catch {
    // ignore
  }
}

export default function Home() {
  const { data: feedsFromDb } = useFeedsFromDb();
  const { data: feeds } = useFeeds();
  const [activeFeed, setActiveFeed] = useState<string>("arxiv");
  const [visibleFeedIds, setVisibleFeedIds] = useState<string[]>([]);
  const [addFeedOpen, setAddFeedOpen] = useState(false);
  const [hasLoadedStorage, setHasLoadedStorage] = useState(false);

  // Load stored preferences after mount to avoid SSR hydration mismatch
  useEffect(() => {
    const storedActive = getStoredActiveFeed();
    const storedVisible = getStoredVisibleFeeds();
    if (storedActive) {
      setActiveFeed(storedActive);
    }
    if (storedVisible.length > 0) {
      setVisibleFeedIds(storedVisible);
    }
    setHasLoadedStorage(true);
  }, []);

  // Initialize visible feeds from DB if not set (only run once when feedsFromDb loads)
  useEffect(() => {
    if (
      hasLoadedStorage &&
      visibleFeedIds.length === 0 &&
      feedsFromDb &&
      feedsFromDb.length > 0
    ) {
      const dbFeedIds = feedsFromDb.map((f) => f.id);
      setVisibleFeedIds(dbFeedIds);
      setStoredVisibleFeeds(dbFeedIds);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [feedsFromDb, hasLoadedStorage]);

  // Persist visible feeds to localStorage
  useEffect(() => {
    if (!hasLoadedStorage) return;
    setStoredVisibleFeeds(visibleFeedIds);
  }, [visibleFeedIds, hasLoadedStorage]);

  // Build tab feeds from visibleFeedIds, using all feeds config for metadata
  const allFeeds = feeds ?? [];
  const tabFeeds = useMemo(() => {
    return visibleFeedIds
      .map((id) => {
        // Prefer config feed for name, fallback to DB feed
        const configFeed = allFeeds.find((f) => f.id === id);
        const dbFeed = feedsFromDb?.find((f) => f.id === id);
        return {
          id,
          name: configFeed?.name ?? dbFeed?.name ?? id,
        };
      })
      .filter((f) => f !== null);
  }, [visibleFeedIds, allFeeds, feedsFromDb]);

  useEffect(() => {
    if (tabFeeds.length === 0) return;
    const valid = new Set(tabFeeds.map((f) => f.id));
    setActiveFeed((prev) => (valid.has(prev) ? prev : tabFeeds[0].id));
  }, [tabFeeds]);

  useEffect(() => {
    try {
      localStorage.setItem(ACTIVE_FEED_KEY, activeFeed);
    } catch {
      // ignore
    }
  }, [activeFeed]);

  const { data, isLoading, isError, error, refetch } = usePapers({
    page: 1,
    size: 21,
    feed: activeFeed,
  });
  const bulkDislike = useBulkDislike();
  const mainRef = useRef<HTMLElement>(null);

  const papers = data?.data ?? [];
  const total = data?.pagination?.total ?? 0;
  const favoritedCount = papers.filter(
    (p) => p.favorite_folders.length > 0,
  ).length;

  async function handleNextBatch() {
    const toDislike = papers
      .filter((p) => p.favorite_folders.length === 0)
      .map((p) => p.id);

    // Scroll so the first card is just below the sticky header.
    mainRef.current?.scrollIntoView({ behavior: "instant" });

    if (toDislike.length > 0) {
      await bulkDislike.mutateAsync(toDislike);
    } else {
      await refetch();
    }
  }

  function handleFeedChange(feedId: string) {
    setActiveFeed(feedId);
  }

  function handleRemoveFeed(feedId: string, e: React.MouseEvent) {
    e.stopPropagation();
    setVisibleFeedIds((prev) => prev.filter((id) => id !== feedId));
    // If removing active feed, switch to another one
    if (activeFeed === feedId) {
      const remaining = visibleFeedIds.filter((id) => id !== feedId);
      if (remaining.length > 0) {
        setActiveFeed(remaining[0]);
      }
    }
  }

  const runFeedNow = useRunFeedNow();
  const [feedError, setFeedError] = useState<string | null>(null);
  
  function handleAddFeed(feedId: string) {
    // Add to visible feeds if not already there
    if (!visibleFeedIds.includes(feedId)) {
      setVisibleFeedIds((prev) => [...prev, feedId]);
    }
    setActiveFeed(feedId);
    setAddFeedOpen(false);
    setFeedError(null);
    
    // Always trigger crawl for the feed
    runFeedNow.mutate(feedId, {
      onError: (error) => {
        const message = error instanceof Error ? error.message : String(error);
        setFeedError(`Failed to fetch papers for ${feedId}: ${message}`);
      },
    });
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Sticky header */}
      <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto max-w-6xl px-4 py-4">
          <h1 className="text-2xl font-bold tracking-tight">WhiteNote</h1>
          <p className="text-sm text-muted-foreground">
            像刷小红书一样刷论文
          </p>
          
          {/* Feed Error Alert */}
          {feedError && (
            <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-md flex items-start gap-2">
              <AlertCircle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm text-red-700">{feedError}</p>
                <p className="text-xs text-red-500 mt-1">
                  如果错误持续，请检查后端服务或稍后重试。
                </p>
              </div>
              <button 
                onClick={() => setFeedError(null)}
                className="text-red-400 hover:text-red-600"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}
          
          {/* Crawl Status Indicator */}
          {runFeedNow.isPending && (
            <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded-md flex items-center gap-2">
              <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
              <span className="text-sm text-blue-700">
                正在抓取论文，请稍候... (首次抓取可能需要几分钟)
              </span>
            </div>
          )}
          
          <nav className="mt-2 flex items-center gap-1 overflow-x-auto min-w-0">
              {tabFeeds.map((feed) => (
                <div
                  key={feed.id}
                  className={`group flex items-center gap-0.5 pb-0.5 whitespace-nowrap shrink-0 cursor-pointer ${
                    activeFeed === feed.id
                      ? "text-foreground border-b-2 border-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                  onClick={() => handleFeedChange(feed.id)}
                >
                  <span className="text-sm font-medium">{feed.name}</span>
                  <button
                    onClick={(e) => handleRemoveFeed(feed.id, e)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 hover:bg-muted rounded"
                    title="Remove tab"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 shrink-0 rounded-full text-muted-foreground hover:text-foreground"
                onClick={() => setAddFeedOpen(true)}
                title="Add feed"
              >
                <Plus className="h-4 w-4" />
              </Button>
              <AddFeedDialog
                open={addFeedOpen}
                onOpenChange={setAddFeedOpen}
                feeds={feeds ?? []}
                visibleFeedIds={tabFeeds.map((f) => f.id)}
                onAdd={handleAddFeed}
              />
          </nav>
        </div>
      </header>

      <main ref={mainRef} className="mx-auto max-w-6xl px-4 py-6 scroll-mt-[1px]">
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}

        {isError && (
          <div className="rounded-md border border-red-200 bg-red-50 p-4 text-left text-red-600">
            <div className="font-semibold mb-2">加载失败</div>
            <div className="text-sm whitespace-pre-line">
              {error instanceof Error ? error.message : "未知错误"}
            </div>
            {error instanceof Error && <DevDebugPanel error={error} />}
          </div>
        )}

        {!isLoading && !isError && papers.length === 0 && (
          <div className="py-20 text-center text-muted-foreground">
            {runFeedNow.isPending ? (
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="h-8 w-8 animate-spin" />
                <span>正在抓取论文...</span>
              </div>
            ) : (
              "暂无论文，等待新论文入库"
            )}
          </div>
        )}

        {papers.length > 0 && (
          <>
            <MasonryGrid>
              {papers.map((paper) => (
                <PaperCard key={paper.id} paper={paper} />
              ))}
            </MasonryGrid>

            <div className="mt-10 mb-8 flex flex-col items-center gap-3">
              <p className="text-sm text-muted-foreground">
                本页 {papers.length} 篇 · 已收藏 {favoritedCount} 篇 · 剩余约{" "}
                {Math.max(0, total - papers.length)} 篇待浏览
              </p>
              <Button
                size="lg"
                className="w-full max-w-xs gap-2"
                onClick={handleNextBatch}
                disabled={bulkDislike.isPending}
              >
                {bulkDislike.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ChevronsUp className="h-4 w-4" />
                )}
                {bulkDislike.isPending ? "处理中…" : "下一批"}
              </Button>
              <p className="text-xs text-muted-foreground text-center max-w-sm">
                未收藏的论文将标记为已浏览，不再出现
              </p>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
