import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ImportMarkdownModal } from "./ImportMarkdownModal";
import * as monitorsApi from "../../lib/monitorsApi";

vi.mock("../../lib/monitorsApi", async () => {
    const actual = await vi.importActual("../../lib/monitorsApi");
    return {
        ...actual,
        extractMonitorsFromMarkdown: vi.fn(),
        createMonitorsBatch: vi.fn(),
    };
});

describe("ImportMarkdownModal", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("renders nothing when isOpen is false", () => {
        const { container } = render(
            <ImportMarkdownModal
                isOpen={false}
                onClose={vi.fn()}
                onSuccess={vi.fn()}
            />,
        );
        expect(container.firstChild).toBeNull();
    });

    it("renders step 1 inputs and validates empty extraction", async () => {
        render(
            <ImportMarkdownModal
                isOpen={true}
                onClose={vi.fn()}
                onSuccess={vi.fn()}
            />,
        );

        expect(
            screen.getByText(/Import API Endpoints from Markdown/i),
        ).toBeInTheDocument();
        const extractBtn = screen.getByText(/Extract Endpoints with AI/i);
        expect(extractBtn).toBeDisabled();

        const textarea = screen.getByPlaceholderText(
            /Paste API documentation here/i,
        );
        fireEvent.change(textarea, { target: { value: "   " } });
        expect(extractBtn).toBeDisabled();
    });

    it("transitions to step 2 after extracting endpoints and allows batch creation", async () => {
        const mockExtract = vi.mocked(monitorsApi.extractMonitorsFromMarkdown);
        mockExtract.mockResolvedValueOnce({
            endpoints: [
                {
                    name: "Health Ping",
                    method: "GET",
                    url: "https://api.example.com/health",
                    expected_status_code: 200,
                    timeout_seconds: 10,
                    check_interval_seconds: 60,
                    failure_threshold: 3,
                    recovery_threshold: 2,
                    description: null,
                },
            ],
            total_found: 1,
            warnings: [],
            used_llm: true,
        });

        const mockBatch = vi.mocked(monitorsApi.createMonitorsBatch);
        mockBatch.mockResolvedValueOnce({
            created: [],
            count: 1,
        });

        const handleSuccess = vi.fn();
        const handleClose = vi.fn();

        render(
            <ImportMarkdownModal
                isOpen={true}
                onClose={handleClose}
                onSuccess={handleSuccess}
            />,
        );

        const textarea = screen.getByPlaceholderText(
            /Paste API documentation here/i,
        );
        fireEvent.change(textarea, {
            target: { value: "### `GET /health`\nReturns 200 OK." },
        });

        const extractBtn = screen.getByText(/Extract Endpoints with AI/i);
        fireEvent.click(extractBtn);

        await waitFor(() => {
            expect(
                screen.getByText(/Gemini Flash-Lite Agent/i),
            ).toBeInTheDocument();
        });

        expect(screen.getByDisplayValue("Health Ping")).toBeInTheDocument();
        expect(
            screen.getByDisplayValue("https://api.example.com/health"),
        ).toBeInTheDocument();

        const confirmBtn = screen.getByText(/Confirm & Add \(1\) Monitors/i);
        fireEvent.click(confirmBtn);

        await waitFor(() => {
            expect(mockBatch).toHaveBeenCalledTimes(1);
            expect(handleSuccess).toHaveBeenCalledWith(1);
        });
    });
});
