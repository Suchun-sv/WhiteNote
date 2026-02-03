"use client";

import { useMemo, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { FeedInfo } from "@/lib/api";

const CRAWLER_SOURCE_HINT =
  "Not listed? Add your own crawler in backend/src/crawler/.";

/** 
 * Extract conference name from feed id (e.g., "cvpr-2025" -> "CVPR", "arxiv" -> "arXiv").
 * This is more reliable than parsing the display name.
 * 
 * Special cases:
 * - NeurIPS: Only first letter capitalized (Neurips)
 * - Others: All uppercase (CVPR, ICCV, ICML, ICLR, VLDB, SIGMOD, etc.)
 */
function getConferenceKey(feed: FeedInfo): string {
  // Remove trailing year suffix like "-2025", "-2024" from id
  const idWithoutYear = feed.id.replace(/-\d{4}$/, "").toLowerCase();
  
  // Special case mappings
  const specialCases: Record<string, string> = {
    "neurips": "Neurips",  // Only first letter capitalized
    "nips": "Neurips",     // Legacy name
  };
  
  if (specialCases[idWithoutYear]) {
    return specialCases[idWithoutYear];
  }
  
  // Default: all uppercase (CVPR, ICCV, ICML, ICLR, VLDB, SIGMOD, ECCV, etc.)
  return idWithoutYear.toUpperCase();
}

/** Group feeds by conference name (e.g. arXiv, ICLR). */
function groupFeedsByConference(feeds: FeedInfo[]): Map<string, FeedInfo[]> {
  const map = new Map<string, FeedInfo[]>();
  for (const f of feeds) {
    const key = getConferenceKey(f);
    const list = map.get(key) ?? [];
    list.push(f);
    map.set(key, list);
  }
  return map;
}

export interface AddFeedDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  feeds: FeedInfo[];
  visibleFeedIds: string[];
  onAdd: (feedId: string) => void;
}

export function AddFeedDialog({
  open,
  onOpenChange,
  feeds,
  visibleFeedIds,
  onAdd,
}: AddFeedDialogProps) {
  const [conference, setConference] = useState<string>("");
  const [year, setYear] = useState<string>("");

  const grouped = useMemo(() => groupFeedsByConference(feeds), [feeds]);
  const conferences = useMemo(
    () => Array.from(grouped.keys()).sort((a, b) => a.localeCompare(b)),
    [grouped],
  );

  const availableFeeds = useMemo(
    () => feeds.filter((f) => !visibleFeedIds.includes(f.id)),
    [feeds, visibleFeedIds],
  );
  const availableByConference = useMemo(
    () => groupFeedsByConference(availableFeeds),
    [availableFeeds],
  );
  const availableConferences = useMemo(
    () => Array.from(availableByConference.keys()).sort((a, b) => a.localeCompare(b)),
    [availableByConference],
  );

  const selectedConference = (conference || availableConferences[0]) ?? "";
  const feedsForConference = availableByConference.get(selectedConference) ?? [];
  // Only show year selector if the crawler supports year filtering (e.g., DBLP)
  const hasYears = feedsForConference.some((f) => f.supports_year_filter);
  const years = useMemo(
    () =>
      [...new Set(feedsForConference.map((f) => f.year).filter((y): y is number => y != null))].sort(
        (a, b) => b - a,
      ),
    [feedsForConference],
  );
  const effectiveYear = year || (years[0] != null ? String(years[0]) : "");

  const selectedFeed = useMemo(() => {
    if (hasYears && effectiveYear) {
      const y = parseInt(effectiveYear, 10);
      return feedsForConference.find((f) => f.year === y);
    }
    return feedsForConference[0] ?? null;
  }, [feedsForConference, hasYears, effectiveYear]);

  const handleAdd = () => {
    if (selectedFeed) {
      onAdd(selectedFeed.id);
      onOpenChange(false);
      setConference("");
      setYear("");
    }
  };

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      setConference("");
      setYear("");
    }
    onOpenChange(next);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add feed</DialogTitle>
          <DialogDescription>
            Choose a conference and year. Only feeds with implemented crawlers are listed.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-2">
          <div className="grid gap-2">
            <label htmlFor="add-feed-conference" className="text-sm font-medium">
              Conference
            </label>
            <select
              id="add-feed-conference"
              value={selectedConference}
              onChange={(e) => {
                setConference(e.target.value);
                setYear("");
              }}
              className={cn(
                "border-input bg-background h-9 w-full rounded-md border px-3 py-1 text-sm shadow-xs",
                "focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] outline-none",
              )}
            >
              {availableConferences.length === 0 ? (
                <option value="">— None available —</option>
              ) : (
                availableConferences.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))
              )}
            </select>
          </div>

          {hasYears && years.length > 0 && (
            <div className="grid gap-2">
              <label htmlFor="add-feed-year" className="text-sm font-medium">
                Year
              </label>
              <select
                id="add-feed-year"
                value={effectiveYear}
                onChange={(e) => setYear(e.target.value)}
                className={cn(
                  "border-input bg-background h-9 w-full rounded-md border px-3 py-1 text-sm shadow-xs",
                  "focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] outline-none",
                )}
              >
                {years.map((y) => (
                  <option key={y} value={String(y)}>
                    {y}
                  </option>
                ))}
              </select>
            </div>
          )}

          <p className="text-muted-foreground text-xs">
            {CRAWLER_SOURCE_HINT}
          </p>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleAdd} disabled={!selectedFeed}>
            Add tab
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
