"use client";

import { useState, useEffect } from "react";
import { AppSidebar } from "./app-sidebar";
import { Button } from "@/components/ui/button";
import { PanelLeftOpen } from "lucide-react";
import { cn } from "@/lib/utils";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Lock body scroll when sidebar open (helps on mobile)
  useEffect(() => {
    if (sidebarOpen) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = prev;
      };
    }
  }, [sidebarOpen]);

  return (
    <div className="flex h-screen min-h-screen w-full overflow-hidden">
      {/* Overlay: visible when sidebar open, tap/click to close */}
      <button
        type="button"
        aria-label="Close sidebar"
        className={cn(
          "fixed inset-0 z-40 bg-black/50 transition-opacity duration-300 ease-out",
          sidebarOpen
            ? "pointer-events-auto opacity-100"
            : "pointer-events-none opacity-0",
        )}
        onClick={() => setSidebarOpen(false)}
      />

      {/* Sidebar: slide in from right; narrow on mobile, w-56 on sm+ */}
      <div
        className={cn(
          "fixed right-0 top-0 z-50 h-full w-[min(14rem,90vw)] shrink-0 transition-transform duration-300 ease-out sm:w-56",
          sidebarOpen ? "translate-x-0" : "translate-x-full",
        )}
      >
        <AppSidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Main content */}
      <main className="relative min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
        {/* Toggle button: top-right, larger tap target on mobile */}
        {!sidebarOpen && (
          <Button
            variant="ghost"
            size="icon"
            className="fixed right-[max(0.75rem,env(safe-area-inset-right))] top-[max(0.75rem,env(safe-area-inset-top))] z-30 h-11 min-h-[44px] w-11 min-w-[44px] shrink-0 rounded-md border bg-background/95 backdrop-blur hover:bg-muted sm:right-4 sm:top-4 sm:h-9 sm:w-9 sm:min-h-0 sm:min-w-0"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open sidebar"
          >
            <PanelLeftOpen className="h-5 w-5 rotate-180 sm:h-4 sm:w-4" />
          </Button>
        )}
        {children}
      </main>
    </div>
  );
}
