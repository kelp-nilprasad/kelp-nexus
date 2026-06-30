"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  TrendingUp,
  Clock,
  Eye,
  Star,
  MessageSquare,
  Layers,
  Hash,
  FileText,
  Users,
  BookCheck,
  ArrowRight,
  FolderTree,
} from "lucide-react";
import { api } from "@/lib/api";
import type { ReportSummary } from "@/lib/types";
import { ReportCard } from "@/components/report-card";
import { CollectionTree } from "@/components/collection-tree";
import { SearchAutocomplete } from "@/components/search-autocomplete";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar } from "@/components/ui/avatar";
import { cn, relativeTime } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/* small building blocks                                               */
/* ------------------------------------------------------------------ */

function StatTile({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number | string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border bg-card/70 px-4 py-3 backdrop-blur">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Icon className="h-5 w-5" />
      </div>
      <div className="min-w-0">
        <p className="text-xl font-bold leading-none">{value}</p>
        <p className="truncate text-xs text-muted-foreground">{label}</p>
      </div>
    </div>
  );
}

function SectionHeading({
  icon: Icon,
  title,
  href,
  /** Optional Tailwind classes for the icon chip (bg + text), e.g. "bg-amber-500/10 text-amber-600". */
  accent,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  href?: string;
  accent?: string;
}) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h2 className="flex items-center gap-2 text-lg font-semibold">
        <span
          className={cn(
            "flex h-7 w-7 items-center justify-center rounded-md",
            accent ?? "bg-primary/10 text-primary",
          )}
        >
          <Icon className="h-4 w-4" />
        </span>
        {title}
      </h2>
      {href && (
        <Link
          href={href}
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-primary"
        >
          View all <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      )}
    </div>
  );
}

/** Compact, scannable list row — replaces a full card for secondary feeds. */
function ReportRow({ report, rank }: { report: ReportSummary; rank?: number }) {
  return (
    <Link
      href={`/reports/${report.slug}`}
      className="group flex items-center gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-accent"
    >
      {rank !== undefined ? (
        <span className="w-5 shrink-0 text-center text-sm font-semibold text-muted-foreground">
          {rank}
        </span>
      ) : (
        <Avatar name={report.author.name} src={report.author.avatar_url} size={28} />
      )}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium group-hover:text-primary">{report.title}</p>
        <p className="truncate text-xs text-muted-foreground">
          {report.author.name} · {relativeTime(report.created_at)}
        </p>
      </div>
      <span className="flex shrink-0 items-center gap-1 text-xs text-muted-foreground">
        <Eye className="h-3.5 w-3.5" /> {report.view_count}
      </span>
    </Link>
  );
}

