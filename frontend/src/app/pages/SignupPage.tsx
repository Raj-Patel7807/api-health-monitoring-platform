import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { signup } from "../../lib/authApi";
import "./auth.css";

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
        <main className="auth-page">
            <div className="auth-card">
                <h1>Create your account</h1>
                <p className="auth-sub">
                    Start monitoring your APIs in minutes.
                </p>
                <form
                    className="auth-form"
                    onSubmit={(event) => {
                        void handleSubmit(event);
                    }}
                >
                    <div className="auth-field">
                        <label htmlFor="signup-name">Full name</label>
                        <input
                            id="signup-name"
                            type="text"
                            placeholder="Your name"
                            value={fullName}
                            onChange={(event) =>
                                setFullName(event.target.value)
                            }
                            required
                        />
                    </div>
                    <div className="auth-field">
                        <label htmlFor="signup-email">Email</label>
                        <input
                            id="signup-email"
                            type="email"
                            placeholder="you@example.com"
                            value={email}
                            onChange={(event) => setEmail(event.target.value)}
                            required
                        />
                    </div>
                    <div className="auth-field">
                        <label htmlFor="signup-password">Password</label>
                        <input
                            id="signup-password"
                            type="password"
                            placeholder="At least 8 characters"
                            value={password}
                            onChange={(event) =>
                                setPassword(event.target.value)
                            }
                            required
                            minLength={8}
                        />
                    </div>
                    {error && (
                        <p role="alert" className="auth-error">
                            {error}
                        </p>
                    )}
                    <button
                        type="submit"
                        className="auth-button"
                        disabled={loading}
                    >
                        {loading ? "Creating account..." : "Sign up"}
                    </button>
                </form>
                <p className="auth-footer">
                    Already have an account? <Link to="/login">Log in</Link>
                </p>
            </div>
        </main>
    );
}
