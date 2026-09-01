import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  BackdropBlobs,
  KeyIcon,
  Logo,
  MailIcon,
  StudyScene,
} from "../components/LoginArt";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) {
    navigate("/inbox", { replace: true });
    return null;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/inbox", { replace: true });
    } catch (err) {
      setError(
        err.response?.data?.detail || "Login failed. Check your credentials."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-white">
      <BackdropBlobs />

      <div className="relative mx-auto grid min-h-screen max-w-6xl items-center gap-12 px-6 py-12 lg:grid-cols-[1.05fr_minmax(0,420px)] lg:gap-16 lg:px-10">
        {/* Illustration — desktop only. Hidden (not shrunk) below lg so it
            costs mobile users neither bandwidth nor vertical space. */}
        <div className="hidden lg:block">
          <p className="mb-1 text-sm font-semibold uppercase tracking-[0.18em] text-[#26346B]/70">
            EduConnect AI
          </p>
          <h2 className="max-w-md text-3xl font-bold leading-tight text-[#26346B]">
            The control room for your school&rsquo;s conversations.
          </h2>
          <StudyScene className="mt-6 h-auto w-full max-w-[520px]" />
        </div>

        {/* Form card */}
        <div className="login-card mx-auto w-full max-w-[420px] rounded-[28px] bg-white p-8 shadow-[0_24px_60px_-20px_rgba(38,52,107,0.35)] ring-1 ring-[#26346B]/5 sm:p-10">
          <div className="flex flex-col items-center text-center">
            <Logo />
            <h1 className="login-script mt-3 text-[#26346B]">Welcome back</h1>
            <p className="mt-2 text-sm text-gray-500">
              Sign in to the control room
            </p>
          </div>

          <form onSubmit={handleSubmit} className="mt-8">
            {error && (
              <div
                role="alert"
                className="mb-5 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-100"
              >
                {error}
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label
                  htmlFor="login-email"
                  className="mb-1.5 ml-1 block text-sm font-medium text-[#26346B]"
                >
                  Email
                </label>
                <div className="relative">
                  <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[#26346B]/45">
                    <MailIcon />
                  </span>
                  <input
                    id="login-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="login-field"
                    placeholder="admin@educonnect.ai"
                    autoComplete="email"
                    required
                    autoFocus
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor="login-password"
                  className="mb-1.5 ml-1 block text-sm font-medium text-[#26346B]"
                >
                  Password
                </label>
                <div className="relative">
                  <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[#26346B]/45">
                    <KeyIcon />
                  </span>
                  <input
                    id="login-password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="login-field"
                    placeholder="Enter password"
                    autoComplete="current-password"
                    required
                  />
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              aria-busy={loading}
              className="login-submit mt-7"
            >
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>

          {/* No self-service reset exists — only a super_admin can reset a
              password — so this is helper text, not a link to nowhere. */}
          <p className="mt-6 text-center text-xs text-gray-500">
            Lost access? Contact your system administrator.
          </p>
        </div>
      </div>
    </div>
  );
}
