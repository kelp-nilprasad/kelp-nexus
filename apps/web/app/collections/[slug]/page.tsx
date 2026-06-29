"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronRight, Folder, FolderPlus, Home, Plus, Trash2, X } from "lucide-react";
import { api } from "@/lib/api";
import { useCurrentUser } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { ReportCard } from "@/components/report-card";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function CollectionPage({ params }: { params: { slug: string } }) {
  const { slug } = params;
  const qc = useQueryClient();
  const router = useRouter();
  const { user } = useCurrentUser();
  const [subName, setSubName] = useState("");
  const [creatingSub, setCreatingSub] = useState(false);

  const { data: collection, isLoading } = useQuery({
    queryKey: ["collection", slug],
    queryFn: () => api.collection(slug),
  });

  const isOwner = user && collection && user.id === collection.owner.id;

  const removeReport = useMutation({
    mutationFn: (reportId: string) => api.removeFromCollection(slug, reportId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["collection", slug] }),
  });

  const createSubfolder = useMutation({
    mutationFn: () => api.createCollection({ name: subName, parent_id: collection!.id }),
    onSuccess: () => {
      setSubName("");
      setCreatingSub(false);
      qc.invalidateQueries({ queryKey: ["collection", slug] });
    },
  });

  const deleteCollection = useMutation({
    mutationFn: () => api.deleteCollection(slug),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["collections"] });
      const parent = collection?.breadcrumbs?.at(-2);
      router.push(parent ? `/collections/${parent.slug}` : "/dashboard");
    },
  });

  if (isLoading) return <p className="text-muted-foreground">Loading…</p>;
  if (!collection) return <p className="text-muted-foreground">Collection not found.</p>;

  return (
    <div className="space-y-6">
      {/* Breadcrumbs */}
      <nav className="flex flex-wrap items-center gap-1 text-sm text-muted-foreground">
        <Link href="/dashboard" className="flex items-center gap-1 hover:text-foreground">
          <Home className="h-3.5 w-3.5" /> Dashboard
        </Link>
        {collection.breadcrumbs.map((b, i) => (
          <span key={b.id} className="flex items-center gap-1">
            <ChevronRight className="h-3.5 w-3.5" />
            {i === collection.breadcrumbs.length - 1 ? (
              <span className="font-medium text-foreground">{b.name}</span>
            ) : (
              <Link href={`/collections/${b.slug}`} className="hover:text-foreground">
                {b.name}
              </Link>
            )}
          </span>
        ))}
      </nav>

      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
            <Folder className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">{collection.name}</h1>
            {collection.description && (
              <p className="text-muted-foreground">{collection.description}</p>
            )}
            <div className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
              <Avatar name={collection.owner.name} src={collection.owner.avatar_url} size={20} />
              {collection.owner.name}
              <Badge variant={collection.is_public ? "secondary" : "muted"}>
                {collection.is_public ? "public" : "private"}
              </Badge>
              <span>
                {collection.report_count} reports · {collection.subfolder_count} folders
              </span>
            </div>
          </div>
        </div>
        {isOwner && (
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setCreatingSub((v) => !v)}>
              <FolderPlus className="h-4 w-4" /> New subfolder
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => deleteCollection.mutate()}
              disabled={deleteCollection.isPending}
            >
              <Trash2 className="h-4 w-4" /> Delete
            </Button>
          </div>
        )}
      </div>

      {creatingSub && (
        <Card>
          <CardContent className="flex gap-2 pt-5">
            <Input
              placeholder="Subfolder name"
              value={subName}
              onChange={(e) => setSubName(e.target.value)}
            />
            <Button
              disabled={!subName.trim() || createSubfolder.isPending}
              onClick={() => createSubfolder.mutate()}
            >
              <Plus className="h-4 w-4" /> Create
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Subfolders */}
      {collection.children.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Subfolders
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {collection.children.map((c) => (
              <Link key={c.id} href={`/collections/${c.slug}`}>
                <Card className="h-full transition-shadow hover:shadow-md">
                  <CardContent className="flex items-center gap-3 pt-5">
                    <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10">
                      <Folder className="h-5 w-5 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate font-medium">{c.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {c.report_count} reports
                        {c.subfolder_count > 0 && ` · ${c.subfolder_count} folders`}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Reports */}
      <section className="space-y-3">
        {collection.children.length > 0 && (
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Reports
          </h2>
        )}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {collection.reports.map((r) => (
            <div key={r.id} className="relative">
              {isOwner && (
                <button
                  onClick={() => removeReport.mutate(r.id)}
                  className="absolute right-2 top-2 z-10 rounded-full bg-background/80 p-1 text-muted-foreground hover:text-destructive"
                  aria-label="Remove from collection"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
              <ReportCard report={r} />
            </div>
          ))}
        </div>
        {!collection.reports.length && !collection.children.length && (
          <p className="text-sm text-muted-foreground">
            This folder is empty. Add a subfolder, or open a report and use “Add to collection”.
          </p>
        )}
      </section>
    </div>
  );
}
