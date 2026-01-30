"use client";

import React, { use, useState, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { fetchPaperById } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { ChatPanel } from "@/components/chat-panel";

interface PaperPageProps {
  params: Promise<{ id: string }>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function PaperPage({ params }: PaperPageProps) {
  const { id } = use(params);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>("comic");

  const { data: paper, isLoading, isError, error } = useQuery({
    queryKey: ["paper", id],
    queryFn: () => fetchPaperById(id),
  });

  // 检查是否有漫画
  const hasComic = paper?.comic_job_status === "completed";
  const comicUrl = hasComic ? `${API_BASE}/api/papers/${id}/comic` : null;
  const pdfUrl = paper?.pdf_url;

  // 根据是否有漫画设置默认tab
  useEffect(() => {
    if (hasComic) {
      setActiveTab("comic");
    } else if (pdfUrl) {
      setActiveTab("pdf");
    }
  }, [hasComic, pdfUrl]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-background">
        <header className="sticky top-0 z-10 border-b bg-background/95">
          <div className="mx-auto max-w-7xl px-4 py-4">
            <Link href="/">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6">
          <div className="rounded-md border border-red-200 bg-red-50 p-4 text-left text-red-600">
            <div className="font-semibold mb-2">加载失败</div>
            <div className="text-sm whitespace-pre-line">
              {error instanceof Error ? error.message : "未知错误"}
            </div>
          </div>
        </main>
      </div>
    );
  }

  if (!paper) {
    return (
      <div className="min-h-screen bg-background">
        <header className="sticky top-0 z-10 border-b bg-background/95">
          <div className="mx-auto max-w-7xl px-4 py-4">
            <Link href="/">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6">
          <div className="text-center py-20 text-muted-foreground">
            论文不存在
          </div>
        </main>
      </div>
    );
  }

  const displayTitle = paper.ai_title || paper.title;
  const displayAbstract = paper.ai_abstract || paper.abstract;

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto max-w-7xl px-4 py-4">
          <div className="flex items-center gap-3">
            <Link href="/">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <div className="flex-1 min-w-0">
              <h1 className="text-xl font-bold tracking-tight truncate">
                {displayTitle}
              </h1>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6">
        {/* 论文基本信息 */}
        <div className="mb-6 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-muted-foreground">
              作者: {paper.authors.join(", ")}
            </span>
            {paper.arxiv_published && (
              <span className="text-sm text-muted-foreground">
                · {new Date(paper.arxiv_published).toLocaleDateString("zh-CN")}
              </span>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {paper.arxiv_primary_category && (
              <Badge variant="secondary">
                {paper.arxiv_primary_category}
              </Badge>
            )}
            {paper.arxiv_categories?.map((cat) => (
              <Badge key={cat} variant="outline">
                {cat}
              </Badge>
            ))}
          </div>
        </div>

        {/* 左右两栏布局 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 左侧：AI摘要、AI Summary、AI对话 */}
          <div className="space-y-6">
            {/* AI摘要 */}
            <div className="space-y-2">
              <h2 className="text-xl font-semibold">AI 摘要</h2>
              <div className="rounded-lg border bg-muted/50 p-4">
                <p className="text-muted-foreground whitespace-pre-wrap leading-relaxed">
                  {displayAbstract || "暂无摘要"}
                </p>
              </div>
            </div>

            {/* AI 总结（如果有） */}
            {paper.ai_summary && (
              <div className="space-y-2">
                <h2 className="text-xl font-semibold">AI 总结</h2>
                <div className="rounded-lg border bg-muted/50 p-4">
                  <p className="text-muted-foreground whitespace-pre-wrap leading-relaxed">
                    {paper.ai_summary}
                  </p>
                </div>
              </div>
            )}

            {/* AI 对话 */}
            <div className="space-y-2">
              <h2 className="text-xl font-semibold">AI 对话</h2>
              <ChatPanel
                paperId={id}
                sessionId={sessionId}
                onSessionChange={setSessionId}
              />
            </div>
          </div>

          {/* 右侧：PDF/漫画 Tab */}
          <div className="space-y-2">
            <h2 className="text-xl font-semibold">内容查看</h2>
            {hasComic || pdfUrl ? (
              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className={`grid w-full ${hasComic && pdfUrl ? 'grid-cols-2' : 'grid-cols-1'}`}>
                  {hasComic && (
                    <TabsTrigger value="comic">🎨 漫画</TabsTrigger>
                  )}
                  {pdfUrl && (
                    <TabsTrigger value="pdf">📄 PDF</TabsTrigger>
                  )}
                </TabsList>

                {hasComic && (
                  <TabsContent value="comic" className="mt-4">
                    <div className="rounded-lg border bg-muted/50 p-4">
                      {comicUrl ? (
                        <img
                          src={comicUrl}
                          alt="论文漫画解读"
                          className="w-full h-auto rounded"
                          onError={(e) => {
                            console.error("Failed to load comic:", comicUrl);
                            const target = e.target as HTMLImageElement;
                            target.style.display = "none";
                            const errorDiv = document.createElement("div");
                            errorDiv.className = "text-center text-red-600 py-8";
                            errorDiv.textContent = `漫画加载失败。请检查：\n1. 漫画文件是否存在\n2. 后端服务是否正常运行\n3. API URL: ${comicUrl}`;
                            target.parentElement?.appendChild(errorDiv);
                          }}
                          onLoad={() => {
                            console.log("Comic loaded successfully:", comicUrl);
                          }}
                        />
                      ) : (
                        <div className="text-center text-muted-foreground py-8">
                          漫画加载中...
                        </div>
                      )}
                    </div>
                  </TabsContent>
                )}

                {pdfUrl && (
                  <TabsContent value="pdf" className="mt-4">
                    <div className="rounded-lg border bg-muted/50 p-4 h-[600px]">
                      <iframe
                        src={pdfUrl}
                        className="w-full h-full rounded"
                        title="PDF Viewer"
                      />
                    </div>
                  </TabsContent>
                )}
              </Tabs>
            ) : (
              <div className="rounded-lg border bg-muted/50 p-8 text-center text-muted-foreground">
                暂无可用内容（PDF 或漫画）
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
