import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  addFavorite,
  removeFavorite,
  markDislike,
  unmarkDislike,
  type PaperListResponse,
} from "@/lib/api";

export function useToggleFavorite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      paperId,
      folder,
      action,
    }: {
      paperId: string;
      folder: string;
      action: "add" | "remove";
    }): Promise<{ success: boolean }> => {
      if (action === "add") return addFavorite(paperId, folder);
      return removeFavorite(paperId, folder);
    },

    onMutate: async ({ paperId, folder, action }) => {
      await qc.cancelQueries({ queryKey: ["papers"] });

      const previousQueries = qc.getQueriesData<PaperListResponse>({
        queryKey: ["papers"],
      });

      qc.setQueriesData<PaperListResponse>(
        { queryKey: ["papers"] },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            data: old.data.map((p) => {
              if (p.id !== paperId) return p;
              const folders = [...p.favorite_folders];
              if (action === "add" && !folders.includes(folder)) {
                folders.push(folder);
              } else if (action === "remove") {
                const idx = folders.indexOf(folder);
                if (idx !== -1) folders.splice(idx, 1);
              }
              return { ...p, favorite_folders: folders };
            }),
          };
        },
      );

      return { previousQueries };
    },

    onError: (_err, _vars, context) => {
      if (context?.previousQueries) {
        for (const [key, data] of context.previousQueries) {
          qc.setQueryData(key, data);
        }
      }
    },

    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["papers"] });
      qc.invalidateQueries({ queryKey: ["collections"] });
    },
  });
}

export function useToggleDislike() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      paperId,
      action,
    }: {
      paperId: string;
      action: "dislike" | "undislike";
    }) =>
      action === "dislike"
        ? markDislike(paperId)
        : unmarkDislike(paperId),

    onMutate: async ({ paperId, action }) => {
      await qc.cancelQueries({ queryKey: ["papers"] });

      const previousQueries = qc.getQueriesData<PaperListResponse>({
        queryKey: ["papers"],
      });

      // 如果是 dislike，立即从列表中移除（乐观更新）
      if (action === "dislike") {
        qc.setQueriesData<PaperListResponse>(
          { queryKey: ["papers"] },
          (old) => {
            if (!old) return old;
            return {
              ...old,
              data: old.data.filter((p) => p.id !== paperId),
              pagination: {
                ...old.pagination,
                total: Math.max(0, old.pagination.total - 1),
              },
            };
          },
        );
      } else {
        // 如果是 undislike，更新状态
        qc.setQueriesData<PaperListResponse>(
          { queryKey: ["papers"] },
          (old) => {
            if (!old) return old;
            return {
              ...old,
              data: old.data.map((p) =>
                p.id === paperId ? { ...p, is_disliked: false } : p
              ),
            };
          },
        );
      }

      return { previousQueries };
    },

    onError: (_err, _vars, context) => {
      if (context?.previousQueries) {
        for (const [key, data] of context.previousQueries) {
          qc.setQueryData(key, data);
        }
      }
    },

    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["papers"] });
    },
  });
}
