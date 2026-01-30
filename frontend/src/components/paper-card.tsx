"use client";

import Link from "next/link";
import { Heart, ExternalLink, ThumbsDown } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FolderPicker } from "@/components/folder-picker";
import { useToggleFavorite, useToggleDislike } from "@/hooks/use-favorites";
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

function formatAuthors(authors: string[]): string {
  if (authors.length <= 3) return authors.join(", ");
  return `${authors.slice(0, 3).join(", ")} +${authors.length - 3} more`;
}

interface PaperCardProps {
  paper: PaperCardData;
}

export function PaperCard({ paper }: PaperCardProps) {
  const displayTitle = paper.ai_title || paper.title;
  const displayAbstract = paper.ai_abstract || paper.abstract;
  const isFavorited = paper.favorite_folders.length > 0;
  const isDisliked = paper.is_disliked || false;
  const toggleFavorite = useToggleFavorite();
  const toggleDislike = useToggleDislike();

  function handleHeartClick(e: React.MouseEvent) {
    e.stopPropagation();
    toggleFavorite.mutate({
      paperId: paper.id,
      folder: DEFAULT_FOLDER,
      action: isFavorited ? "remove" : "add",
    });
  }

  function handleDislikeClick(e: React.MouseEvent) {
    e.stopPropagation();
    toggleDislike.mutate({
      paperId: paper.id,
      action: isDisliked ? "undislike" : "dislike",
    });
  }

  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <Link
            href={`/paper/${paper.id}`}
            className="flex-1 min-w-0 group"
          >
            <CardTitle className="text-base font-semibold leading-snug line-clamp-2 group-hover:text-primary transition-colors cursor-pointer">
              {displayTitle}
            </CardTitle>
          </Link>
          <div className="flex shrink-0 items-center gap-1">
            <Link
              href={`/paper/${paper.id}`}
              className="text-muted-foreground hover:text-foreground transition-colors"
              aria-label="查看详情"
            >
              <ExternalLink className="h-4 w-4" />
            </Link>
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
        <p className="text-xs text-muted-foreground">
          {formatAuthors(paper.authors)}
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground line-clamp-3">
          {displayAbstract}
        </p>
        <div className="flex items-center justify-between gap-2">
          <div className="flex flex-wrap gap-1">
            {paper.arxiv_primary_category && (
              <Badge variant="secondary">{paper.arxiv_primary_category}</Badge>
            )}
          </div>
          <span className="text-xs text-muted-foreground whitespace-nowrap">
            {formatDate(paper.arxiv_published)}
          </span>
        </div>
        {/* 不喜欢按钮 - 设计得大一点好按 */}
        <Button
          variant={isDisliked ? "destructive" : "outline"}
          size="lg"
          className="w-full mt-3 h-12 text-base font-medium"
          onClick={handleDislikeClick}
          disabled={toggleDislike.isPending}
        >
          <ThumbsDown className="h-5 w-5 mr-2" />
          {isDisliked ? "已标记为不感兴趣" : "不感兴趣"}
        </Button>
      </CardContent>
    </Card>
  );
}
