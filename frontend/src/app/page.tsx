"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PaperCard } from "@/components/paper-card";
import { usePapers } from "@/hooks/use-papers";

export default function Home() {
  const [page, setPage] = useState(1);
  const { data, isLoading, isError, error } = usePapers({ page, size: 20 });

  const pagination = data?.pagination;
  const papers = data?.data ?? [];

  return (
    <div className="min-h-screen bg-background">
      {/* Sticky header */}
      <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto max-w-6xl px-4 py-4">
          <h1 className="text-2xl font-bold tracking-tight">WhiteNote</h1>
          <p className="text-sm text-muted-foreground">
            像刷小红书一样刷论文
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        {/* Loading */}
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}

        {/* Error */}
        {isError && (
          <div className="rounded-md border border-red-200 bg-red-50 p-4 text-center text-red-600">
            加载失败：{error instanceof Error ? error.message : "未知错误"}
          </div>
        )}

        {/* Empty */}
        {!isLoading && !isError && papers.length === 0 && (
          <div className="py-20 text-center text-muted-foreground">
            暂无论文
          </div>
        )}

        {/* Paper grid */}
        {papers.length > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {papers.map((paper) => (
              <PaperCard key={paper.id} paper={paper} />
            ))}
          </div>
        )}

        {/* Pagination */}
        {pagination && pagination.total_pages > 1 && (
          <div className="mt-8 flex items-center justify-center gap-4">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              上一页
            </Button>
            <span className="text-sm text-muted-foreground">
              第 {pagination.page} / {pagination.total_pages} 页（共{" "}
              {pagination.total} 篇）
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= pagination.total_pages}
              onClick={() => setPage((p) => p + 1)}
            >
              下一页
            </Button>
          </div>
        )}
      </main>
    </div>
  );
}
