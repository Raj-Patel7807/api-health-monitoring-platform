import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { signup } from "../../lib/authApi";

export function SignupPage() {
    const navigate = useNavigate();
    const [fullName, setFullName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError(null);
        setLoading(true);
        try {
            await signup(fullName, email, password);
            navigate("/login");
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
            <h1>Create account</h1>
            <form
                onSubmit={(event) => {
                    void handleSubmit(event);
                }}
            >
                <label htmlFor="signup-name">Full name</label>
                <input
                    id="signup-name"
                    type="text"
                    value={fullName}
                    onChange={(event) => setFullName(event.target.value)}
                    required
                />
                <label htmlFor="signup-email">Email</label>
                <input
                    id="signup-email"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                />
                <label htmlFor="signup-password">Password</label>
                <input
                    id="signup-password"
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                    minLength={8}
                />
                {error && <p role="alert">{error}</p>}
                <button type="submit" disabled={loading}>
                    {loading ? "Creating account..." : "Sign up"}
                </button>
            </form>
            <p>
                Already have an account? <Link to="/login">Log in</Link>
            </p>
        </main>
    );
}
