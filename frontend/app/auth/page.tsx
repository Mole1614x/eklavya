import { AuthForm } from "@/components/auth-form";

export const metadata = { title: "Account" };

export default function AuthPage() {
  return <><header className="page-header"><p className="eyebrow">Your EKLAVYA account</p><h1>Your next breakthrough starts here.</h1><p>Sign in to solve challenges, track your progress and access the workspace built for your role.</p></header><AuthForm /></>;
}
