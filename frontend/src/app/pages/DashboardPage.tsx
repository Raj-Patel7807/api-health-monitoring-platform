import { useNavigate } from "react-router-dom";

import { clearTokens } from "../../lib/auth";
import "./auth.css";

export function DashboardPage() {
    const navigate = useNavigate();

    function handleLogout() {
        clearTokens();
        navigate("/login");
    }

    return (
        <main className="auth-page">
            <div className="auth-card">
                <h1>Dashboard</h1>
                <p className="auth-sub">You are logged in.</p>
                <button
                    type="button"
                    className="auth-button"
                    onClick={handleLogout}
                >
                    Log out
                </button>
            </div>
        </main>
    );
}
