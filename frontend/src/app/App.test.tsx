import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import { App } from "./App";

function renderApp() {
    const client = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return render(
        <QueryClientProvider client={client}>
            <MemoryRouter>
                <App />
            </MemoryRouter>
        </QueryClientProvider>,
    );
}

test("renders the main heading", () => {
    renderApp();
    expect(
        screen.getByRole("heading", {
            level: 1,
            name: "API Health Monitor",
        }),
    ).toBeInTheDocument();
});

test("renders the stack section heading", () => {
    renderApp();
    expect(
        screen.getByRole("heading", { name: /built on a proven foundation/i }),
    ).toBeInTheDocument();
});

test("renders all six stack cards", () => {
    renderApp();
    // Full card names are unique — safe to use getByText.
    expect(screen.getByText("React 18 + TypeScript")).toBeInTheDocument();
    expect(screen.getByText("FastAPI + Python")).toBeInTheDocument();
    expect(screen.getByText("PostgreSQL + pgvector")).toBeInTheDocument();
    expect(screen.getByText("Celery + Celery Beat")).toBeInTheDocument();
    expect(screen.getByText("Docker Compose")).toBeInTheDocument();
    // "Redis" also appears in the footer chip, so assert at least one match.
    expect(screen.getAllByText("Redis").length).toBeGreaterThanOrEqual(1);
});

test("renders the live backend status widget", () => {
    renderApp();
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByText("Backend API")).toBeInTheDocument();
});
