import { useQuery } from "@tanstack/react-query";
import { fetchFeeds } from "@/lib/api";

export function useFeeds() {
  return useQuery({
    queryKey: ["feeds"],
    queryFn: fetchFeeds,
    staleTime: 5 * 60 * 1000, // feeds config rarely changes
  });
}
