"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { TrendingUp, Clock, Eye, Star, MessageSquare, Layers, Hash } from "lucide-react";
import { api } from "@/lib/api";
import { ReportCard } from "@/components/report-card";
import { CollectionTree } from "@/components/collection-tree";
import { SearchAutocomplete } from "@/components/search-autocomplete";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { relativeTime } from "@/lib/utils";

function Section({
  title,
  icon: Icon,
  items,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  items: import("@/lib/types").ReportSummary[];
}) {
  if (!items?.length) return null;
  return (
    <section className="space-y-3">
      <h2 className="flex items-center gap-2 text-lg font-semibold">
        <Icon className="h-5 w-5 text-primary" /> {title}
      </h2>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {items.slice(0, 6).map((r) => (
          <ReportCard key={r.id} report={r} />
        ))}
      </div>
    </section>
  );
}

export default function DashboardPage() {
  const { data, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
  const { data: techCloud } = useQuery({
    queryKey: ["tech-cloud"],
    queryFn: api.technologyCloud,
  });
  const { data: favorites } = useQuery({ queryKey: ["favorites"], queryFn: api.favorites });

  if (isLoading) return <p className="text-muted-foreground">Loading dashboard…</p>;

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div className="space-y-4">
        <div>
          <h1 className="text-3xl font-bold">Knowledge Dashboard</h1>
          <p className="text-muted-foreground">
            Discover, search, and reuse engineering work across the org.
          </p>
        </div>
        <SearchAutocomplete
          className="max-w-xl"
          placeholder="Quick search reports, technologies, authors…"
        />
      </div>

      {/* Two-column workspace: navigation rail (left) + content feeds (right) */}
      <div className="grid gap-8 lg:grid-cols-[320px_minmax(0,1fr)] lg:items-start">
        {/* LEFT RAIL — collections tree + taxonomy */}
        <aside className="space-y-6 lg:sticky lg:top-20">
          <CollectionTree />

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Layers className="h-5 w-5 text-primary" /> Categories
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {Object.entries(data?.category_counts ?? {}).map(([name, count]) => (
                <Link key={name} href={`/search?category=${encodeURIComponent(name)}`}>
                  <Badge variant="secondary">
                    {name} <span className="ml-1 opacity-60">{count}</span>
                  </Badge>
                </Link>
              ))}
              {!Object.keys(data?.category_counts ?? {}).length && (
                <p className="text-sm text-muted-foreground">No categories yet.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Hash className="h-5 w-5 text-primary" /> Technology cloud
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap items-baseline gap-x-3 gap-y-1.5">
              {(techCloud ?? []).slice(0, 24).map((t) => (
                <Link key={t.slug} href={`/search?technology=${t.slug}`}>
                  <span
                    className="text-muted-foreground hover:text-primary"
                    style={{ fontSize: `${0.8 + Math.min(t.count, 8) * 0.08}rem` }}
                  >
                    {t.name}
                  </span>
                </Link>
              ))}
              {!techCloud?.length && (
                <p className="text-sm text-muted-foreground">No technologies yet.</p>
              )}
            </CardContent>
          </Card>
        </aside>

        {/* RIGHT — content feeds */}
        <div className="space-y-8">
          <Section title="Trending this week" icon={TrendingUp} items={data?.trending ?? []} />
          <Section title="Recently added" icon={Clock} items={data?.recently_added ?? []} />
          <Section title="Most viewed" icon={Eye} items={data?.most_viewed ?? []} />
          {!!favorites?.length && (
            <Section title="Your favorites" icon={Star} items={favorites} />
          )}

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <MessageSquare className="h-5 w-5 text-primary" /> Recent comments
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              {(data?.recent_comments ?? []).map((c, i) => (
                <Link
                  key={i}
                  href={`/reports/${c.report_slug}`}
                  className="block rounded-md border p-3 text-sm transition-colors hover:bg-accent"
                >
                  <p className="line-clamp-2 text-foreground">{c.body}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {c.author_name} on {c.report_title} · {relativeTime(c.created_at)}
                  </p>
                </Link>
              ))}
              {!data?.recent_comments?.length && (
                <p className="text-sm text-muted-foreground">No comments yet.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
