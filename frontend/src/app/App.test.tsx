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

test("shows login and signup links in the header", () => {
    renderApp();
    expect(screen.getByRole("link", { name: "Log in" })).toHaveAttribute(
        "href",
        "/login",
    );
    expect(screen.getByRole("link", { name: "Sign up" })).toHaveAttribute(
        "href",
        "/signup",
    );
});

test("renders overview features without exposing technology stack details", () => {
    renderApp();
    expect(
        screen.getByRole("heading", {
            name: /what you can monitor/i,
        }),
    ).toBeInTheDocument();
    expect(screen.getByText("Endpoint Monitoring")).toBeInTheDocument();
    expect(screen.getByText("Results & Incidents")).toBeInTheDocument();
    expect(screen.getByText("Alerts & Team Roles")).toBeInTheDocument();
    expect(screen.queryByText(/technology stack/i)).not.toBeInTheDocument();
    expect(
        screen.queryByText(/platform foundation active/i),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("React 18 + TypeScript")).not.toBeInTheDocument();
    expect(screen.queryByText("FastAPI + Python")).not.toBeInTheDocument();
});

test("renders the live backend status widget", () => {
    renderApp();
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByText("Backend API")).toBeInTheDocument();
});
