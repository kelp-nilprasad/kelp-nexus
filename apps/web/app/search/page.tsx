"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Search as SearchIcon } from "lucide-react";
import { api } from "@/lib/api";
import { ReportCard } from "@/components/report-card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

function SearchInner() {
  const params = useSearchParams();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [submitted, setSubmitted] = useState(params.get("q") ?? "");

  const technology = params.get("technology") ?? undefined;
  const category = params.get("category") ?? undefined;
  const [authorId, setAuthorId] = useState(params.get("author") ?? "");

  const { data: categories } = useQuery({ queryKey: ["categories"], queryFn: api.categories });
  const { data: authors } = useQuery({ queryKey: ["authors"], queryFn: api.authors });
  const categoryId = categories?.find((c) => c.name === category)?.id;

  const { data, isLoading } = useQuery({
    queryKey: ["search", submitted, technology, categoryId, authorId],
    queryFn: () => {
      const p: Record<string, string> = {};
      if (submitted) p.q = submitted;
      if (technology) p.technology = technology;
      if (categoryId) p.category_id = categoryId;
      if (authorId) p.author_id = authorId;
      return api.search(p);
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Search</h1>
        <p className="text-muted-foreground">
          Full-text search across titles, descriptions, and report content.
        </p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setSubmitted(q);
        }}
        className="flex gap-2"
      >
        <Input
          placeholder="Search keywords, technologies, authors…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="max-w-xl"
        />
        <select
          className="h-10 rounded-md border border-input bg-background px-3 text-sm"
          value={authorId}
          onChange={(e) => setAuthorId(e.target.value)}
        >
          <option value="">All authors</option>
          {authors?.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
        <Button type="submit">
          <SearchIcon className="h-4 w-4" /> Search
        </Button>
      </form>

      <div className="flex flex-wrap gap-2 text-sm">
        {technology && <Badge variant="secondary">technology: {technology}</Badge>}
        {category && <Badge variant="secondary">category: {category}</Badge>}
      </div>

      {isLoading ? (
        <p className="text-muted-foreground">Searching…</p>
      ) : (
        <>
          <p className="text-sm text-muted-foreground">{data?.total ?? 0} results</p>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data?.items.map((item) => (
              <ReportCard key={item.report.id} report={item.report} />
            ))}
          </div>
          {!data?.items.length && (
            <p className="text-muted-foreground">No reports match your search.</p>
          )}
        </>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<p className="text-muted-foreground">Loading…</p>}>
      <SearchInner />
    </Suspense>
  );
}
