"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Folder, FolderPlus, Plus, Upload } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent } from "./ui/card";
import { Button } from "./ui/button";
import { Input, Textarea } from "./ui/input";

export function CollectionsPanel() {
  const qc = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const { data: collections } = useQuery({ queryKey: ["collections"], queryFn: api.collections });

  const create = useMutation({
    mutationFn: () => api.createCollection({ name, description }),
    onSuccess: () => {
      setName("");
      setDescription("");
      setCreating(false);
      qc.invalidateQueries({ queryKey: ["collections"] });
    },
  });
  const createError = create.error instanceof Error ? create.error.message : null;

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <Folder className="h-5 w-5 text-primary" /> Collections
        </h2>
        <Button variant="default" size="sm" onClick={() => setCreating((v) => !v)}>
          <FolderPlus className="h-4 w-4" /> New collection
        </Button>
      </div>

      {creating && (
        <Card>
          <CardContent className="space-y-3 pt-5">
            <Input placeholder="Collection name" value={name} onChange={(e) => setName(e.target.value)} />
            <Textarea
              placeholder="Description (optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            {createError && <p className="text-sm text-destructive">{createError}</p>}
            <div className="flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={() => setCreating(false)}>
                Cancel
              </Button>
              <Button size="sm" disabled={!name.trim() || create.isPending} onClick={() => create.mutate()}>
                <Plus className="h-4 w-4" /> {create.isPending ? "Creating…" : "Create"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {collections?.map((c) => (
          <div key={c.id} className="group relative">
            <Link href={`/collections/${c.slug}`}>
              <Card className="h-full transition-shadow hover:shadow-md">
                <CardContent className="flex items-center gap-3 pt-5 pr-10">
                  <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10">
                    <Folder className="h-5 w-5 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <p className="truncate font-medium">{c.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {c.report_count} {c.report_count === 1 ? "report" : "reports"}
                      {c.subfolder_count > 0 && ` · ${c.subfolder_count} folders`}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </Link>
            <Link
              href={`/upload?collection=${c.id}`}
              className="absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground opacity-0 transition hover:bg-primary/10 hover:text-primary focus-visible:opacity-100 group-hover:opacity-100"
              aria-label={`Upload a report to ${c.name}`}
              title="Upload here"
            >
              <Upload className="h-4 w-4" />
            </Link>
          </div>
        ))}
        {!collections?.length && (
          <p className="text-sm text-muted-foreground">
            No collections yet. Create one to group related reports.
          </p>
        )}
      </div>
    </section>
  );
}
