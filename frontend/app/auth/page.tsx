import { AuthForm } from "@/components/auth-form";

export const metadata = { title: "Account" };

export default function AuthPage() {
  return <><header className="page-header"><p className="eyebrow">Your EKLAVYA account</p><h1>Practice with progress that follows you</h1><p>Sign in to save submissions, earn verified XP, join learning paths, and enter contests.</p></header><AuthForm /></>;
}
