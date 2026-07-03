"use client";

import { useQuery } from "@tanstack/react-query";
import { Boxes } from "lucide-react";
import { api } from "@/lib/api";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function LoginPage() {
  const { data: config } = useQuery({ queryKey: ["auth-config"], queryFn: api.authConfig });

  return (
    <div className="flex min-h-[80vh] items-center justify-center">
      <Card className="w-full max-w-md">
        <CardHeader className="items-center text-center">
          <Boxes className="h-9 w-9 text-primary" />
          <CardTitle className="text-2xl">Kelp Nexus</CardTitle>
          <p className="text-sm text-muted-foreground">Engineering Knowledge Portal</p>
        </CardHeader>
        <CardContent className="space-y-4">
          {config?.microsoft ? (
            <a
              href="/api/v1/auth/login"
              className={buttonVariants({ variant: "default", className: "w-full" })}
            >
              Sign in with Microsoft
            </a>
          ) : (
            <p className="text-center text-sm text-muted-foreground">
              Microsoft sign-in is not configured. Set the MSAL app credentials on the
              server to enable login.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
