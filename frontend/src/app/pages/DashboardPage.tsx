import { useNavigate } from "react-router-dom";

import { clearTokens } from "../../lib/auth";

export function DashboardPage() {
    const navigate = useNavigate();

    function handleLogout() {
        clearTokens();
        navigate("/login");
    }

    return (
        <main className="container">
            <h1>Dashboard</h1>
            <p>You are logged in.</p>
            <button type="button" onClick={handleLogout}>
                Log out
            </button>
        </main>
    );
}
