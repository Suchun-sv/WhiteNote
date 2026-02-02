import { useQuery } from "@tanstack/react-query";
import { fetchFeeds, fetchFeedsFromDb } from "@/lib/api";

export function useFeeds() {
  return useQuery({
    queryKey: ["feeds"],
    queryFn: fetchFeeds,
    staleTime: 5 * 60 * 1000, // feeds config rarely changes
  });
}

/** Feeds that have papers in DB (for home tabs). */
export function useFeedsFromDb() {
  return useQuery({
    queryKey: ["feeds", "from-db"],
    queryFn: fetchFeedsFromDb,
    staleTime: 60 * 1000,
  });
}
