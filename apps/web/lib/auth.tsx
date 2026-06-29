"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import type { User } from "./types";

/** Current user hook. `null` when unauthenticated, `undefined` while loading. */
export function useCurrentUser(): { user: User | null | undefined; isLoading: boolean } {
  const { data, isLoading } = useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      try {
        return await api.me();
      } catch {
        return null;
      }
    },
    retry: false,
  });
  return { user: data, isLoading };
}

export function canEdit(user: User | null | undefined): boolean {
  return !!user && ["admin", "editor", "author"].includes(user.role);
}

export function isAdmin(user: User | null | undefined): boolean {
  return user?.role === "admin";
}
