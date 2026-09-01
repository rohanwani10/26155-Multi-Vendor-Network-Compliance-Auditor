"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ShieldCheck, Upload, BookOpen, LayoutDashboard } from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();

  const navLinks = [
    { name: "Upload", href: "/", icon: Upload },
    { name: "Training queue", href: "/training", icon: BookOpen },
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  ];

  return (
    <nav className="bg-surface-alt border-b border-hairline sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-[10px] bg-ink flex items-center justify-center shrink-0">
              <ShieldCheck className="w-4 h-4 text-paper" strokeWidth={2} />
            </div>
            <span className="font-semibold text-body-lg text-ink">
              Compliance Auditor
            </span>
          </Link>

          <div className="flex items-center gap-1">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive =
                pathname === link.href ||
                (link.href !== "/" && pathname.startsWith(link.href));

              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-pill text-body font-medium transition-colors ${
                    isActive
                      ? "bg-ink text-paper"
                      : "text-mid-gray hover:text-ink hover:bg-canvas"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" strokeWidth={2} />
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
