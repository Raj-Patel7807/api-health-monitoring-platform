const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getHealth(): Promise<{ status: string }> {
    const response = await fetch(`${apiBaseUrl}/health`);
    if (!response.ok) {
        throw new Error("The API is unavailable.");
    }
    return response.json() as Promise<{ status: string }>;
}
