import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/lib/providers";
import { Nav } from "@/components/nav";

export const metadata: Metadata = {
  title: "Kelp Nexus — Engineering Knowledge Portal",
  description: "Central repository for technical research, POCs, benchmarks, and reports.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <Nav />
          <main className="container py-8">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
