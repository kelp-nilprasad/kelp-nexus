"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { LayoutDashboard, FileText, Upload, Shield, LogOut, Boxes } from "lucide-react";
import { useCurrentUser, isAdmin } from "@/lib/auth";
import { api } from "@/lib/api";
import { Avatar } from "./ui/avatar";
import { Button } from "./ui/button";
import { SearchAutocomplete } from "./search-autocomplete";
import { cn } from "@/lib/utils";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/upload", label: "Upload", icon: Upload },
];

export function Nav() {
  const pathname = usePathname();
  const router = useRouter();
  const qc = useQueryClient();
  const { user } = useCurrentUser();

  if (pathname === "/login" || pathname === "/") return null;

  async function logout() {
    await api.logout();
    qc.clear();
    router.push("/login");
  }

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
      <div className="container flex h-14 items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/dashboard" className="flex items-center gap-2 font-semibold">
            <Boxes className="h-5 w-5 text-primary" /> Kelp Nexus
          </Link>
          <nav className="hidden items-center gap-1 md:flex">
            {links.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors",
                  pathname.startsWith(href)
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4" /> {label}
              </Link>
            ))}
            {isAdmin(user) && (
              <Link
                href="/admin"
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors",
                  pathname.startsWith("/admin")
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <Shield className="h-4 w-4" /> Admin
              </Link>
            )}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <SearchAutocomplete
            className="hidden w-72 md:block"
            placeholder="Search reports…"
          />
          {user && (
            <Link href={`/authors/${user.id}`} className="flex items-center gap-2">
              <Avatar name={user.name} src={user.avatar_url} size={30} />
              <span className="hidden text-sm sm:inline">{user.name}</span>
            </Link>
          )}
          <Button variant="ghost" size="icon" onClick={logout} aria-label="Log out">
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  );
}
