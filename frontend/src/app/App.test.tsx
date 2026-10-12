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
        screen.getByRole("heading", { level: 1, name: /distributed api health/i }),
    ).toBeInTheDocument();
});

test("renders the stack section heading", () => {
    renderApp();
    expect(
        screen.getByRole("heading", { name: /built on a proven foundation/i }),
    ).toBeInTheDocument();
});

test("renders all four sprint cards", () => {
    renderApp();
    expect(screen.getByText("Safe Foundation")).toBeInTheDocument();
    expect(screen.getByText("Monitoring Loop")).toBeInTheDocument();
    expect(screen.getByText("Store, Confirm & Alert")).toBeInTheDocument();
    expect(screen.getByText("Visibility & Access")).toBeInTheDocument();
});

test("sprint 1 is marked as In Progress", () => {
    renderApp();
    expect(screen.getByText("In Progress")).toBeInTheDocument();
});
