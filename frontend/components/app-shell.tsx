"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/sidebar";
import { StudioHeader } from "@/components/studio-header";

/** Authentication uses its own focused layout. All other routes retain the
 * existing header/sidebar geometry unchanged. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  if (pathname === "/auth") {
    return <main className="auth-main" id="main-content">{children}</main>;
  }
  return <>
    <StudioHeader />
    <Sidebar />
    <main className="main" id="main-content">{children}</main>
  </>;
}
