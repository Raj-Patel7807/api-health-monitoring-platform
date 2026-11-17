import { NavLink } from "react-router-dom";
import { useCurrentRole } from "../hooks/useCurrentRole";

export function AppNav() {
    const { isReadOnly } = useCurrentRole();

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
            {!isReadOnly && (
                <NavLink
                    to="/members"
                    className={({ isActive }) =>
                        `app-nav-link${isActive ? " app-nav-link--active" : ""}`
                    }
                    data-testid="nav-members-link"
                >
                    <span aria-hidden="true">👥</span>
                    <span>Members</span>
                </NavLink>
            )}
        </nav>
    );
}
