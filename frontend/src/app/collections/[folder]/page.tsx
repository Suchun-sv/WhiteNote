"use client";

import { useState } from "react";
import { use } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PaperCard } from "@/components/paper-card";
import { usePapers } from "@/hooks/use-papers";

interface FolderPageProps {
  params: Promise<{ folder: string }>;
}

export default function FolderPage({ params }: FolderPageProps) {
  const { folder } = use(params);
  const folderName = decodeURIComponent(folder);
  const [page, setPage] = useState(1);
  const { data, isLoading, isError, error } = usePapers({
    page,
    size: 20,
    folder: folderName,
  });

  const pagination = data?.pagination;
  const papers = data?.data ?? [];

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto max-w-6xl px-4 py-4">
          <div className="flex items-center gap-3">
            <Link href="/collections">
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <div>
              <h1 className="text-xl font-bold tracking-tight">
                {folderName}
              </h1>
              <p className="text-sm text-muted-foreground">
                {pagination ? `${pagination.total} 篇论文` : ""}
              </p>
            </div>
          </div>
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
            {process.env.NODE_ENV === "development" && error instanceof Error && (
              <details className="mt-2 text-xs">
                <summary className="cursor-pointer text-red-500 hover:text-red-700">
                  查看调试信息
                </summary>
                <pre className="mt-2 p-2 bg-red-100 rounded overflow-auto">
                  {error.stack || error.message}
                </pre>
              </details>
            )}
          </div>
        )}

        {!isLoading && !isError && papers.length === 0 && (
          <div className="py-20 text-center text-muted-foreground">
            该收藏夹暂无论文
          </div>
        )}

        {papers.length > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {papers.map((paper) => (
              <PaperCard key={paper.id} paper={paper} />
            ))}
          </div>
        )}

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
