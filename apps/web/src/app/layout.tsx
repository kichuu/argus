import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Serif, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/Providers";
import { CommandPalette } from "@/components/shell/CommandPalette";
import { KeyboardShortcuts } from "@/components/shell/KeyboardShortcuts";
import { NotifsPanel } from "@/components/shell/NotifsPanel";
import { Sidebar } from "@/components/shell/Sidebar";
import { StatusBar } from "@/components/shell/StatusBar";
import { ThemeApplier } from "@/components/shell/ThemeApplier";
import { TopBar } from "@/components/shell/TopBar";

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

const ibmPlexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-ibm-plex-sans",
  display: "swap",
});

const ibmPlexSerif = IBM_Plex_Serif({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-ibm-plex-serif",
  display: "swap",
});

export const metadata: Metadata = {
  title: "argus · World Awareness Platform",
  description: "Claim-ledger world-awareness platform with multi-agent debate over cited evidence.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      data-theme="dark"
      data-light-variant="paper"
      className={`${jetbrainsMono.variable} ${ibmPlexSans.variable} ${ibmPlexSerif.variable}`}
    >
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
