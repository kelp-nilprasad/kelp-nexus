"use client";

import { useRef, useState } from "react";
import { Maximize2, Minimize2 } from "lucide-react";
import { Button } from "./ui/button";

/**
 * Renders an uploaded HTML report inside a hardened sandboxed iframe.
 *
 * Security model (defense in depth):
 *  - HTML is sanitized server-side on ingest (bleach).
 *  - The render endpoint sets a strict CSP and `X-Content-Type-Options: nosniff`.
 *  - Here the iframe `sandbox` omits `allow-same-origin` and `allow-scripts`, so
 *    even if malicious markup slipped through it cannot run scripts, read cookies,
 *    or reach the parent origin.
 */
export function ReportViewer({ src, title }: { src: string; title: string }) {
  const [fullscreen, setFullscreen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      wrapRef.current?.requestFullscreen?.();
      setFullscreen(true);
    } else {
      document.exitFullscreen?.();
      setFullscreen(false);
    }
  }

  return (
    <div
      ref={wrapRef}
      className="relative flex flex-col overflow-hidden rounded-lg border bg-white"
    >
      <div className="flex items-center justify-between border-b bg-muted/40 px-4 py-2">
        <span className="truncate text-sm font-medium text-muted-foreground">{title}</span>
        <Button variant="ghost" size="sm" onClick={toggleFullscreen} aria-label="Toggle fullscreen">
          {fullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          {fullscreen ? "Exit" : "Fullscreen"}
        </Button>
      </div>
      <iframe
        src={src}
        title={title}
        // No allow-same-origin / allow-scripts: fully isolated rendering.
        sandbox="allow-popups allow-popups-to-escape-sandbox"
        referrerPolicy="no-referrer"
        className="h-[70vh] w-full bg-white"
        style={fullscreen ? { height: "calc(100vh - 41px)" } : undefined}
      />
    </div>
  );
}
