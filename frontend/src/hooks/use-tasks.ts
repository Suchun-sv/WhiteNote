import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchTasksOverview,
  fetchScheduledTasks,
  fetchPendingSummary,
  fetchPendingComic,
  fetchPendingEnrich,
  fetchTaskHistory,
  fetchTaskLogs,
  runFeedNow,
  runDailyArxivNow,
  runEnrichBackfill,
} from "@/lib/api";

export function useTasksOverview() {
  return useQuery({
    queryKey: ["tasks", "overview"],
    queryFn: fetchTasksOverview,
    refetchInterval: 10 * 1000,
  });
}

export function useScheduledTasks() {
  return useQuery({
    queryKey: ["tasks", "scheduled"],
    queryFn: fetchScheduledTasks,
    refetchInterval: 30 * 1000,
  });
}

export function usePendingSummary() {
  return useQuery({
    queryKey: ["tasks", "pending-summary"],
    queryFn: fetchPendingSummary,
    refetchInterval: 5 * 1000,
  });
}

export function usePendingComic() {
  return useQuery({
    queryKey: ["tasks", "pending-comic"],
    queryFn: fetchPendingComic,
    refetchInterval: 5 * 1000,
  });
}

export function usePendingEnrich() {
  return useQuery({
    queryKey: ["tasks", "pending-enrich"],
    queryFn: fetchPendingEnrich,
    refetchInterval: 5 * 1000,
  });
}

export function useTaskHistory(limit?: number) {
  return useQuery({
    queryKey: ["tasks", "history", limit],
    queryFn: () => fetchTaskHistory(limit),
    refetchInterval: 10 * 1000,
  });
}

export function useTaskLogs(source: string, lines?: number) {
  return useQuery({
    queryKey: ["tasks", "logs", source, lines],
    queryFn: () => fetchTaskLogs(source, lines),
    refetchInterval: 5 * 1000,
    enabled: !!source,
  });
}

export function useRunFeedNow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (feedId: string) => runFeedNow(feedId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      qc.invalidateQueries({ queryKey: ["feeds", "from-db"] });
    },
  });
}

export function useRunDailyArxivNow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: runDailyArxivNow,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}

export function useRunEnrichBackfill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: runEnrichBackfill,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}
