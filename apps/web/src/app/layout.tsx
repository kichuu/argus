import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/Providers";
import { CommandPalette } from "@/components/shell/CommandPalette";
import { KeyboardShortcuts } from "@/components/shell/KeyboardShortcuts";
import { NotifsPanel } from "@/components/shell/NotifsPanel";
import { Sidebar } from "@/components/shell/Sidebar";
import { StatusBar } from "@/components/shell/StatusBar";
import { ThemeApplier } from "@/components/shell/ThemeApplier";
import { TopBar } from "@/components/shell/TopBar";

export const metadata: Metadata = {
  title: "argus · World Awareness Platform",
  description: "Claim-ledger world-awareness platform with multi-agent debate over cited evidence.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark" data-light-variant="paper">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Serif:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <Providers>
          <ThemeApplier />
          <KeyboardShortcuts />
          <div
            className="col"
            style={{
              height: "100vh",
              width: "100vw",
              overflow: "hidden",
              background: "var(--bg-0)",
            }}
          >
            <TopBar />
            <div className="row grow" style={{ overflow: "hidden" }}>
              <Sidebar />
              <div className="grow col" style={{ overflow: "hidden", position: "relative" }}>
                {children}
              </div>
            </div>
            <StatusBar />
            <CommandPalette />
            <NotifsPanel />
          </div>
        </Providers>
      </body>
    </html>
  );
}
