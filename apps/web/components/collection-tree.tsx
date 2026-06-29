"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ChevronRight,
  Folder,
  FolderOpen,
  FolderPlus,
  Plus,
  FileText,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Collection } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { cn } from "@/lib/utils";

type TreeNode = Collection & { children: TreeNode[] };

function buildTree(items: Collection[]): TreeNode[] {
  const byId = new Map<string, TreeNode>(items.map((c) => [c.id, { ...c, children: [] }]));
  const roots: TreeNode[] = [];
  for (const node of byId.values()) {
    const parent = node.parent_id ? byId.get(node.parent_id) : null;
    if (parent) parent.children.push(node);
    else roots.push(node);
  }
  const sortRec = (nodes: TreeNode[]) => {
    nodes.sort((a, b) => a.name.localeCompare(b.name));
    nodes.forEach((n) => sortRec(n.children));
  };
  sortRec(roots);
  return roots;
}

export function CollectionTree() {
  const qc = useQueryClient();
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [creatingRoot, setCreatingRoot] = useState(false);
  const [rootName, setRootName] = useState("");

  const { data: collections, isLoading } = useQuery({
    queryKey: ["all-collections"],
    queryFn: api.allCollections,
  });

  const tree = useMemo(() => buildTree(collections ?? []), [collections]);

  const createRoot = useMutation({
    mutationFn: () => api.createCollection({ name: rootName }),
    onSuccess: () => {
      setRootName("");
      setCreatingRoot(false);
      qc.invalidateQueries({ queryKey: ["all-collections"] });
      qc.invalidateQueries({ queryKey: ["collections"] });
    },
  });

  const toggle = (id: string) =>
    setCollapsed((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Folder className="h-5 w-5 text-primary" /> Collections
        </CardTitle>
        <Button variant="outline" size="sm" onClick={() => setCreatingRoot((v) => !v)}>
          <FolderPlus className="h-4 w-4" /> New
        </Button>
      </CardHeader>
      <CardContent className="space-y-1">
        {creatingRoot && (
          <div className="mb-2 flex gap-2">
            <Input
              autoFocus
              placeholder="Collection name"
              value={rootName}
              onChange={(e) => setRootName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && rootName.trim() && createRoot.mutate()}
              className="h-8"
            />
            <Button
              size="sm"
              disabled={!rootName.trim() || createRoot.isPending}
              onClick={() => createRoot.mutate()}
            >
              {createRoot.isPending ? "…" : "Add"}
            </Button>
          </div>
        )}

        {isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}
        {!isLoading && !tree.length && (
          <p className="text-sm text-muted-foreground">
            No collections yet. Click <span className="font-medium">New</span> to create your first
            folder.
          </p>
        )}

        {tree.map((node) => (
          <TreeRow
            key={node.id}
            node={node}
            depth={0}
            collapsed={collapsed}
            toggle={toggle}
            activePath={pathname}
          />
        ))}
      </CardContent>
    </Card>
  );
}

function TreeRow({
  node,
  depth,
  collapsed,
  toggle,
  activePath,
}: {
  node: TreeNode;
  depth: number;
  collapsed: Set<string>;
  toggle: (id: string) => void;
  activePath: string;
}) {
  const qc = useQueryClient();
  const [addingSub, setAddingSub] = useState(false);
  const [subName, setSubName] = useState("");

  const hasChildren = node.children.length > 0;
  const isOpen = !collapsed.has(node.id);
  const isActive = activePath === `/collections/${node.slug}`;

  const createSub = useMutation({
    mutationFn: () => api.createCollection({ name: subName, parent_id: node.id }),
    onSuccess: () => {
      setSubName("");
      setAddingSub(false);
      qc.invalidateQueries({ queryKey: ["all-collections"] });
      qc.invalidateQueries({ queryKey: ["collections"] });
    },
  });

  return (
    <div>
      <div
        className={cn(
          "group flex items-center gap-1 rounded-md py-1.5 pr-2 transition-colors hover:bg-accent",
          isActive && "bg-accent",
        )}
        style={{ paddingLeft: depth * 18 + 4 }}
      >
        {/* expand / collapse */}
        {hasChildren ? (
          <button
            onClick={() => toggle(node.id)}
            className="flex h-5 w-5 shrink-0 items-center justify-center text-muted-foreground hover:text-foreground"
            aria-label={isOpen ? "Collapse" : "Expand"}
          >
            <ChevronRight
              className={cn("h-4 w-4 transition-transform", isOpen && "rotate-90")}
            />
          </button>
        ) : (
          <span className="h-5 w-5 shrink-0" />
        )}

        {isOpen && hasChildren ? (
          <FolderOpen className="h-4 w-4 shrink-0 text-primary" />
        ) : (
          <Folder className="h-4 w-4 shrink-0 text-primary" />
        )}

        <Link
          href={`/collections/${node.slug}`}
          className="min-w-0 flex-1 truncate text-sm font-medium hover:text-primary"
        >
          {node.name}
        </Link>

        {/* report count */}
        {node.report_count > 0 && (
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <FileText className="h-3 w-3" />
            {node.report_count}
          </span>
        )}

        {/* add subfolder (on hover) */}
        <button
          onClick={() => setAddingSub((v) => !v)}
          className="flex h-5 w-5 shrink-0 items-center justify-center rounded text-muted-foreground opacity-0 transition-opacity hover:bg-background hover:text-primary group-hover:opacity-100"
          aria-label="Add subfolder"
          title="Add subfolder"
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
      </div>

      {addingSub && (
        <div className="flex gap-2 py-1" style={{ paddingLeft: depth * 18 + 28 }}>
          <Input
            autoFocus
            placeholder="Subfolder name"
            value={subName}
            onChange={(e) => setSubName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && subName.trim() && createSub.mutate()}
            className="h-7 text-sm"
          />
          <Button
            size="sm"
            className="h-7"
            disabled={!subName.trim() || createSub.isPending}
            onClick={() => createSub.mutate()}
          >
            {createSub.isPending ? "…" : "Add"}
          </Button>
        </div>
      )}

      {isOpen && hasChildren && (
        <div className="ml-[14px] border-l border-border/70">
          {node.children.map((child) => (
            <TreeRow
              key={child.id}
              node={child}
              depth={depth + 1}
              collapsed={collapsed}
              toggle={toggle}
              activePath={activePath}
            />
          ))}
        </div>
      )}
    </div>
  );
}
