import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { ReportViewer } from "@/components/report-viewer";

describe("ReportViewer", () => {
  it("renders a sandboxed iframe without same-origin/scripts", () => {
    const { container } = render(<ReportViewer src="/api/v1/reports/x/render" title="Demo" />);
    const iframe = container.querySelector("iframe")!;
    expect(iframe).toBeTruthy();
    const sandbox = iframe.getAttribute("sandbox") ?? "";
    // Critical XSS guarantee: the rendered report cannot run scripts or read cookies.
    expect(sandbox).not.toContain("allow-scripts");
    expect(sandbox).not.toContain("allow-same-origin");
  });
});
