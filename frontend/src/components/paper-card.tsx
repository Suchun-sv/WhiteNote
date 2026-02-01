"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Heart, ChevronDown, ChevronUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FolderPicker } from "@/components/folder-picker";
import { MathText } from "@/components/math-text";
import { useToggleFavorite } from "@/hooks/use-favorites";
import type { PaperCard as PaperCardData } from "@/lib/api";

const DEFAULT_FOLDER = "我的收藏";

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

interface PaperCardProps {
  paper: PaperCardData;
}

export function PaperCard({ paper }: PaperCardProps) {
  const displayTitle = paper.ai_title || paper.title;
  const displayAbstract = paper.ai_abstract || paper.abstract;
  const isFavorited = paper.favorite_folders.length > 0;
  const toggleFavorite = useToggleFavorite();
  const [isExpanded, setIsExpanded] = useState(false);
  const [isTruncated, setIsTruncated] = useState(false);
  const abstractRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = abstractRef.current;
    if (el) {
      setIsTruncated(el.scrollHeight > el.clientHeight + 1);
    }
  }, [displayAbstract]);

  function handleHeartClick(e: React.MouseEvent) {
    e.stopPropagation();
    toggleFavorite.mutate({
      paperId: paper.id,
      folder: DEFAULT_FOLDER,
      action: isFavorited ? "remove" : "add",
    });
  }

  return (
    <Card
      className={`transition-all duration-200 hover:shadow-md ${
        isFavorited
          ? "ring-1 ring-red-200 bg-red-50/30 dark:ring-red-900/40 dark:bg-red-950/10"
          : ""
      }`}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <Link
            href={`/paper/${paper.id}`}
            className="flex-1 min-w-0 group"
          >
            <CardTitle className="text-base font-semibold leading-snug line-clamp-2 group-hover:text-primary group-hover:underline transition-colors cursor-pointer">
              {displayTitle}
            </CardTitle>
          </Link>
          <div className="flex shrink-0 items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={handleHeartClick}
              aria-label={isFavorited ? "取消收藏" : "收藏"}
            >
              <Heart
                className={`h-4 w-4 ${
                  isFavorited
                    ? "fill-red-500 text-red-500"
                    : "text-muted-foreground"
                }`}
              />
            </Button>
            <FolderPicker
              paperId={paper.id}
              currentFolders={paper.favorite_folders}
            />
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1 pt-1">
          {paper.feed && (
            <Badge variant="outline" className="text-[10px] font-normal text-muted-foreground">
              {paper.feed}
            </Badge>
          )}
          {paper.keywords.map((kw) => (
            <Badge key={kw} variant="secondary" className="text-[10px]">
              {kw}
            </Badge>
          ))}
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        <div>
          <div
            ref={abstractRef}
            className={`text-sm text-muted-foreground ${
              isExpanded ? "" : "line-clamp-2"
            } ${isTruncated || isExpanded ? "cursor-pointer" : ""}`}
            onClick={isTruncated || isExpanded ? () => setIsExpanded(!isExpanded) : undefined}
          >
            <MathText text={displayAbstract} />
          </div>
          {(isTruncated || isExpanded) && (
            <button
              className="text-xs text-primary/70 hover:text-primary flex items-center gap-0.5 mt-1 active:opacity-70"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? (
                <>收起 <ChevronUp className="h-3 w-3" /></>
              ) : (
                <>展开摘要 <ChevronDown className="h-3 w-3" /></>
              )}
            </button>
          )}
        </div>
        <div className="text-xs text-muted-foreground">
          {formatDate(paper.arxiv_published)}
        </div>
      </CardContent>
    </Card>
  );
}
