"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ReportCard } from "@/components/report-card";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";

export default function AuthorPage({ params }: { params: { id: string } }) {
  const { id } = params;
  const { data: user } = useQuery({ queryKey: ["user", id], queryFn: () => api.user(id) });
  const { data: reports } = useQuery({
    queryKey: ["user-reports", id],
    queryFn: () => api.userReports(id),
  });

  if (!user) return <p className="text-muted-foreground">Loading…</p>;

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-4">
        <Avatar name={user.name} src={user.avatar_url} size={72} />
        <div>
          <h1 className="text-3xl font-bold">{user.name}</h1>
          <p className="text-muted-foreground">
            {user.title} · {user.team} · {user.department}
          </p>
          <div className="mt-1 flex items-center gap-2">
            <Badge variant="secondary">{user.role}</Badge>
            <span className="text-sm text-muted-foreground">{user.email}</span>
          </div>
        </div>
      </div>

      {user.bio && <p className="max-w-2xl text-muted-foreground">{user.bio}</p>}

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">
          Reports by {user.name} ({reports?.length ?? 0})
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {reports?.map((r) => (
            <ReportCard key={r.id} report={r} />
          ))}
        </div>
        {!reports?.length && <p className="text-muted-foreground">No reports yet.</p>}
      </section>
    </div>
  );
}
