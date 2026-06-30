"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { Fragment } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

const LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  reports: "Reports",
  upload: "Upload",
  admin: "Admin",
  collections: "Collections",
  authors: "Authors",
  search: "Search",
};

function humanize(segment: string): string {
  if (LABELS[segment]) return LABELS[segment];
  return segment
    .replace(/-/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function Breadcrumb() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);

  // On a collection detail page (/collections/{slug}) fetch the collection so we
  // can render its real, nested path (Home > Collections > Parent > Child) using
  // the ancestor chain the API returns, instead of the bare URL slug.
  const isCollectionDetail = segments[0] === "collections" && segments.length === 2;
  const collectionSlug = isCollectionDetail ? segments[1] : null;
  const { data: collection } = useQuery({
    queryKey: ["collection", collectionSlug],
    queryFn: () => api.collection(collectionSlug!),
    enabled: !!collectionSlug,
  });

  // Hide on login, root, and the dashboard itself.
  if (pathname === "/login" || pathname === "/" || pathname === "/dashboard") {
    return null;
  }
  if (segments.length === 0) return null;

  let crumbs: { label: string; href: string; isLast: boolean }[];
  if (isCollectionDetail && collection?.breadcrumbs) {
    crumbs = [
      { label: LABELS.collections, href: "/collections", isLast: false },
      ...collection.breadcrumbs.map((c, i) => ({
        label: c.name,
        href: `/collections/${c.slug}`,
        isLast: i === collection.breadcrumbs.length - 1,
      })),
    ];
  } else {
    crumbs = segments.map((segment, i) => ({
      label: humanize(segment),
      href: "/" + segments.slice(0, i + 1).join("/"),
      isLast: i === segments.length - 1,
    }));
  }

  return (
    <nav
      aria-label="Breadcrumb"
      className="mb-6 flex items-center gap-1.5 text-sm text-muted-foreground"
    >
      <Link href="/dashboard" className="hover:text-foreground">
        Home
      </Link>
      {crumbs.map((crumb) => (
        <Fragment key={crumb.href}>
          <ChevronRight className="h-3.5 w-3.5 shrink-0 opacity-60" />
          {crumb.isLast ? (
            <span className="font-medium text-foreground">{crumb.label}</span>
          ) : (
            <Link href={crumb.href} className="hover:text-foreground">
              {crumb.label}
            </Link>
          )}
        </Fragment>
      ))}
    </nav>
  );
}
