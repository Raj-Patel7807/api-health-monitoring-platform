import { NavLink } from "react-router-dom";

export function AppNav() {
    return (
        <nav className="app-nav" aria-label="Main platform navigation">
            <NavLink
                to="/monitors"
                className={({ isActive }) =>
                    `app-nav-link${isActive ? " app-nav-link--active" : ""}`
                }
            >
                <span aria-hidden="true">📡</span>
                <span>Monitors</span>
            </NavLink>
            <NavLink
                to="/incidents"
                className={({ isActive }) =>
                    `app-nav-link${isActive ? " app-nav-link--active" : ""}`
                }
            >
                <span aria-hidden="true">🚨</span>
                <span>Incidents</span>
            </NavLink>
            <NavLink
                to="/channels"
                className={({ isActive }) =>
                    `app-nav-link${isActive ? " app-nav-link--active" : ""}`
                }
            >
                <span aria-hidden="true">🔔</span>
                <span>Channels</span>
            </NavLink>
            <NavLink
                to="/dashboard"
                className={({ isActive }) =>
                    `app-nav-link${isActive ? " app-nav-link--active" : ""}`
                }
            >
                <span aria-hidden="true">📊</span>
                <span>Dashboard</span>
            </NavLink>
        </nav>
    );
}
