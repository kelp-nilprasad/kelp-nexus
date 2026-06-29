"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useCurrentUser, isAdmin } from "@/lib/auth";
import { Avatar } from "@/components/ui/avatar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Role } from "@/lib/types";

const ROLES: Role[] = ["admin", "editor", "author", "viewer"];

export default function AdminPage() {
  const qc = useQueryClient();
  const { user, isLoading } = useCurrentUser();

  const { data: users } = useQuery({
    queryKey: ["admin-users"],
    queryFn: api.adminUsers,
    enabled: isAdmin(user),
  });
  const { data: analytics } = useQuery({
    queryKey: ["analytics"],
    queryFn: api.analytics,
    enabled: isAdmin(user),
  });

  const setRole = useMutation({
    mutationFn: ({ id, role }: { id: string; role: string }) => api.setRole(id, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  if (isLoading) return <p className="text-muted-foreground">Loading…</p>;
  if (!isAdmin(user)) return <p className="text-destructive">Admins only.</p>;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Admin</h1>
        <p className="text-muted-foreground">Manage users, roles, and review usage.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Stat label="Reports" value={analytics?.total_reports} />
        <Stat label="Published" value={analytics?.total_published} />
        <Stat label="Users" value={analytics?.total_users} />
        <Stat label="Total views" value={analytics?.total_views} />
        <Stat label="Views (30d)" value={analytics?.views_last_30d} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Users &amp; roles</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="divide-y">
            {users?.map((u) => (
              <div key={u.id} className="flex items-center justify-between py-3">
                <div className="flex items-center gap-3">
                  <Avatar name={u.name} src={u.avatar_url} size={32} />
                  <div>
                    <p className="text-sm font-medium">{u.name}</p>
                    <p className="text-xs text-muted-foreground">{u.email}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant="secondary">{u.team ?? "—"}</Badge>
                  <select
                    className="h-9 rounded-md border border-input bg-background px-2 text-sm"
                    value={u.role}
                    onChange={(e) => setRole.mutate({ id: u.id, role: e.target.value })}
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function Stat({ label, value }: { label: string; value?: number }) {
  return (
    <Card>
      <CardContent className="pt-5">
        <p className="text-2xl font-bold">{value ?? "—"}</p>
        <p className="text-sm text-muted-foreground">{label}</p>
      </CardContent>
    </Card>
  );
}
