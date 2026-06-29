"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, FolderPlus, Plus } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "./ui/button";
import { Input } from "./ui/input";

export function AddToCollection({ reportId }: { reportId: string }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [added, setAdded] = useState<Set<string>>(new Set());

  const { data: collections } = useQuery({
    queryKey: ["collections"],
    queryFn: api.collections,
    enabled: open,
  });

  const add = useMutation({
    mutationFn: (slug: string) => api.addToCollection(slug, reportId),
    onSuccess: (_d, slug) => {
      setAdded((s) => new Set(s).add(slug));
      qc.invalidateQueries({ queryKey: ["collections"] });
    },
  });

  const createAndAdd = useMutation({
    mutationFn: async () => {
      const c = await api.createCollection({ name: newName });
      await api.addToCollection(c.slug, reportId);
      return c;
    },
    onSuccess: () => {
      setNewName("");
      qc.invalidateQueries({ queryKey: ["collections"] });
      setOpen(false);
    },
  });

  return (
    <div className="relative">
      <Button variant="outline" size="sm" className="w-full" onClick={() => setOpen((v) => !v)}>
        <FolderPlus className="h-4 w-4" /> Add to collection
      </Button>
      {open && (
        <div className="mt-2 space-y-1 rounded-md border bg-card p-2 shadow-sm">
          {collections?.map((c) => (
            <button
              key={c.id}
              onClick={() => add.mutate(c.slug)}
              className="flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-sm hover:bg-accent"
            >
              {c.name}
              {added.has(c.slug) && <Check className="h-4 w-4 text-primary" />}
            </button>
          ))}
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
