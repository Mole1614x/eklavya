import type { Metadata } from "next";
import { AppShell } from "@/components/app-shell";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "EKLAVYA | Learn. Practice. Master.", template: "%s | EKLAVYA" },
  description: "Practice programming, data, statistics, and AI with hands-on challenges.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip" href="#main-content">Skip to content</a>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
