import { render, screen } from "@testing-library/react";

import { App } from "./App";

test("shows the foundation message", () => {
    render(<App />);

    expect(
        screen.getByRole("heading", { name: "API Health Monitor" }),
    ).toBeInTheDocument();
});
