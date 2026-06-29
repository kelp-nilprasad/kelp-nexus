"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Star, Github, ExternalLink, PlayCircle, FileText, History } from "lucide-react";
import { api } from "@/lib/api";
import { useCurrentUser } from "@/lib/auth";
import { ReportViewer } from "@/components/report-viewer";
import { ReportCard } from "@/components/report-card";
import { AddToCollection } from "@/components/add-to-collection";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/input";
import { formatDate, relativeTime } from "@/lib/utils";

export default function ReportDetailPage({ params }: { params: { slug: string } }) {
  const { slug } = params;
  const qc = useQueryClient();
  const { user } = useCurrentUser();
  const [comment, setComment] = useState("");

  const { data: report, isLoading } = useQuery({
    queryKey: ["report", slug],
    queryFn: () => api.getReport(slug),
  });
  const { data: related } = useQuery({
    queryKey: ["related", slug],
    queryFn: () => api.relatedReports(slug),
    enabled: !!report,
  });
  const { data: comments } = useQuery({
    queryKey: ["comments", report?.id],
    queryFn: () => api.comments(report!.id),
    enabled: !!report,
  });
  const { data: favorites } = useQuery({ queryKey: ["favorites"], queryFn: api.favorites });

  const isFav = favorites?.some((f) => f.id === report?.id) ?? false;

  const toggleFav = useMutation({
    mutationFn: () =>
      isFav ? api.removeFavorite(report!.id) : api.addFavorite(report!.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["favorites"] }),
  });

  const postComment = useMutation({
    mutationFn: () => api.addComment(report!.id, comment),
    onSuccess: () => {
      setComment("");
      qc.invalidateQueries({ queryKey: ["comments", report?.id] });
    },
  });

  if (isLoading) return <p className="text-muted-foreground">Loading…</p>;
  if (!report) return <p className="text-muted-foreground">Report not found.</p>;

  const hasHtml = report.versions.some((v) => v.has_html);

  return (
    <div className="space-y-8">
      <div className="grid gap-8 lg:grid-cols-[1fr_300px]">
        <div className="space-y-6">
          {/* Header */}
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              {report.category && <Badge variant="secondary">{report.category.name}</Badge>}
              <Badge variant={report.status === "published" ? "success" : "muted"}>
                {report.status}
              </Badge>
              <Badge variant="outline">{report.visibility}</Badge>
              <Badge variant="muted">v{report.current_version}</Badge>
            </div>
            <h1 className="text-3xl font-bold leading-tight">{report.title}</h1>
            {report.description && (
              <p className="text-lg text-muted-foreground">{report.description}</p>
            )}
            <div className="flex items-center justify-between">
              <Link href={`/authors/${report.author.id}`} className="flex items-center gap-2">
                <Avatar name={report.author.name} src={report.author.avatar_url} />
                <div>
                  <p className="text-sm font-medium">{report.author.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {report.team} · {formatDate(report.created_at)}
                  </p>
                </div>
              </Link>
              {user && (
                <Button
                  variant={isFav ? "default" : "outline"}
                  size="sm"
                  onClick={() => toggleFav.mutate()}
                >
                  <Star className={isFav ? "h-4 w-4 fill-current" : "h-4 w-4"} />
                  {isFav ? "Favorited" : "Favorite"}
                </Button>
              )}
            </div>
          </div>

          {report.summary && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm uppercase tracking-wide text-muted-foreground">
                  Summary
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p>{report.summary}</p>
              </CardContent>
            </Card>
          )}

          {/* HTML viewer */}
          {hasHtml && (
            <ReportViewer src={api.renderUrl(report.slug)} title={report.title} />
          )}

          {/* Comments */}
          <section className="space-y-4">
            <h2 className="text-xl font-semibold">Comments</h2>
            {user && (
              <div className="space-y-2">
                <Textarea
                  placeholder="Add a comment…"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                />
                <Button
                  size="sm"
                  disabled={!comment.trim() || postComment.isPending}
                  onClick={() => postComment.mutate()}
                >
                  Post
                </Button>
              </div>
            )}
            <div className="space-y-4">
              {comments?.map((c) => (
                <div key={c.id} className="flex gap-3">
                  <Avatar name={c.author.name} src={c.author.avatar_url} size={32} />
                  <div>
                    <p className="text-sm">
                      <span className="font-medium">{c.author.name}</span>{" "}
                      <span className="text-xs text-muted-foreground">
                        {relativeTime(c.created_at)}
                      </span>
                    </p>
                    <p className="text-sm text-muted-foreground">{c.body}</p>
                  </div>
                </div>
              ))}
              {!comments?.length && (
                <p className="text-sm text-muted-foreground">No comments yet.</p>
              )}
            </div>
          </section>
        </div>

        {/* Sidebar */}
        <aside className="space-y-6">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm uppercase tracking-wide text-muted-foreground">
                Details
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <Meta label="Team" value={report.team} />
              <Meta label="Department" value={report.department} />
              <Meta label="Project" value={report.project} />
              <Meta label="Views" value={String(report.view_count)} />
              <Meta label="Updated" value={formatDate(report.updated_at)} />
            </CardContent>
          </Card>

          {(report.github_repo || report.demo_url || report.video_url || report.pull_request) && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm uppercase tracking-wide text-muted-foreground">
                  Links
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {report.github_repo && (
                  <ExtLink href={report.github_repo} icon={Github} label="Repository" />
                )}
                {report.pull_request && (
                  <ExtLink href={report.pull_request} icon={ExternalLink} label="Pull request" />
                )}
                {report.demo_url && (
                  <ExtLink href={report.demo_url} icon={ExternalLink} label="Demo" />
                )}
                {report.video_url && (
                  <ExtLink href={report.video_url} icon={PlayCircle} label="Video" />
                )}
              </CardContent>
            </Card>
          )}

          {!!report.tags.length && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm uppercase tracking-wide text-muted-foreground">
                  Tags
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-1.5">
                {report.tags.map((t) => (
                  <Link key={t.id} href={`/search?tag=${t.slug}`}>
                    <Badge variant="outline">{t.name}</Badge>
                  </Link>
                ))}
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm uppercase tracking-wide text-muted-foreground">
                <History className="h-4 w-4" /> Versions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {report.versions
                .slice()
                .reverse()
                .map((v) => (
                  <div key={v.id} className="flex items-center justify-between">
                    <span>v{v.version}</span>
                    <div className="flex items-center gap-2">
                      {v.has_html && (
                        <a
                          className="text-primary hover:underline"
                          href={api.renderUrl(report.slug, v.version)}
                          target="_blank"
                          rel="noreferrer"
                        >
                          HTML
                        </a>
                      )}
                      <span className="text-xs text-muted-foreground">
                        {relativeTime(v.created_at)}
                      </span>
                    </div>
                  </div>
                ))}
              {!report.versions.length && (
                <p className="text-muted-foreground">No versions uploaded.</p>
              )}
            </CardContent>
          </Card>

          {user && <AddToCollection reportId={report.id} />}

          <Link
            href={`/upload`}
            className={buttonVariants({ variant: "outline", className: "w-full" })}
          >
            <FileText className="h-4 w-4" /> New report
          </Link>
        </aside>
      </div>

      {!!related?.length && (
        <section className="space-y-3">
          <h2 className="text-xl font-semibold">Related reports</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {related.map((r) => (
              <ReportCard key={r.id} report={r} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function Meta({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div className="flex justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

function ExtLink({
  href,
  icon: Icon,
  label,
}: {
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="flex items-center gap-2 text-primary hover:underline"
    >
      <Icon className="h-4 w-4" /> {label}
    </a>
  );
}
