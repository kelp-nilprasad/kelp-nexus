import Link from "next/link";
import { Eye } from "lucide-react";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader } from "./ui/card";
import { Avatar } from "./ui/avatar";
import { relativeTime } from "@/lib/utils";
import type { ReportSummary } from "@/lib/types";

const statusVariant = { published: "success", draft: "warning", archived: "muted" } as const;

export function ReportCard({ report }: { report: ReportSummary }) {
  return (
    <Card className="flex h-full flex-col transition-shadow hover:shadow-md">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          {report.category && <Badge variant="secondary">{report.category.name}</Badge>}
          <Badge variant={statusVariant[report.status]}>{report.status}</Badge>
        </div>
        <Link href={`/reports/${report.slug}`} className="mt-2 block">
          <h3 className="line-clamp-2 text-base font-semibold leading-snug hover:text-primary">
            {report.title}
          </h3>
        </Link>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col justify-between gap-3">
        <p className="line-clamp-3 text-sm text-muted-foreground">
          {report.summary || report.description || "No summary available."}
        </p>
        <div className="flex flex-wrap gap-1.5">
          {report.technologies.slice(0, 4).map((t) => (
            <Badge key={t.id} variant="outline">
              {t.name}
            </Badge>
          ))}
        </div>
        <div className="flex items-center justify-between border-t pt-3 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <Avatar name={report.author.name} src={report.author.avatar_url} size={24} />
            <span>{report.author.name}</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <Eye className="h-3.5 w-3.5" /> {report.view_count}
            </span>
            <span>{relativeTime(report.created_at)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