function ListCard({
  icon,
  title,
  href,
  children,
  empty,
  /** Optional Tailwind gradient classes for the header tint, e.g. "bg-gradient-to-r from-blue-500/10 to-transparent". */
  tint,
  /** Optional Tailwind classes for the icon (color), e.g. "text-blue-600". */
  iconColor,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  href?: string;
  children: React.ReactNode;
  empty: boolean;
  tint?: string;
  iconColor?: string;
}) {
  const Icon = icon;
  return (
    <Card className="flex h-full flex-col overflow-hidden">
      <CardHeader
        className={cn(
          "flex-row items-center justify-between space-y-0 pb-2",
          tint,
        )}
      >
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon className={cn("h-4 w-4", iconColor ?? "text-primary")} /> {title}
        </CardTitle>
        {href && !empty && (
          <Link href={href} className="text-xs text-muted-foreground hover:text-primary">
            View all
          </Link>
        )}
      </CardHeader>
      <CardContent className="flex-1 space-y-0.5">
        {empty ? <p className="px-2 py-1 text-sm text-muted-foreground">Nothing yet.</p> : children}
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* page                                                                */
/* ------------------------------------------------------------------ */

export default function DashboardPage() {
  const { data, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
  const { data: stats } = useQuery({ queryKey: ["analytics"], queryFn: api.analytics });
  const { data: techCloud } = useQuery({ queryKey: ["tech-cloud"], queryFn: api.technologyCloud });
  const { data: favorites } = useQuery({ queryKey: ["favorites"], queryFn: api.favorites });

  if (isLoading) return <DashboardSkeleton />;

  const trending = (data?.trending?.length ? data.trending : data?.recently_added) ?? [];
  const categories = Object.entries(data?.category_counts ?? {});

  return (
    <div className="grid gap-8 lg:grid-cols-[300px_minmax(0,1fr)] lg:items-start">
      {/* ---------- LEFT SIDEBAR (sticky): Collections + Browse ---------- */}
      <aside className="space-y-4 self-start lg:sticky lg:top-20">
        {/* Collections — teal/primary tint. CollectionTree renders its own Card; we
            wrap it so the panel reads with a subtle primary header tint. */}
        <Card className="overflow-hidden">
          <CardHeader className="flex-row items-center gap-2 space-y-0 bg-gradient-to-r from-primary/10 to-transparent pb-3">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
              <FolderTree className="h-4 w-4" />
            </span>
            <CardTitle className="text-base">Collections</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <CollectionTree />
          </CardContent>
        </Card>

        {/* Browse — slate/indigo neutral tint */}
        <Card className="overflow-hidden">
          <CardHeader className="flex-row items-center gap-2 space-y-0 bg-gradient-to-r from-indigo-500/10 to-transparent pb-3">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-indigo-500/10 text-indigo-600">
              <Layers className="h-4 w-4" />
            </span>
            <CardTitle className="text-base">Browse</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Categories
              </p>
              <div className="flex flex-wrap gap-1.5">
                {categories.length ? (
                  categories.map(([name, count]) => (
                    <Link key={name} href={`/search?category=${encodeURIComponent(name)}`}>
                      <Badge variant="secondary">
                        {name} <span className="ml-1 opacity-60">{count}</span>
                      </Badge>
                    </Link>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">None yet.</p>
                )}
              </div>
            </div>

            <div className="border-t pt-3">
              <p className="mb-2 flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <Hash className="h-3 w-3" /> Technologies
              </p>
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1.5">
                {(techCloud ?? []).slice(0, 20).map((t) => (
                  <Link key={t.slug} href={`/search?technology=${t.slug}`}>
                    <span
                      className="text-muted-foreground hover:text-primary"
                      style={{ fontSize: `${0.8 + Math.min(t.count, 8) * 0.07}rem` }}
                    >
                      {t.name}
                    </span>
                  </Link>
                ))}
                {!techCloud?.length && (
                  <p className="text-sm text-muted-foreground">None yet.</p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </aside>

      {/* ---------- MAIN AREA ---------- */}
      <div className="space-y-8">
        {/* ---------- SEARCH (clean, prominent) ---------- */}
        <section className="overflow-hidden rounded-2xl border bg-gradient-to-br from-primary/5 via-accent/30 to-transparent p-6">
          <div className="mb-4 space-y-0.5">
            <h1 className="text-2xl font-bold tracking-tight">Knowledge Dashboard</h1>
            <p className="text-sm text-muted-foreground">
              Discover, search, and reuse engineering work across the org.
            </p>
          </div>
          <SearchAutocomplete
            className="max-w-2xl"
            placeholder="Search reports, technologies, authors…"
          />
        </section>

        {/* ---------- STAT TILES ---------- */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatTile icon={FileText} label="Reports" value={stats?.total_reports ?? "—"} />
          <StatTile icon={BookCheck} label="Published" value={stats?.total_published ?? "—"} />
          <StatTile icon={Users} label="Contributors" value={stats?.total_users ?? "—"} />
          <StatTile icon={Eye} label="Total views" value={stats?.total_views ?? "—"} />
        </div>

        {/* ---------- TRENDING (amber tint) ---------- */}
        {!!trending.length && (
          <section>
            <SectionHeading
              icon={TrendingUp}
              title="Trending this week"
              href="/reports"
              accent="bg-amber-500/10 text-amber-600"
            />
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {trending.slice(0, 3).map((r) => (
                <ReportCard key={r.id} report={r} />
              ))}
            </div>
          </section>
        )}

        {/* ---------- Recently added (blue) / Most viewed (violet) ---------- */}
        <div className="grid gap-6 sm:grid-cols-2">
          <ListCard
            icon={Clock}
            title="Recently added"
            href="/reports"
            empty={!data?.recently_added?.length}
            tint="bg-gradient-to-r from-blue-500/10 to-transparent"
            iconColor="text-blue-600"
          >
            {data?.recently_added?.slice(0, 6).map((r) => (
              <ReportRow key={r.id} report={r} />
            ))}
          </ListCard>

          <ListCard
            icon={Eye}
            title="Most viewed"
            href="/reports"
            empty={!data?.most_viewed?.length}
            tint="bg-gradient-to-r from-violet-500/10 to-transparent"
            iconColor="text-violet-600"
          >
            {data?.most_viewed?.slice(0, 6).map((r, i) => (
              <ReportRow key={r.id} report={r} rank={i + 1} />
            ))}
          </ListCard>
        </div>

        {/* ---------- favorites — only when present (rose tint) ---------- */}
        {!!favorites?.length && (
          <section>
            <SectionHeading
              icon={Star}
              title="Your favorites"
              accent="bg-rose-500/10 text-rose-600"
            />
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {favorites.slice(0, 3).map((r) => (
                <ReportCard key={r.id} report={r} />
              ))}
            </div>
          </section>
        )}

        {/* ---------- recent activity (emerald tint) ---------- */}
        <Card className="overflow-hidden">
          <CardHeader className="flex-row items-center gap-2 space-y-0 bg-gradient-to-r from-emerald-500/10 to-transparent pb-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-600">
              <MessageSquare className="h-4 w-4" />
            </span>
            <CardTitle className="text-base">Recent activity</CardTitle>
          </CardHeader>
          <CardContent className="divide-y">
            {(data?.recent_comments ?? []).slice(0, 6).map((c, i) => (
              <Link
                key={i}
                href={`/reports/${c.report_slug}`}
                className="flex gap-3 py-2.5 first:pt-0 last:pb-0"
              >
                <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent text-accent-foreground">
                  <MessageSquare className="h-3.5 w-3.5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="line-clamp-1 text-sm text-foreground">{c.body}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    <span className="font-medium text-foreground/80">{c.author_name}</span> on{" "}
                    {c.report_title} · {relativeTime(c.created_at)}
                  </p>
                </div>
              </Link>
            ))}
            {!data?.recent_comments?.length && (
              <p className="py-1 text-sm text-muted-foreground">No comments yet.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* loading skeleton — keeps layout stable, avoids a jarring flash      */
/* ------------------------------------------------------------------ */

function DashboardSkeleton() {
  return (
    <div className="grid gap-8 lg:grid-cols-[300px_minmax(0,1fr)] lg:items-start">
      {/* sidebar */}
      <div className="space-y-4">
        <div className="h-72 animate-pulse rounded-xl border bg-muted/40" />
        <div className="h-52 animate-pulse rounded-xl border bg-muted/40" />
      </div>
      {/* main */}
      <div className="space-y-8">
        <div className="h-40 animate-pulse rounded-2xl border bg-muted/40" />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl border bg-muted/40" />
          ))}
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-44 animate-pulse rounded-xl border bg-muted/40" />
          ))}
        </div>
        <div className="grid gap-6 sm:grid-cols-2">
          <div className="h-72 animate-pulse rounded-xl border bg-muted/40" />
          <div className="h-72 animate-pulse rounded-xl border bg-muted/40" />
        </div>
      </div>
    </div>
  );
}
