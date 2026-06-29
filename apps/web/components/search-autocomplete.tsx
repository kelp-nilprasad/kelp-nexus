"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Search, Hash, Tag as TagIcon, FileText } from "lucide-react";
import { api } from "@/lib/api";
import type { Suggestion } from "@/lib/types";
import { Input } from "./ui/input";
import { cn } from "@/lib/utils";

const ICON = {
  technology: Hash,
  tag: TagIcon,
  report: FileText,
} as const;

function hrefFor(s: Suggestion): string {
  if (s.type === "report") return `/reports/${s.value}`;
  if (s.type === "technology") return `/search?technology=${s.value}`;
  return `/search?tag=${s.value}`;
}

export function SearchAutocomplete({
  className,
  placeholder = "Search reports, technologies, tags…",
}: {
  className?: string;
  placeholder?: string;
}) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const boxRef = useRef<HTMLDivElement>(null);

  // Debounce keystrokes so we don't hit the API on every character.
  useEffect(() => {
    const t = setTimeout(() => setDebounced(q.trim()), 150);
    return () => clearTimeout(t);
  }, [q]);

  const { data: suggestions = [] } = useQuery({
    queryKey: ["suggest", debounced],
    queryFn: () => api.searchSuggest(debounced),
    enabled: debounced.length >= 1,
    staleTime: 30_000,
  });

  // Close on outside click.
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const go = (href: string) => {
    setOpen(false);
    setActive(-1);
    router.push(href);
  };

  const submitFreeText = () => {
    if (q.trim()) go(`/search?q=${encodeURIComponent(q.trim())}`);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!open || !suggestions.length) {
      if (e.key === "Enter") submitFreeText();
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => (i + 1) % suggestions.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => (i - 1 + suggestions.length) % suggestions.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (active >= 0) go(hrefFor(suggestions[active]));
      else submitFreeText();
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  const showDropdown = open && debounced.length >= 1 && suggestions.length > 0;

  return (
    <div ref={boxRef} className={cn("relative", className)}>
      <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
      <Input
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
          setActive(-1);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        className="h-9 pl-8"
        role="combobox"
        aria-expanded={showDropdown}
        aria-autocomplete="list"
      />

      {showDropdown && (
        <ul
          className="absolute z-50 mt-1 max-h-80 w-full min-w-[18rem] overflow-auto rounded-md border bg-popover p-1 shadow-md"
          role="listbox"
        >
          {suggestions.map((s, i) => {
            const Icon = ICON[s.type];
            return (
              <li key={`${s.type}:${s.value}`} role="option" aria-selected={i === active}>
                <button
                  type="button"
                  onMouseEnter={() => setActive(i)}
                  onMouseDown={(e) => {
                    e.preventDefault(); // keep focus; fire before blur
                    go(hrefFor(s));
                  }}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm",
                    i === active ? "bg-accent text-accent-foreground" : "hover:bg-accent",
                  )}
                >
                  <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  <span className="flex-1 truncate">{s.label}</span>
                  <span className="shrink-0 text-[10px] uppercase tracking-wide text-muted-foreground">
                    {s.type}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
