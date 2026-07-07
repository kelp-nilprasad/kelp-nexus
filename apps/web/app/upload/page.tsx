"use client";

import { Suspense, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function UploadForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { data: categories } = useQuery({ queryKey: ["categories"], queryFn: api.categories });
  const { data: collections } = useQuery({
    queryKey: ["all-collections"],
    queryFn: api.allCollections,
  });
  // Pre-select the collection when arriving from a folder ("Upload here").
  const [collectionId, setCollectionId] = useState(() => searchParams.get("collection") ?? "");

  const [form, setForm] = useState({
    title: "",
    description: "",
    summary: "",
    project: "",
    category_id: "",
    status: "published",
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

  function set<K extends keyof typeof form>(k: K, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  // Accept the same set the file input advertises: HTML, PDF, or any video.
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

  const tagList = form.tags.split(",").map((s) => s.trim()).filter(Boolean);
  const isValid =
    form.title.trim() &&
    form.description.trim() &&
    form.summary.trim() &&
    tagList.length > 0 &&
    !!assetFile;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!isValid) {
      setError("Description, summary, at least one tag, and a report file are required.");
      return;
    }
    setBusy(true);
    try {
      const report = await api.createReport({
        title: form.title,
        description: form.description || null,
        summary: form.summary || null,
        project: form.project || null,
        category_id: form.category_id || null,
        status: form.status,
        github_repo: form.github_repo || null,
        demo_url: form.demo_url || null,
        tags: tagList,
        technologies: form.technologies.split(",").map((s) => s.trim()).filter(Boolean),
      });

      const fd = new FormData();
      if (assetFile) fd.append("file", assetFile);
      await api.uploadVersion(report.slug, fd);

      if (collectionId) {
        await api.addToCollection(collectionId, report.id);
      }
      router.push(`/reports/${report.slug}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Upload a Report</h1>
        <p className="text-muted-foreground">
          Share research, a benchmark, an RFC, or an HTML report with the org.
        </p>
      </div>

      <form onSubmit={submit} className="space-y-6">
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
              <label className="mb-1 block text-sm font-medium">Add to collection</label>
              <select
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={collectionId}
                onChange={(e) => setCollectionId(e.target.value)}
              >
                <option value="">— None —</option>
                {collections?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.parent_id ? "↳ " : ""}
                    {c.name}
                  </option>
                ))}
              </select>
              {searchParams.get("collection") && collectionId && (
                <p className="mt-1 text-xs text-muted-foreground">
                  Pre-selected from the folder you opened. Change it above if needed.
                </p>
              )}
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
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Files</CardTitle>
          </CardHeader>
          <CardContent>
            <div>
              <label className="mb-1 block text-sm font-medium">Report file *</label>
              <div
                role="button"
                tabIndex={0}
                aria-label="Drag and drop a report file here, or click to browse"
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
                      {dragActive ? "Drop the file to upload" : "Drag & drop a file here"}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      or <span className="text-primary underline">click to browse</span>
                    </p>
                  </>
                )}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Required. HTML, PDF, or video. HTML is sanitized on upload and rendered in a
                sandboxed iframe; PDFs and videos are viewed inline.
              </p>
            </div>
          </CardContent>
        </Card>

        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={() => router.back()}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy || !isValid}>
            {busy ? "Publishing…" : "Publish report"}
          </Button>
        </div>
      </form>
    </div>
  );
}

export default function UploadPage() {
  // useSearchParams() must sit under a Suspense boundary (Next 14 requirement).
  return (
    <Suspense fallback={<p className="text-muted-foreground">Loading…</p>}>
      <UploadForm />
    </Suspense>
  );
}
