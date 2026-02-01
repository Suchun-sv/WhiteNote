"use client";

import { useRef, useState, useEffect } from "react";
import Link from "next/link";
import { Loader2, ChevronsUp, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PaperCard } from "@/components/paper-card";
import { usePapers } from "@/hooks/use-papers";
import { useFeeds } from "@/hooks/use-feeds";
import { useBulkDislike } from "@/hooks/use-favorites";
import { DevDebugPanel } from "@/components/dev-debug-panel";
import { MasonryGrid } from "@/components/masonry-grid";
import { AddFeedDialog } from "@/components/add-feed-dialog";

const VISIBLE_FEEDS_KEY = "whitenote-visible-feeds";

function getStoredVisibleFeedIds(): string[] | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(VISIBLE_FEEDS_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) && parsed.every((x) => typeof x === "string")
      ? parsed
      : null;
  } catch {
    return null;
  }
}

export default function Home() {
  const { data: feeds } = useFeeds();
  const [visibleFeedIds, setVisibleFeedIds] = useState<string[]>(["arxiv"]);
  const [activeFeed, setActiveFeed] = useState<string>("arxiv");
  const [addFeedOpen, setAddFeedOpen] = useState(false);

  // Hydrate visible tabs from localStorage; then keep in sync with feeds
  useEffect(() => {
    const stored = getStoredVisibleFeedIds();
    if (stored != null && stored.length > 0) {
      setVisibleFeedIds(stored);
      setActiveFeed((prev) => (stored.includes(prev) ? prev : stored[0]));
    }
  }, []);
  useEffect(() => {
    if (!feeds?.length) return;
    const validIds = new Set(feeds.map((f) => f.id));
    setVisibleFeedIds((prev) => {
      const next = prev.filter((id) => validIds.has(id));
      if (next.length === 0) return [feeds[0].id];
      return next;
    });
  }, [feeds]);
  useEffect(() => {
    try {
      localStorage.setItem(VISIBLE_FEEDS_KEY, JSON.stringify(visibleFeedIds));
    } catch {
      // ignore
    }
  }, [visibleFeedIds]);

  const visibleFeeds =
    feeds?.filter((f) => visibleFeedIds.includes(f.id)) ?? [];

  const { data, isLoading, isError, error, refetch } = usePapers({
    page: 1,
    size: 21,
    feed: activeFeed,
  });
  const bulkDislike = useBulkDislike();
  const topRef = useRef<HTMLDivElement>(null);

  const papers = data?.data ?? [];
  const total = data?.pagination?.total ?? 0;
  const favoritedCount = papers.filter(
    (p) => p.favorite_folders.length > 0,
  ).length;

  async function handleNextBatch() {
    const toDislike = papers
      .filter((p) => p.favorite_folders.length === 0)
      .map((p) => p.id);

    if (toDislike.length > 0) {
      await bulkDislike.mutateAsync(toDislike);
    } else {
      await refetch();
    }

    topRef.current?.scrollIntoView({ behavior: "smooth" });
  }

  function handleFeedChange(feedId: string) {
    setActiveFeed(feedId);
  }

  function handleAddFeed(feedId: string) {
    if (!visibleFeedIds.includes(feedId)) {
      setVisibleFeedIds((prev) => [...prev, feedId]);
      setActiveFeed(feedId);
    }
    setAddFeedOpen(false);
  }

  return (
    <div className="min-h-screen bg-background">
      <div ref={topRef} />

      {/* Sticky header */}
      <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto max-w-6xl px-4 py-4">
          <h1 className="text-2xl font-bold tracking-tight">WhiteNote</h1>
          <p className="text-sm text-muted-foreground">
            像刷小红书一样刷论文
          </p>
          <nav className="mt-2 flex items-center gap-4 overflow-x-auto">
            {visibleFeeds.map((feed) => (
              <button
                key={feed.id}
                onClick={() => handleFeedChange(feed.id)}
                className={`text-sm font-medium pb-0.5 whitespace-nowrap ${
                  activeFeed === feed.id
                    ? "text-foreground border-b-2 border-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {feed.name}
              </button>
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
              visibleFeedIds={visibleFeedIds}
              onAdd={handleAddFeed}
            />
            <Link
              href="/collections"
              className="text-sm font-medium text-muted-foreground hover:text-foreground pb-0.5 whitespace-nowrap"
            >
              收藏夹
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
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
            暂无论文，等待新论文入库
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
