"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useCurrentUser } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const csvToList = (s: string) =>
  s
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);

export default function EditReportPage({ params }: { params: { slug: string } }) {
  const { slug } = params;
  const router = useRouter();
  const qc = useQueryClient();
  const { user } = useCurrentUser();

  const { data: report, isLoading } = useQuery({
    queryKey: ["report", slug],
    queryFn: () => api.getReport(slug),
  });
  const { data: categories } = useQuery({ queryKey: ["categories"], queryFn: api.categories });

  const [form, setForm] = useState({
    title: "",
    description: "",
    summary: "",
    project: "",
    category_id: "",
    status: "published",
    visibility: "internal",
    tags: "",
    technologies: "",
    github_repo: "",
    demo_url: "",
  });
  const [assetFile, setAssetFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Populate the form once the report loads.
  useEffect(() => {
    if (!report) return;
    setForm({
      title: report.title ?? "",
      description: report.description ?? "",
      summary: report.summary ?? "",
      project: report.project ?? "",
      category_id: report.category?.id ?? "",
      status: report.status ?? "published",
      visibility: report.visibility ?? "internal",
      tags: (report.tags ?? []).map((t) => t.name).join(", "),
      technologies: (report.technologies ?? []).map((t) => t.name).join(", "),
      github_repo: report.github_repo ?? "",
      demo_url: report.demo_url ?? "",
    });
  }, [report]);

  function set<K extends keyof typeof form>(k: K, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  function isAcceptedFile(file: File): boolean {
    const name = file.name.toLowerCase();
    return (
      file.type === "text/html" ||
      file.type === "application/pdf" ||
      file.type.startsWith("video/") ||
      name.endsWith(".html") ||
      name.endsWith(".htm") ||
      name.endsWith(".pdf")
    );
  }

  function acceptFile(file: File | undefined | null) {
    if (!file) return;
    if (!isAcceptedFile(file)) {
      setError("Unsupported file type. Upload an HTML, PDF, or video file.");
      return;
    }
    setError("");
    setAssetFile(file);
  }

  function onDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragActive(false);
    acceptFile(e.dataTransfer.files?.[0]);
  }

  const canEdit =
    !!user &&
    !!report &&
    (user.id === report.author.id || user.role === "admin" || user.role === "editor");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!report) return;
    setError("");
    setBusy(true);
    try {
      await api.updateReport(slug, {
        title: form.title,
        description: form.description,
        summary: form.summary,
        project: form.project || null,
        category_id: form.category_id || null,
        status: form.status,
        visibility: form.visibility,
        github_repo: form.github_repo || null,
        demo_url: form.demo_url || null,
        tags: csvToList(form.tags),
        technologies: csvToList(form.technologies),
      });
      // Optionally replace the file (uploads a new version).
      if (assetFile) {
        const fd = new FormData();
        fd.append("file", assetFile);
        await api.uploadVersion(slug, fd);
      }
      qc.invalidateQueries({ queryKey: ["report", slug] });
      qc.invalidateQueries({ queryKey: ["reports"] });
      router.push(`/reports/${slug}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save changes.");
      setBusy(false);
    }
  }

  if (isLoading) return <p className="text-muted-foreground">Loading…</p>;
  if (!report) return <p className="text-muted-foreground">Report not found.</p>;
  if (!canEdit)
    return (
      <div className="space-y-4">
        <p className="text-muted-foreground">You don&apos;t have permission to edit this report.</p>
        <Link href={`/reports/${slug}`} className="text-primary underline">
          Back to report
        </Link>
      </div>
    );

  const isValid =
    form.title.trim() &&
    form.description.trim() &&
    form.summary.trim() &&
    csvToList(form.tags).length > 0;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Edit report</h1>
        <p className="text-sm text-muted-foreground">{report.title}</p>
      </div>

      <form onSubmit={onSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Metadata</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className="mb-1 block text-sm font-medium">Title *</label>
              <Input required value={form.title} onChange={(e) => set("title", e.target.value)} />
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1 block text-sm font-medium">Description *</label>
              <Textarea
                required
                value={form.description}
                onChange={(e) => set("description", e.target.value)}
              />
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1 block text-sm font-medium">Summary *</label>
              <Textarea
                required
                value={form.summary}
                onChange={(e) => set("summary", e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Project</label>
              <Input value={form.project} onChange={(e) => set("project", e.target.value)} />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Category</label>
              <select
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={form.category_id}
                onChange={(e) => set("category_id", e.target.value)}
              >
                <option value="">—</option>
                {categories?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Tags * (comma-separated)</label>
              <Input
                required
                value={form.tags}
                onChange={(e) => set("tags", e.target.value)}
                placeholder="e.g. search, benchmark"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">
                Technologies (comma-separated)
              </label>
              <Input
                value={form.technologies}
                onChange={(e) => set("technologies", e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">GitHub repo</label>
              <Input value={form.github_repo} onChange={(e) => set("github_repo", e.target.value)} />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Demo URL</label>
              <Input value={form.demo_url} onChange={(e) => set("demo_url", e.target.value)} />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Status</label>
              <select
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={form.status}
                onChange={(e) => set("status", e.target.value)}
              >
                <option value="draft">Draft</option>
                <option value="published">Published</option>
                <option value="archived">Archived</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Visibility</label>
              <select
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={form.visibility}
                onChange={(e) => set("visibility", e.target.value)}
              >
                <option value="public">Public</option>
                <option value="internal">Internal</option>
                <option value="private">Private</option>
              </select>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Replace file (optional)</CardTitle>
          </CardHeader>
          <CardContent>
            <div
              role="button"
              tabIndex={0}
              aria-label="Drag and drop a file to upload a new version, or click to browse"
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  fileInputRef.current?.click();
                }
              }}
              onDragOver={(e) => {
                e.preventDefault();
                setDragActive(true);
              }}
              onDragEnter={(e) => {
                e.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={(e) => {
                e.preventDefault();
                setDragActive(false);
              }}
              onDrop={onDrop}
              className={`flex cursor-pointer flex-col items-center justify-center rounded-md border-2 border-dashed px-6 py-8 text-center transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                dragActive
                  ? "border-primary bg-primary/5"
                  : "border-input hover:border-primary/50 hover:bg-accent/50"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                className="sr-only"
                accept=".html,text/html,application/pdf,.pdf,video/*"
                onChange={(e) => acceptFile(e.target.files?.[0])}
              />
              {assetFile ? (
                <>
                  <p className="text-sm font-medium">{assetFile.name}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {Math.round(assetFile.size / 1024)} KB · click or drop to replace
                  </p>
                </>
              ) : (
                <>
                  <p className="text-sm font-medium">
                    {dragActive ? "Drop the file to upload" : "Drag & drop a new file here"}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    or <span className="text-primary underline">click to browse</span>
                  </p>
                </>
              )}
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Leave empty to keep the current file. Uploading here creates a new version (v
              {report.current_version + 1}). HTML is sanitized on upload.
            </p>
          </CardContent>
        </Card>

        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={() => router.push(`/reports/${slug}`)}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy || !isValid}>
            {busy ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </form>
    </div>
  );
}
