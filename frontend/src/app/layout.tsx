import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Navbar from "./components/Navbar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Multi-Vendor Network Compliance Auditor",
  description: "Vendor-agnostic network configuration compliance auditing and self-learning vector store platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning className={`h-full bg-slate-950 text-slate-100 ${inter.className}`}>

      <body className="min-h-screen bg-slate-950 text-slate-100 flex flex-col antialiased">
        <Navbar />
        <main className="flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
        <footer className="mt-auto border-t border-slate-800 py-6 text-center text-xs text-slate-500">
          Multi-Vendor Network Compliance Auditor — Integrated with FastAPI Backend (http://localhost:8000)
        </footer>
      </body>
    </html>
  );
}
