"use client";

import { useState } from "react";
import { ChevronDown, Check, Plus } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { useCollections } from "@/hooks/use-collections";
import { useToggleFavorite } from "@/hooks/use-favorites";
import { CreateFolderDialog } from "@/components/create-folder-dialog";

interface FolderPickerProps {
  paperId: string;
  currentFolders: string[];
}

export function FolderPicker({ paperId, currentFolders }: FolderPickerProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const { data } = useCollections();
  const toggleFavorite = useToggleFavorite();

  const folders = data?.data ?? [];

  function handleToggle(folderName: string) {
    const isIn = currentFolders.includes(folderName);
    toggleFavorite.mutate({
      paperId,
      folder: folderName,
      action: isIn ? "remove" : "add",
    });
  }

  return (
    <>
      <Popover>
        <PopoverTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            aria-label="选择收藏夹"
          >
            <ChevronDown className="h-3.5 w-3.5" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-48 p-1" align="start">
          {folders.length === 0 && (
            <p className="px-2 py-1.5 text-sm text-muted-foreground">
              暂无收藏夹
            </p>
          )}
          {folders.map((f) => {
            const isIn = currentFolders.includes(f.name);
            return (
              <button
                key={f.name}
                className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent"
                onClick={() => handleToggle(f.name)}
              >
                <Check
                  className={`h-4 w-4 ${isIn ? "opacity-100" : "opacity-0"}`}
                />
                <span className="truncate">{f.name}</span>
              </button>
            );
          })}
          <div className="border-t mt-1 pt-1">
            <button
              className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent"
              onClick={() => setDialogOpen(true)}
            >
              <Plus className="h-4 w-4" />
              <span>新建收藏夹</span>
            </button>
          </div>
        </PopoverContent>
      </Popover>
      <CreateFolderDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </>
  );
}
