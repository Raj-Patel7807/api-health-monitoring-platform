import { Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./components/ProtectedRoute";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { SignupPage } from "./pages/SignupPage";
import { HealthStatus } from "./components/HealthStatus";
import { MonitorsPage } from "./pages/MonitorsPage";
import { MonitorFormPage } from "./pages/MonitorFormPage";

const STACK = [
    {
        icon: "⚛️",
        name: "React 18 + TypeScript",
        role: "UI layer — strict mode, React Router, TanStack Query",
        tag: "Frontend",
    },
    {
        icon: "⚡",
        name: "FastAPI + Python",
        role: "REST API — typed, async, Pydantic validation, OpenAPI docs",
        tag: "Backend",
    },
    {
        icon: "🐘",
        name: "PostgreSQL + pgvector",
        role: "Primary data store — durable facts, future embeddings",
        tag: "Database",
    },
    {
        icon: "🟥",
        name: "Redis",
        role: "Queue broker, short-lived coordination and cache",
        tag: "Queue",
    },
    {
        icon: "🌿",
        name: "Celery + Celery Beat",
        role: "Background workers and scheduled health-check jobs",
        tag: "Workers",
    },
    {
        icon: "🐳",
        name: "Docker Compose",
        role: "Full local stack — one command to boot all services",
        tag: "Infrastructure",
    },
];

function HomePage() {
    return (
        <div className="page-wrapper">
            {/* ── Header ──────────────────────────────────────────────── */}
            <header className="site-header">
                <div className="container">
                    <a
                        href="/"
                        className="logo"
                        aria-label="API Health Monitor home"
                    >
                        <div className="logo-icon" aria-hidden="true">
                            📡
                        </div>
                        <span className="logo-text">API Health Monitor</span>
                    </a>
                    <span className="header-badge">Header</span>
                </div>
            </header>

            <main>
                {/* ── Hero ──────────────────────────────────────────────── */}
                <section className="hero" aria-labelledby="hero-heading">
                    <div className="container">
                        <div className="hero-eyebrow" role="note">
                            <span
                                className="hero-eyebrow-dot"
                                aria-hidden="true"
                            />
                            Platform Foundation Active
                        </div>

                        <h1 id="hero-heading">API Health Monitor</h1>

                        <p className="hero-sub">
                            Distributed API Health &amp; Incident Monitoring
                            Platform — monitor endpoints, detect failures in
                            under two minutes, confirm incidents, and dispatch
                            alerts with responsible rate limiting and AES-256
                            encrypted configuration.
                        </p>

                        {/* Live backend status widget */}
                        <HealthStatus />
                    </div>
                </section>

                {/* ── Stack ──────────────────────────────────────────────── */}
                <section
                    className="section"
                    aria-labelledby="stack-heading"
                    id="stack"
                >
                    <div className="container">
                        <div className="section-header">
                            <p className="section-label">Technology Stack</p>
                            <h2 className="section-title" id="stack-heading">
                                Built on a proven foundation
                            </h2>
                        </div>

                        <div className="stack-grid">
                            {STACK.map((item, i) => (
                                <article
                                    key={item.name}
                                    className="stack-card"
                                    style={{ animationDelay: `${i * 60}ms` }}
                                >
                                    <span
                                        className="stack-card-icon"
                                        aria-hidden="true"
                                    >
                                        {item.icon}
                                    </span>
                                    <div className="stack-card-name">
                                        {item.name}
                                    </div>
                                    <p className="stack-card-role">
                                        {item.role}
                                    </p>
                                    <span className="stack-card-tag">
                                        {item.tag}
                                    </span>
                                </article>
                            ))}
                        </div>
                    </div>
                </section>
            </main>

            {/* ── Footer ──────────────────────────────────────────────── */}
            <footer className="site-footer">
                <div className="container">
                    <p className="footer-text">© 2026 API Health Monitor</p>
                    <div
                        className="footer-stack"
                        aria-label="Technology stack chips"
                    >
                        {[
                            "React",
                            "FastAPI",
                            "PostgreSQL",
                            "Redis",
                            "Celery",
                            "Docker",
                        ].map((t) => (
                            <span key={t} className="footer-chip">
                                {t}
                            </span>
                        ))}
                    </div>
                </div>
            </footer>
        </div>
    );
}
export function App() {
    return (
        <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route element={<ProtectedRoute />}>
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/monitors" element={<MonitorsPage />} />
                <Route path="/monitors/new" element={<MonitorFormPage />} />
                <Route
                    path="/monitors/:monitorId/edit"
                    element={<MonitorFormPage />}
                />
            </Route>
        </Routes>
    );
}
