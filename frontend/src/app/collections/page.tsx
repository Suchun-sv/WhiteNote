"use client";

import { useState } from "react";
import Link from "next/link";
import { Loader2, FolderOpen, MoreVertical, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  useCollections,
  useCreateCollection,
  useRenameCollection,
  useDeleteCollection,
} from "@/hooks/use-collections";

export default function CollectionsPage() {
  const { data, isLoading, isError, error } = useCollections();
  const folders = data?.data ?? [];

  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState("");
  const createMutation = useCreateCollection();

  const [renameOpen, setRenameOpen] = useState(false);
  const [renameTarget, setRenameTarget] = useState("");
  const [renameName, setRenameName] = useState("");
  const renameMutation = useRenameCollection();

  const deleteMutation = useDeleteCollection();

  function handleCreate() {
    const trimmed = createName.trim();
    if (!trimmed) return;
    createMutation.mutate(trimmed, {
      onSuccess: () => {
        setCreateName("");
        setCreateOpen(false);
      },
    });
  }

  function openRename(folderName: string) {
    setRenameTarget(folderName);
    setRenameName(folderName);
    setRenameOpen(true);
  }

  function handleRename() {
    const trimmed = renameName.trim();
    if (!trimmed || trimmed === renameTarget) return;
    renameMutation.mutate(
      { oldName: renameTarget, newName: trimmed },
      {
        onSuccess: () => {
          setRenameOpen(false);
        },
      },
    );
  }

  function handleDelete(folderName: string) {
    deleteMutation.mutate(folderName);
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto max-w-6xl px-4 py-4">
          <h1 className="text-2xl font-bold tracking-tight">WhiteNote</h1>
          <p className="text-sm text-muted-foreground">
            像刷小红书一样刷论文
          </p>
          <nav className="mt-2 flex gap-4">
            <Link
              href="/"
              className="text-sm font-medium text-muted-foreground hover:text-foreground pb-0.5"
            >
              论文
            </Link>
            <Link
              href="/collections"
              className="text-sm font-medium text-foreground border-b-2 border-foreground pb-0.5"
            >
              收藏夹
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-lg font-semibold">我的收藏夹</h2>
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="mr-1 h-4 w-4" />
            新建收藏夹
          </Button>
        </div>

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

        {!isLoading && !isError && folders.length === 0 && (
          <div className="py-20 text-center text-muted-foreground">
            暂无收藏夹，点击上方按钮创建
          </div>
        )}

        {folders.length > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {folders.map((folder) => (
              <Card
                key={folder.name}
                className="transition-shadow hover:shadow-md"
              >
                <CardContent className="flex items-center gap-3 p-4">
                  <Link
                    href={`/collections/${encodeURIComponent(folder.name)}`}
                    className="flex flex-1 items-center gap-3 min-w-0"
                  >
                    <FolderOpen className="h-8 w-8 shrink-0 text-muted-foreground" />
                    <div className="min-w-0">
                      <p className="font-medium truncate">{folder.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {folder.count} 篇论文
                      </p>
                    </div>
                  </Link>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => openRename(folder.name)}>
                        重命名
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className="text-red-600"
                        onClick={() => handleDelete(folder.name)}
                      >
                        删除
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>

      {/* Create dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建收藏夹</DialogTitle>
            <DialogDescription>输入收藏夹名称</DialogDescription>
          </DialogHeader>
          <Input
            placeholder="收藏夹名称"
            value={createName}
            onChange={(e) => setCreateName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleCreate();
            }}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              取消
            </Button>
            <Button
              onClick={handleCreate}
              disabled={!createName.trim() || createMutation.isPending}
            >
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Rename dialog */}
      <Dialog open={renameOpen} onOpenChange={setRenameOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>重命名收藏夹</DialogTitle>
            <DialogDescription>输入新的收藏夹名称</DialogDescription>
          </DialogHeader>
          <Input
            placeholder="新名称"
            value={renameName}
            onChange={(e) => setRenameName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleRename();
            }}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setRenameOpen(false)}>
              取消
            </Button>
            <Button
              onClick={handleRename}
              disabled={
                !renameName.trim() ||
                renameName.trim() === renameTarget ||
                renameMutation.isPending
              }
            >
              确定
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
