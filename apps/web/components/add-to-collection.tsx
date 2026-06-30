"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, FolderPlus, Loader2, Plus } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "./ui/button";
import { Input } from "./ui/input";

export function AddToCollection({ reportId }: { reportId: string }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [newName, setNewName] = useState("");

  // All collections the user can add to (including nested ones).
  const { data: collections } = useQuery({
    queryKey: ["collections", "all"],
    queryFn: api.allCollections,
    enabled: open,
  });

  // Which collections this report is already in — drives the checkmarks so the
  // panel reflects what's actually saved (and survives re-opening).
  const { data: memberOf } = useQuery({
    queryKey: ["report-collections", reportId],
    queryFn: () => api.collectionsForReport(reportId),
    enabled: open,
  });

  const memberSlugs = useMemo(
    () => new Set((memberOf ?? []).map((c) => c.slug)),
    [memberOf],
  );

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["report-collections", reportId] });
    qc.invalidateQueries({ queryKey: ["collections"] });
  };

  // Toggle membership: remove if already a member, otherwise add.
  const toggle = useMutation({
    mutationFn: (slug: string) =>
      memberSlugs.has(slug)
        ? api.removeFromCollection(slug, reportId)
        : api.addToCollection(slug, reportId),
    onSuccess: invalidate,
  });

  const createAndAdd = useMutation({
    mutationFn: async () => {
      const c = await api.createCollection({ name: newName });
      await api.addToCollection(c.slug, reportId);
      return c;
    },
    onSuccess: () => {
      setNewName("");
      invalidate();
    },
  });

  const pendingSlug = toggle.isPending ? (toggle.variables as string) : null;

  return (
    <div className="relative">
      <Button variant="outline" size="sm" className="w-full" onClick={() => setOpen((v) => !v)}>
        <FolderPlus className="h-4 w-4" /> Add to collection
      </Button>
      {open && (
        <div className="mt-2 space-y-1 rounded-md border bg-card p-2 shadow-sm">
          {collections?.map((c) => {
            const member = memberSlugs.has(c.slug);
            const busy = pendingSlug === c.slug;
            return (
              <button
                key={c.id}
                onClick={() => toggle.mutate(c.slug)}
                disabled={busy}
                className="flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-sm hover:bg-accent disabled:opacity-60"
              >
                {c.name}
                {busy ? (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                ) : member ? (
                  <Check className="h-4 w-4 text-primary" />
                ) : null}
              </button>
            );
          })}
          {collections && collections.length === 0 && (
            <p className="px-2 py-1.5 text-sm text-muted-foreground">No collections yet.</p>
          )}
          <div className="flex gap-1 border-t pt-2">
            <Input
              placeholder="New collection…"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="h-8 text-sm"
            />
            <Button
              size="icon"
              className="h-8 w-8 shrink-0"
              disabled={!newName.trim() || createAndAdd.isPending}
              onClick={() => createAndAdd.mutate()}
              aria-label="Create and add"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
