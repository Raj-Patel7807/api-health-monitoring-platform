import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";

import { App } from "./app/App";
import { getSessionId, subscribeSession } from "./lib/auth";
import "./app/styles.css";

const queryClient = new QueryClient();
let sessionId = getSessionId();
subscribeSession(() => {
    const next = getSessionId();
    if (next !== sessionId) {
        sessionId = next;
        queryClient.clear();
    }
});

ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
        <QueryClientProvider client={queryClient}>
            <BrowserRouter>
                <App />
            </BrowserRouter>
        </QueryClientProvider>
    </React.StrictMode>,
);
