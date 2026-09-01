"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ShieldCheck, Upload, BookOpen, LayoutDashboard } from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();

  const navLinks = [
    { name: "Upload Configs", href: "/", icon: Upload },
    { name: "Training Queue", href: "/training", icon: BookOpen },
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  ];

  return (
    <nav className="bg-slate-900/90 backdrop-blur-md border-b border-slate-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link href="/" className="flex items-center space-x-3 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 group-hover:scale-105 transition-transform">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight text-white">
                Compliance<span className="text-cyan-400">Auditor</span>
              </span>
              <span className="ml-2 px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase bg-slate-800 text-cyan-400 rounded-full border border-slate-700">
                Next.js 16
              </span>
            </div>
          </Link>

          <div className="flex space-x-1 sm:space-x-2">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive =
                pathname === link.href ||
                (link.href !== "/" && pathname.startsWith(link.href));

              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-sm font-medium transition ${
                    isActive
                      ? "bg-slate-800 text-white shadow-sm border border-slate-700"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? "text-cyan-400" : ""}`} />
                  <span>{link.name}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
}
