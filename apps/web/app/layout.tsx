import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/lib/providers";
import { Nav } from "@/components/nav";
import { Breadcrumb } from "@/components/breadcrumb";

// Applied before paint to honor the saved theme and avoid a flash of the wrong
// mode. Defaults to dark unless the user explicitly chose light.
const themeInit = `(function(){try{var t=localStorage.getItem('theme');if(t==='light'){document.documentElement.classList.remove('dark');}else{document.documentElement.classList.add('dark');}}catch(e){}})();`;

export const metadata: Metadata = {
  title: "Kelp Nexus — Engineering Knowledge Portal",
  description: "Central repository for technical research, POCs, benchmarks, and reports.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body>
        <Providers>
          <Nav />
          <main className="container py-8">
            <Breadcrumb />
            {children}
          </main>
        </Providers>
      </body>
    </html>
  );
}
