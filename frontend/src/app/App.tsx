import { Link, Outlet, Route, Routes } from "react-router-dom";

import { useCurrentRole } from "./hooks/useCurrentRole";
import { GuestRoute, ProtectedRoute } from "./components/ProtectedRoute";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { SignupPage } from "./pages/SignupPage";
import { HealthStatus } from "./components/HealthStatus";
import { MonitorsPage } from "./pages/MonitorsPage";
import { MonitorFormPage } from "./pages/MonitorFormPage";
import { MonitorDetailPage } from "./pages/MonitorDetailPage";
import { ChannelsPage } from "./pages/ChannelsPage";
import { ChannelFormPage } from "./pages/ChannelFormPage";
import { IncidentsPage } from "./pages/IncidentsPage";
import { IncidentDetailPage } from "./pages/IncidentDetailPage";
import { MembersPage } from "./pages/MembersPage";

const FEATURES = [
    {
        title: "Endpoint Monitoring",
        description:
            "Configure HTTP checks with custom intervals, timeouts, and expected status codes.",
    },
    {
        title: "Results & Incidents",
        description:
            "View check history, response times, and open or resolved incident timelines.",
    },
    {
        title: "Alerts & Team Roles",
        description:
            "Send failure notifications to team channels and manage member permissions.",
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
                    <nav className="header-auth-actions" aria-label="Account">
                        <Link className="header-login-link" to="/login">
                            Log in
                        </Link>
                        <Link className="header-signup-link" to="/signup">
                            Sign up
                        </Link>
                    </nav>
                </div>
            </header>

            <main>
                {/* ── Hero ──────────────────────────────────────────────── */}
                <section className="hero" aria-labelledby="hero-heading">
                    <div className="container">
                        <h1 id="hero-heading">API Health Monitor</h1>

                        <p className="hero-sub">
                            Monitor API endpoints, review check history, track
                            incidents, and send alerts to your team.
                        </p>

                        <div className="hero-actions">
                            <Link
                                className="hero-btn hero-btn--primary"
                                to="/signup"
                            >
                                Get started
                            </Link>
                            <Link
                                className="hero-btn hero-btn--secondary"
                                to="/login"
                            >
                                Sign in
                            </Link>
                        </div>

                        {/* Live backend status widget */}
                        <HealthStatus />
                    </div>
                </section>

                {/* ── Overview ──────────────────────────────────────────── */}
                <section className="section" aria-labelledby="overview-heading">
                    <div className="container">
                        <div className="section-header">
                            <h2 className="section-title" id="overview-heading">
                                What you can monitor
                            </h2>
                        </div>

                        <div className="capabilities-grid">
                            {FEATURES.map((item) => (
                                <article
                                    key={item.title}
                                    className="stack-card"
                                >
                                    <h3 className="stack-card-name">
                                        {item.title}
                                    </h3>
                                    <p className="stack-card-role">
                                        {item.description}
                                    </p>
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
                </div>
            </footer>
        </div>
    );
}
function WriteAccess() {
    const { isLoading, isReadOnly } = useCurrentRole();
    if (isLoading) return <p role="status">Loading team permissions…</p>;
    if (isReadOnly)
        return (
            <p role="alert">
                An admin or operator role is required.{" "}
                <Link to="/dashboard">Back to dashboard</Link>
            </p>
        );
    return <Outlet />;
}

export function App() {
    return (
        <Routes>
            <Route element={<GuestRoute />}>
                <Route path="/" element={<HomePage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/signup" element={<SignupPage />} />
            </Route>
            <Route element={<ProtectedRoute />}>
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/monitors" element={<MonitorsPage />} />
                <Route
                    path="/monitors/:monitorId"
                    element={<MonitorDetailPage />}
                />
                <Route element={<WriteAccess />}>
                    <Route path="/monitors/new" element={<MonitorFormPage />} />
                    <Route
                        path="/monitors/:monitorId/edit"
                        element={<MonitorFormPage />}
                    />
                    <Route path="/channels" element={<ChannelsPage />} />
                    <Route path="/channels/new" element={<ChannelFormPage />} />
                    <Route
                        path="/channels/:channelId/edit"
                        element={<ChannelFormPage />}
                    />
                </Route>
                <Route path="/incidents" element={<IncidentsPage />} />
                <Route
                    path="/incidents/:incidentId"
                    element={<IncidentDetailPage />}
                />
                <Route path="/members" element={<MembersPage />} />
            </Route>
        </Routes>
    );
}
