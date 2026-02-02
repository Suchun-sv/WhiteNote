"use client";

import { useState } from "react";
import {
  Loader2,
  Play,
  Clock,
  ListTodo,
  History,
  Terminal,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  useTasksOverview,
  useScheduledTasks,
  usePendingSummary,
  usePendingComic,
  usePendingEnrich,
  useTaskHistory,
  useTaskLogs,
  useRunFeedNow,
  useRunDailyArxivNow,
  useRunEnrichBackfill,
} from "@/hooks/use-tasks";
import { useFeeds } from "@/hooks/use-feeds";
import { cn } from "@/lib/utils";

function formatDt(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("zh-CN", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

export default function TasksPage() {
  const [logSource, setLogSource] = useState("daily_arxiv");
  const [logLines, setLogLines] = useState(150);
  const [selectedFeedId, setSelectedFeedId] = useState("");

  const { data: overview, refetch: refetchOverview } = useTasksOverview();
  const { data: scheduled, isLoading: loadingScheduled } = useScheduledTasks();
  const { data: pendingSummary } = usePendingSummary();
  const { data: pendingComic } = usePendingComic();
  const { data: pendingEnrich } = usePendingEnrich();
  const { data: history } = useTaskHistory(50);
  const { data: logs, isLoading: loadingLogs } = useTaskLogs(logSource, logLines);

  const { data: feeds } = useFeeds();
  const runFeed = useRunFeedNow();
  const runArxiv = useRunDailyArxivNow();
  const runEnrichBackfill = useRunEnrichBackfill();

  const pendingTotal =
    (overview?.pending_summary_count ?? 0) +
    (overview?.pending_comic_count ?? 0) +
    (overview?.pending_enrich_count ?? 0);

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto max-w-5xl px-4 py-4">
          <h1 className="text-2xl font-bold tracking-tight">任务</h1>
          <p className="text-sm text-muted-foreground">
            定时任务、一次性任务、队列与日志
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-4 text-sm">
            <span className="text-muted-foreground">
              定时: {overview?.scheduled?.length ?? 0} · 待处理: {pendingTotal}
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 gap-1"
              onClick={() => refetchOverview()}
            >
              <RefreshCw className="h-3.5 w-3.5" />
              刷新
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-6">
        <Tabs defaultValue="scheduled" className="w-full">
          <TabsList className="mb-4 flex flex-wrap gap-1">
            <TabsTrigger value="scheduled" className="gap-1.5">
              <Clock className="h-3.5 w-3.5" />
              定时任务
            </TabsTrigger>
            <TabsTrigger value="oneoff" className="gap-1.5">
              <ListTodo className="h-3.5 w-3.5" />
              一次性 / 队列
            </TabsTrigger>
            <TabsTrigger value="history" className="gap-1.5">
              <History className="h-3.5 w-3.5" />
              历史
            </TabsTrigger>
            <TabsTrigger value="terminal" className="gap-1.5">
              <Terminal className="h-3.5 w-3.5" />
              日志
            </TabsTrigger>
          </TabsList>

          <TabsContent value="scheduled" className="mt-0">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">定时任务 (APScheduler)</CardTitle>
                <p className="text-sm text-muted-foreground">
                  按 cron 表达式周期性执行
                </p>
              </CardHeader>
              <CardContent className="space-y-3">
                {loadingScheduled && (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                )}
                {!loadingScheduled && (!scheduled || scheduled.length === 0) && (
                  <p className="text-sm text-muted-foreground">暂无定时任务</p>
                )}
                {!loadingScheduled &&
                  scheduled?.map((job) => (
                    <div
                      key={job.id}
                      className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/30 px-4 py-3"
                    >
                      <div>
                        <p className="font-medium">{job.id}</p>
                        <p className="text-xs text-muted-foreground">
                          下次: {formatDt(job.next_run_time)} · {job.trigger ?? ""}
                        </p>
                      </div>
                      {job.id === "daily_arxiv" && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="gap-1"
                          disabled={runArxiv.isPending}
                          onClick={() => runArxiv.mutate()}
                        >
                          {runArxiv.isPending ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Play className="h-3.5 w-3.5" />
                          )}
                          立即执行
                        </Button>
                      )}
                    </div>
                  ))}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="oneoff" className="mt-0">
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">触发一次性任务</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    抓取指定 feed 或执行每日 ArXiv
                  </p>
                </CardHeader>
                <CardContent className="flex flex-wrap items-center gap-3">
                  <select
                    className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                    value={selectedFeedId}
                    onChange={(e) => setSelectedFeedId(e.target.value)}
                  >
                    <option value="">选择 feed 立即抓取</option>
                    {feeds?.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.name}
                      </option>
                    ))}
                  </select>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={!selectedFeedId || runFeed.isPending}
                    onClick={() => {
                      if (selectedFeedId) runFeed.mutate(selectedFeedId);
                    }}
                  >
                    {runFeed.isPending ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Play className="h-3.5 w-3.5" />
                    )}
                    执行
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={runArxiv.isPending}
                    onClick={() => runArxiv.mutate()}
                  >
                    {runArxiv.isPending ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Play className="h-3.5 w-3.5" />
                    )}
                    执行每日 ArXiv
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={runEnrichBackfill.isPending}
                    onClick={() => runEnrichBackfill.mutate()}
                  >
                    {runEnrichBackfill.isPending ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Play className="h-3.5 w-3.5" />
                    )}
                    翻译全部未翻译
                  </Button>
                </CardContent>
              </Card>

              <div className="grid gap-4 sm:grid-cols-3">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">总结队列</CardTitle>
                    <p className="text-xs text-muted-foreground">
                      待执行 + 执行中: {overview?.summary_queue.queued ?? 0} +{" "}
                      {overview?.summary_queue.started ?? 0}
                    </p>
                  </CardHeader>
                  <CardContent>
                    {!pendingSummary?.length ? (
                      <p className="text-sm text-muted-foreground">无待处理</p>
                    ) : (
                      <ul className="space-y-1.5 text-sm">
                        {(pendingSummary ?? []).slice(0, 10).map((j, i) => (
                          <li
                            key={`${j.job_id}-${j.paper_id ?? "none"}-${i}`}
                            className="truncate rounded bg-muted/50 px-2 py-1 font-mono text-xs"
                          >
                            {j.paper_id ?? j.job_id} · {j.status}
                          </li>
                        ))}
                        {(pendingSummary?.length ?? 0) > 10 && (
                          <li className="text-muted-foreground">
                            … 共 {pendingSummary?.length} 个
                          </li>
                        )}
                      </ul>
                    )}
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">翻译队列</CardTitle>
                    <p className="text-xs text-muted-foreground">
                      待执行 + 执行中: {overview?.enrich_queue.queued ?? 0} +{" "}
                      {overview?.enrich_queue.started ?? 0}
                    </p>
                  </CardHeader>
                  <CardContent>
                    {!pendingEnrich?.length ? (
                      <p className="text-sm text-muted-foreground">无待处理</p>
                    ) : (
                      <ul className="space-y-1.5 text-sm">
                        {(pendingEnrich ?? []).slice(0, 10).map((j, i) => (
                          <li
                            key={`${j.job_id}-${j.paper_id ?? "none"}-${i}`}
                            className="truncate rounded bg-muted/50 px-2 py-1 font-mono text-xs"
                          >
                            {j.paper_id ?? j.job_id} · {j.status}
                          </li>
                        ))}
                        {(pendingEnrich?.length ?? 0) > 10 && (
                          <li className="text-muted-foreground">
                            … 共 {pendingEnrich?.length} 个
                          </li>
                        )}
                      </ul>
                    )}
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">漫画队列</CardTitle>
                    <p className="text-xs text-muted-foreground">
                      待执行 + 执行中: {overview?.comic_queue.queued ?? 0} +{" "}
                      {overview?.comic_queue.started ?? 0}
                    </p>
                  </CardHeader>
                  <CardContent>
                    {!pendingComic?.length ? (
                      <p className="text-sm text-muted-foreground">无待处理</p>
                    ) : (
                      <ul className="space-y-1.5 text-sm">
                        {(pendingComic ?? []).slice(0, 10).map((j, i) => (
                          <li
                            key={`${j.job_id}-${j.paper_id ?? "none"}-${i}`}
                            className="truncate rounded bg-muted/50 px-2 py-1 font-mono text-xs"
                          >
                            {j.paper_id ?? j.job_id} · {j.status}
                          </li>
                        ))}
                        {(pendingComic?.length ?? 0) > 10 && (
                          <li className="text-muted-foreground">
                            … 共 {pendingComic?.length} 个
                          </li>
                        )}
                      </ul>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="history" className="mt-0">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">运行历史</CardTitle>
                <p className="text-sm text-muted-foreground">最近触发的任务（内存记录）</p>
              </CardHeader>
              <CardContent>
                {!history?.length ? (
                  <p className="text-sm text-muted-foreground">暂无记录</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b text-left text-muted-foreground">
                          <th className="pb-2 pr-4">类型</th>
                          <th className="pb-2 pr-4">开始</th>
                          <th className="pb-2 pr-4">结束</th>
                          <th className="pb-2 pr-4">状态</th>
                          <th className="pb-2">结果 / 错误</th>
                        </tr>
                      </thead>
                      <tbody>
                        {history.map((h) => (
                          <tr key={h.job_id} className="border-b last:border-0">
                            <td className="py-2 pr-4 font-medium">{h.job_type}</td>
                            <td className="py-2 pr-4 text-muted-foreground">
                              {formatDt(h.started_at)}
                            </td>
                            <td className="py-2 pr-4 text-muted-foreground">
                              {formatDt(h.ended_at)}
                            </td>
                            <td className="py-2 pr-4">
                              <span
                                className={cn(
                                  "rounded px-1.5 py-0.5 text-xs",
                                  h.status === "completed" && "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
                                  h.status === "failed" && "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
                                  h.status === "running" && "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
                                )}
                              >
                                {h.status}
                              </span>
                            </td>
                            <td className="py-2 text-muted-foreground">
                              {h.result != null
                                ? JSON.stringify(h.result)
                                : h.error ?? "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="terminal" className="mt-0">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">日志</CardTitle>
                <p className="text-sm text-muted-foreground">
                  选择日志源与行数，自动刷新
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-3">
                  <select
                    className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                    value={logSource}
                    onChange={(e) => setLogSource(e.target.value)}
                  >
                    <option value="daily_arxiv">daily_arxiv.log</option>
                    <option value="worker">rq-worker.log</option>
                    <option value="supervisord">supervisord.log</option>
                  </select>
                  <select
                    className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                    value={logLines}
                    onChange={(e) => setLogLines(Number(e.target.value))}
                  >
                    <option value={50}>最近 50 行</option>
                    <option value={100}>最近 100 行</option>
                    <option value={150}>最近 150 行</option>
                    <option value={300}>最近 300 行</option>
                    <option value={500}>最近 500 行</option>
                  </select>
                </div>
              </CardHeader>
              <CardContent>
                {loadingLogs && (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                )}
                {!loadingLogs && (
                  <pre className="max-h-[60vh] overflow-auto rounded border bg-muted/30 p-4 font-mono text-xs leading-relaxed">
                    {logs?.content || logs?.message || "无内容"}
                  </pre>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
