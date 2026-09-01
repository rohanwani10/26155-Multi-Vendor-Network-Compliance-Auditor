import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Navbar from "./components/Navbar";

const geist = Geist({ subsets: ["latin"], variable: "--font-geist" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });

export const metadata: Metadata = {
  title: "Multi-Vendor Network Compliance Auditor",
  description: "Vendor-agnostic network configuration compliance auditing platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning className={`${geist.variable} ${geistMono.variable}`}>
      <body className="min-h-screen bg-canvas text-ink flex flex-col antialiased font-sans">
        <Navbar />
        <main className="flex-grow max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-10">
          {children}
        </main>
        <footer className="border-t border-hairline py-6">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-xs text-mid-gray">
            Compliance Auditor — vendor-agnostic network configuration auditing
          </div>
        </footer>
      </body>
    </html>
  );
}
