import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { login } from "../../lib/authApi";

export function LoginPage() {
    const navigate = useNavigate();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError(null);
        setLoading(true);
        try {
            await login(email, password);
            navigate("/");
        } catch (err) {
            setError(
                err instanceof Error ? err.message : "Something went wrong.",
            );
        } finally {
            setLoading(false);
        }
    }

    return (
        <main className="container">
            <h1>Log in</h1>
            <form
                onSubmit={(event) => {
                    void handleSubmit(event);
                }}
            >
                <label htmlFor="login-email">Email</label>
                <input
                    id="login-email"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                />
                <label htmlFor="login-password">Password</label>
                <input
                    id="login-password"
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                />
                {error && <p role="alert">{error}</p>}
                <button type="submit" disabled={loading}>
                    {loading ? "Logging in..." : "Log in"}
                </button>
            </form>
            <p>
                New here? <Link to="/signup">Create an account</Link>
            </p>
        </main>
    );
}
