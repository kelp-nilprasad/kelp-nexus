"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Boxes } from "lucide-react";
import { api } from "@/lib/api";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function LoginPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [email, setEmail] = useState("admin@kelp.dev");
  const [password, setPassword] = useState("password123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const { data: config } = useQuery({ queryKey: ["auth-config"], queryFn: api.authConfig });

  async function handleDevLogin(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.devLogin(email, password);
      await qc.invalidateQueries({ queryKey: ["me"] });
      router.push("/dashboard");
    } catch {
      setError("Invalid credentials");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-[80vh] items-center justify-center">
      <Card className="w-full max-w-md">
        <CardHeader className="items-center text-center">
          <Boxes className="h-9 w-9 text-primary" />
          <CardTitle className="text-2xl">Kelp Nexus</CardTitle>
          <p className="text-sm text-muted-foreground">Engineering Knowledge Portal</p>
        </CardHeader>
        <CardContent className="space-y-4">
          {config?.microsoft && (
            <a
              href="/api/v1/auth/login"
              className={buttonVariants({ variant: "outline", className: "w-full" })}
            >
              Sign in with Microsoft (SSO)
            </a>
          )}
          {config?.dev_login && (
            <form onSubmit={handleDevLogin} className="space-y-3">
              {config?.microsoft && (
                <div className="relative py-2 text-center text-xs text-muted-foreground">
                  <span className="bg-card px-2">or use a dev account</span>
                </div>
              )}
              <Input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <Input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Signing in…" : "Sign in"}
              </Button>
              <p className="text-center text-xs text-muted-foreground">
                Seeded: admin@kelp.dev / password123
              </p>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
