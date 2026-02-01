"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Loader2, FolderOpen, BookOpen, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useCollections } from "@/hooks/use-collections";
import { cn } from "@/lib/utils";

interface AppSidebarProps {
  onClose?: () => void;
}

export function AppSidebar({ onClose }: AppSidebarProps) {
  const pathname = usePathname();
  const { data, isLoading } = useCollections();
  const folders = data?.data ?? [];

  const isHome = pathname === "/";
  const isCollectionsRoot = pathname === "/collections";
  const isInFolder = pathname.startsWith("/collections/") && pathname !== "/collections";
  const currentFolder = isInFolder
    ? decodeURIComponent(pathname.replace("/collections/", ""))
    : null;

  return (
    <aside className="flex h-full w-full flex-col border-r bg-background pt-[env(safe-area-inset-top)]">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <Link href="/" className="text-lg font-bold tracking-tight text-foreground hover:opacity-80" onClick={onClose}>
          WhiteNote
        </Link>
        {onClose && (
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0 rounded-md"
            onClick={onClose}
            aria-label="Close sidebar"
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-1 overflow-y-auto p-3">
        <Link
          href="/"
          className={cn(
            "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
            isHome
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:bg-muted hover:text-foreground",
          )}
        >
          <BookOpen className="h-4 w-4 shrink-0" />
          论文
        </Link>

        <div className="mt-2">
          <Link
            href="/collections"
            className={cn(
              "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              isCollectionsRoot && !isInFolder
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            <FolderOpen className="h-4 w-4 shrink-0" />
            收藏夹
          </Link>

          {isLoading ? (
            <div className="flex items-center gap-2 px-3 py-2 text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              <span className="text-xs">加载中…</span>
            </div>
          ) : (
            <ul className="mt-0.5 space-y-0.5 pl-6">
              {folders.map((f) => (
                <li key={f.name}>
                  <Link
                    href={`/collections/${encodeURIComponent(f.name)}`}
                    className={cn(
                      "block truncate rounded-md px-2 py-1.5 text-xs transition-colors",
                      currentFolder === f.name
                        ? "bg-primary/10 font-medium text-primary"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground",
                    )}
                    title={`${f.name} · ${f.count} 篇`}
                  >
                    {f.name}
                    <span className="ml-1 text-muted-foreground/80">
                      {f.count}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </aside>
  );
}
