import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { PaperCard as PaperCardData } from "@/lib/api";

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

  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base font-semibold leading-snug line-clamp-2">
            {displayTitle}
          </CardTitle>
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
      </CardContent>
    </Card>
  );
}
