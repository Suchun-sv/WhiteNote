"use client";

import React, { use, useState, useEffect } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Loader2,
  Sparkles,
  FileText,
  MessageCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { fetchPaperById } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { ChatPanel } from "@/components/chat-panel";
import { CollapsibleSection } from "@/components/collapsible-section";

interface PaperPageProps {
  params: Promise<{ id: string }>;
}

import { getApiBase } from "@/lib/api-config";

export default function PaperPage({ params }: PaperPageProps) {
  const { id } = use(params);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>("comic");
  const [apiBase, setApiBase] = useState<string>("http://localhost:8000");

  // 在客户端获取 API_BASE，避免 hydration 错误
  useEffect(() => {
    setApiBase(getApiBase());
  }, []);

  const {
    data: paper,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["paper", id],
    queryFn: () => fetchPaperById(id),
  });

  const hasComic = paper?.comic_job_status === "completed";
  const comicUrl = hasComic ? `${apiBase}/api/papers/${id}/comic` : null;
  const pdfUrl = paper?.pdf_url;
  
  // 构建 arXiv HTML 页面 URL
  const getArxivHtmlUrl = (): string | null => {
    if (!paper?.arxiv_entry_id) return null;
    // arxiv_entry_id 格式可能是:
    // - http://arxiv.org/abs/2301.12345v1
    // - https://arxiv.org/abs/2301.12345v1
    // - arxiv.org/abs/2301.12345v1
    // 提取 ID 部分（去掉版本号）
    const match = paper.arxiv_entry_id.match(/arxiv\.org\/abs\/([\d.]+)/);
    if (match) {
      const arxivId = match[1];
      // 使用 HTML 版本（更适合移动端阅读，支持响应式布局）
      return `https://arxiv.org/html/${arxivId}`;
    }
    // 如果 entry_id 格式不匹配，尝试使用 paper id（通常是规范化后的 arXiv ID）
    // paper id 格式通常是: 2301.12345（没有版本号）
    if (paper.id && /^\d{4}\.\d{4,5}$/.test(paper.id)) {
      return `https://arxiv.org/html/${paper.id}`;
    }
    return null;
  };
  
  const arxivHtmlUrl = getArxivHtmlUrl();
  const hasArxivHtml = !!arxivHtmlUrl;

  useEffect(() => {
    // 优先显示漫画，然后是 arXiv HTML（移动端友好），最后是 PDF
    if (hasComic) {
      setActiveTab("comic");
    } else if (hasArxivHtml) {
      setActiveTab("arxiv");
    } else if (pdfUrl) {
      setActiveTab("pdf");
    }
  }, [hasComic, hasArxivHtml, pdfUrl]);

  // --- Loading ---
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // --- Error / Not found ---
  if (isError || !paper) {
    return (
      <div className="min-h-screen bg-background">
        <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur">
          <div className="mx-auto max-w-[1400px] px-6 py-3">
            <Link href="/">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </header>
        <main className="mx-auto max-w-[1400px] px-6 py-8">
          {isError ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-600">
              <div className="font-semibold mb-1">加载失败</div>
              <div className="text-sm">
                {error instanceof Error ? error.message : "未知错误"}
              </div>
            </div>
          ) : (
            <div className="text-center py-20 text-muted-foreground">
              论文不存在
            </div>
          )}
        </main>
      </div>
    );
  }

  const displayTitle = paper.ai_title || paper.title;
  const displayAbstract = paper.ai_abstract || paper.abstract;

  return (
    <div className="min-h-screen bg-background">
      {/* Header: title + metadata */}
      <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto max-w-[1400px] px-6 py-3">
          <div className="flex items-start gap-3">
            <Link href="/" className="mt-0.5 shrink-0">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <div className="flex-1 min-w-0">
              <h1 className="text-base font-bold leading-snug line-clamp-2">
                {displayTitle}
              </h1>
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1">
                <span className="text-xs text-muted-foreground truncate max-w-[360px]">
                  {paper.authors.slice(0, 3).join(", ")}
                  {paper.authors.length > 3 &&
                    ` +${paper.authors.length - 3}`}
                </span>
                {paper.arxiv_published && (
                  <>
                    <span className="text-xs text-muted-foreground">·</span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(paper.arxiv_published).toLocaleDateString(
                        "zh-CN"
                      )}
                    </span>
                  </>
                )}
                {paper.arxiv_primary_category && (
                  <>
                    <span className="text-xs text-muted-foreground">·</span>
                    <Badge
                      variant="secondary"
                      className="text-[10px] px-1.5 py-0 leading-4"
                    >
                      {paper.arxiv_primary_category}
                    </Badge>
                  </>
                )}
                {paper.arxiv_categories
                  ?.filter((c) => c !== paper.arxiv_primary_category)
                  .slice(0, 3)
                  .map((cat) => (
                    <Badge
                      key={cat}
                      variant="outline"
                      className="text-[10px] px-1.5 py-0 leading-4"
                    >
                      {cat}
                    </Badge>
                  ))}
                {paper.affiliations && paper.affiliations.length > 0 && (
                  <>
                    <span className="text-xs text-muted-foreground">·</span>
                    {paper.affiliations.map((aff) => (
                      <Badge
                        key={aff}
                        variant="outline"
                        className="text-[10px] px-1.5 py-0 leading-4"
                      >
                        {aff}
                      </Badge>
                    ))}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main: two-column layout */}
      <main className="mx-auto max-w-[1400px] px-6 py-5">
        <div className="flex flex-col lg:flex-row gap-5">
          {/* ---- Left column: PDF / Comic / ArXiv HTML viewer (sticky) ---- */}
          <div className="flex-1 min-w-0">
            <div className="lg:sticky lg:top-[5.5rem]">
              {hasComic || pdfUrl || hasArxivHtml ? (
                <div className="rounded-lg border bg-card shadow-sm overflow-hidden">
                  <Tabs value={activeTab} onValueChange={setActiveTab}>
                    <div className="border-b px-4 pt-3 pb-0">
                      <TabsList
                        className={`grid w-full ${
                          [hasComic, hasArxivHtml, pdfUrl].filter(Boolean).length === 3
                            ? "grid-cols-3"
                            : [hasComic, hasArxivHtml, pdfUrl].filter(Boolean).length === 2
                            ? "grid-cols-2"
                            : "grid-cols-1"
                        } max-w-[360px]`}
                      >
                        {hasComic && (
                          <TabsTrigger value="comic" className="text-xs sm:text-sm">
                            漫画
                          </TabsTrigger>
                        )}
                        {hasArxivHtml && (
                          <TabsTrigger value="arxiv" className="text-xs sm:text-sm">
                            HTML
                          </TabsTrigger>
                        )}
                        {pdfUrl && (
                          <TabsTrigger value="pdf" className="text-xs sm:text-sm">
                            PDF
                          </TabsTrigger>
                        )}
                      </TabsList>
                    </div>

                    {hasComic && (
                      <TabsContent value="comic" className="mt-0">
                        <div className="p-4">
                          {comicUrl ? (
                            <img
                              src={comicUrl}
                              alt="论文漫画解读"
                              className="w-full h-auto rounded"
                              onError={(e) => {
                                const target = e.target as HTMLImageElement;
                                target.style.display = "none";
                                const errorDiv = document.createElement("div");
                                errorDiv.className =
                                  "text-center text-red-500 py-8 text-sm";
                                errorDiv.textContent = "漫画加载失败";
                                target.parentElement?.appendChild(errorDiv);
                              }}
                            />
                          ) : (
                            <div className="text-center text-muted-foreground py-8 text-sm">
                              漫画加载中...
                            </div>
                          )}
                        </div>
                      </TabsContent>
                    )}

                    {hasArxivHtml && (
                      <TabsContent value="arxiv" className="mt-0 p-0">
                        <div className="relative w-full" style={{ height: "calc(100vh - 10rem)", minHeight: "600px" }}>
                          <iframe
                            src={arxivHtmlUrl || undefined}
                            className="w-full h-full border-0"
                            title="arXiv HTML Viewer"
                            allow="fullscreen"
                          />
                          {/* 移动端优化：添加外部链接按钮 */}
                          <div className="absolute top-2 right-2 z-10">
                            <a
                              href={arxivHtmlUrl || undefined}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-background/90 backdrop-blur-sm border rounded-md hover:bg-background transition-colors"
                            >
                              在新窗口打开
                            </a>
                          </div>
                        </div>
                      </TabsContent>
                    )}

                    {pdfUrl && (
                      <TabsContent value="pdf" className="mt-0 p-0">
                        <div className="relative w-full" style={{ height: "calc(100vh - 10rem)", minHeight: "600px" }}>
                          <iframe
                            src={pdfUrl}
                            className="w-full h-full border-0"
                            title="PDF Viewer"
                            allow="fullscreen"
                          />
                          {/* 移动端优化：添加外部链接和下载按钮 */}
                          <div className="absolute top-2 right-2 z-10 flex gap-2">
                            <a
                              href={pdfUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-background/90 backdrop-blur-sm border rounded-md hover:bg-background transition-colors"
                            >
                              在新窗口打开
                            </a>
                            <a
                              href={pdfUrl}
                              download
                              className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-background/90 backdrop-blur-sm border rounded-md hover:bg-background transition-colors"
                            >
                              下载
                            </a>
                          </div>
                        </div>
                      </TabsContent>
                    )}
                  </Tabs>
                </div>
              ) : (
                <div className="rounded-lg border bg-card shadow-sm p-8 text-center text-muted-foreground text-sm">
                  暂无可用内容（PDF、HTML 或漫画）
                </div>
              )}
            </div>
          </div>

          {/* ---- Right column: AI sections ---- */}
          <div className="w-full lg:w-[440px] shrink-0 space-y-3">
            {/* AI 摘要 — default open */}
            <CollapsibleSection
              title="AI 摘要"
              icon={<Sparkles className="h-4 w-4 text-amber-500" />}
              defaultOpen
            >
              <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">
                {displayAbstract || "暂无摘要"}
              </p>
            </CollapsibleSection>

            {/* AI 总结 — default collapsed */}
            {paper.ai_summary && (
              <CollapsibleSection
                title="AI 总结"
                icon={<FileText className="h-4 w-4 text-blue-500" />}
              >
                <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">
                  {paper.ai_summary}
                </p>
              </CollapsibleSection>
            )}

            {/* AI 对话 — default collapsed */}
            <CollapsibleSection
              title="AI 对话"
              icon={<MessageCircle className="h-4 w-4 text-green-500" />}
            >
              <ChatPanel
                paperId={id}
                sessionId={sessionId}
                onSessionChange={setSessionId}
              />
            </CollapsibleSection>
          </div>
        </div>
      </main>
    </div>
  );
}
