import { NavLink } from "react-router-dom";
import { clearTokens } from "../../lib/auth";
import { useCurrentRole } from "../hooks/useCurrentRole";

export function AppNav() {
    const { isReadOnly } = useCurrentRole();

    return (
        <nav className="app-nav" aria-label="Main platform navigation">
            <NavLink
                to="/dashboard"
                className={({ isActive }) =>
                    `app-nav-link${isActive ? " app-nav-link--active" : ""}`
                }
            >
                <span aria-hidden="true">🏠</span>
                <span>Dashboard</span>
            </NavLink>
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
            {!isReadOnly && (
                <NavLink
                    to="/channels"
                    className={({ isActive }) =>
                        `app-nav-link${isActive ? " app-nav-link--active" : ""}`
                    }
                >
                    <span aria-hidden="true">🔔</span>
                    <span>Channels</span>
                </NavLink>
            )}
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
            <NavLink
                to="/profile"
                className={({ isActive }) =>
                    `app-nav-link${isActive ? " app-nav-link--active" : ""}`
                }
                data-testid="nav-profile-link"
            >
                <span aria-hidden="true">👤</span>
                <span>Profile</span>
            </NavLink>
            <button
                type="button"
                className="app-nav-link app-nav-logout"
                onClick={clearTokens}
            >
                Log out
            </button>
        </nav>
    );
}
