import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { fetchPapers, type FetchPapersParams } from "@/lib/api";

export function usePapers(params: FetchPapersParams) {
  return useQuery({
    queryKey: ["papers", params],
    queryFn: () => fetchPapers(params),
    placeholderData: keepPreviousData,
  });
}
