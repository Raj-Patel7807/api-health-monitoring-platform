import { afterEach, expect, it, vi } from "vitest";
import { getDashboardData } from "./dashboardApi";

afterEach(() => vi.unstubAllGlobals());

it("loads all dashboard pages within the API's 100-item limit", async () => {
    const fetchMock = vi.fn(async (input: string) => {
        const url = new URL(input);
        const size = Number(url.searchParams.get("page_size"));
        if (size < 1 || size > 100) return new Response(null, { status: 422 });
        const isIncident = url.pathname === "/api/v1/incidents";
        if (isIncident) expect(url.searchParams.get("status")).toBe("open");
        const page = Number(url.searchParams.get("page"));
        const first = (page - 1) * size;
        const items = Array.from(
            { length: Math.min(size, 101 - first) },
            (_, i) => {
                const id = String(first + i);
                return isIncident
                    ? { id: `incident-${id}`, monitor_id: id }
                    : { id, name: `Monitor ${id}`, enabled: true };
            },
        );
        return Response.json({ items, total: 101, page, page_size: size });
    });
    vi.stubGlobal("fetch", fetchMock);
    const { rows, summary } = await getDashboardData();
    expect(rows).toHaveLength(101);
    expect(rows.at(-1)?.openIncidentId).toBe("incident-100");
    expect(summary.openIncidents).toBe(101);
    expect(fetchMock).toHaveBeenCalledTimes(4);
});
