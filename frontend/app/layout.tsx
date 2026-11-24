import type { Metadata } from "next";
import { Sidebar } from "@/components/sidebar";
import { StudioHeader } from "@/components/studio-header";
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
        <StudioHeader />
        <Sidebar />
        <main className="main" id="main-content">{children}</main>
      </body>
    </html>
  );
}
