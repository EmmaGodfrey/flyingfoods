import { useMemo } from "react";
import {
  ChartLine,
  House,
  LayoutDashboard,
  Package,
  Receipt,
  User,
  type LucideIcon,
} from "lucide-react";

/**
 * Reusable React + Tailwind UI scaffold aligned to docs/05_UI_DESIGN_SYSTEM.md.
 *
 * Notes:
 * - Requires Tailwind CSS in your app.
 * - Uses arbitrary values for exact palette/spacing parity with the design system.
 * - Swap static placeholders with real route/content data.
 */
export default function ERPBlueWhiteTemplate() {
  const ICON = {
    topbar: 18,
    nav: 16,
    meta: 14,
  } as const;

  const navItems = useMemo<{ label: string; icon: LucideIcon; active: boolean }[]>(
    () => [
      { label: "Overview", icon: House, active: true },
      { label: "Inventory", icon: Package, active: false },
      { label: "Procurement", icon: Receipt, active: false },
      { label: "Reports", icon: ChartLine, active: false },
    ],
    [],
  );

  return (
    <div className="min-h-screen bg-[linear-gradient(to_bottom_right,#FFFFFF,#F5F9FF)] p-6 text-[#111827] md:p-4">
      <div className="mx-auto grid max-w-[1360px] grid-rows-[auto_1fr] gap-6">
        <header className="sticky top-4 z-10 flex items-center justify-between gap-4 rounded-2xl border border-white/90 bg-white/80 px-4 py-3 shadow-[0_4px_20px_rgba(0,0,0,0.05)] backdrop-blur-[10px]">
          <div className="flex items-center gap-2.5 text-base font-semibold">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-[10px] bg-[linear-gradient(140deg,#2563EB,#1D4ED8)] text-white shadow-[0_0_0_3px_rgba(37,99,235,0.14)]">
              <LayoutDashboard size={ICON.topbar} strokeWidth={1.8} aria-hidden="true" />
            </span>
            ERP Interface
          </div>

          <nav className="hidden items-center gap-6 text-sm text-[#6B7280] md:flex" aria-label="Primary">
            <span>Dashboard</span>
            <span>Inventory</span>
            <span>Analytics</span>
          </nav>

          <button
            type="button"
            className="inline-flex h-[34px] w-[34px] items-center justify-center rounded-full border border-[#E5EAF2] bg-white text-[#1D4ED8]"
            aria-label="Profile"
          >
            <User size={ICON.topbar} strokeWidth={1.8} aria-hidden="true" />
          </button>
        </header>

        <div className="grid grid-cols-[250px_1fr] gap-6 lg:grid-cols-1">
          <aside className="h-fit rounded-2xl border border-[rgba(37,99,235,0.12)] bg-white/80 p-6 shadow-[0_4px_20px_rgba(0,0,0,0.05)]">
            <h2 className="mb-4 text-sm font-semibold">Navigation</h2>

            <div className="space-y-2">
              {navItems.map((item) => (
                <button
                  key={item.label}
                  type="button"
                  className={[
                    "flex w-full items-center gap-2 rounded-[10px] border px-3 py-2.5 text-left text-sm transition-all duration-200",
                    item.active
                      ? "border-[rgba(37,99,235,0.2)] bg-[rgba(37,99,235,0.08)] text-[#1D4ED8] shadow-[0_8px_18px_rgba(37,99,235,0.14)]"
                      : "border-transparent text-[#6B7280] hover:border-[rgba(37,99,235,0.15)] hover:bg-white",
                  ].join(" ")}
                >
                  <item.icon size={ICON.nav} strokeWidth={1.8} aria-hidden="true" />
                  {item.label}
                </button>
              ))}
            </div>
          </aside>

          <main className="rounded-2xl border border-[rgba(37,99,235,0.12)] bg-white/80 p-8 shadow-[0_4px_20px_rgba(0,0,0,0.05)] md:p-6">
            <h1 className="mb-4 text-4xl font-semibold tracking-[-0.02em] md:text-[28px]">
              Minimalist Blue and White UI
            </h1>

            <p className="mb-8 max-w-[70ch] text-base leading-[1.55] text-[#6B7280]">
              This starter is built for consistency across future pages: clean spacing, restrained motion,
              glass-like surfaces, and clear hierarchy.
            </p>

            <section className="mb-8 grid grid-cols-3 gap-4 md:grid-cols-1" aria-label="Summary cards">
              <article className="rounded-2xl border border-[rgba(37,99,235,0.12)] bg-white p-6 shadow-[0_4px_20px_rgba(0,0,0,0.05)] transition-all duration-200 hover:-translate-y-[2px] hover:shadow-[0_12px_30px_rgba(37,99,235,0.12)]">
                <h3 className="mb-2 text-[20px] font-medium">Card Title</h3>
                <p className="text-base leading-[1.55] text-[#6B7280]">
                  Body text uses 16px size and balanced contrast for readability.
                </p>
              </article>

              <article className="rounded-2xl border border-[rgba(37,99,235,0.12)] bg-white p-6 shadow-[0_4px_20px_rgba(0,0,0,0.05)] transition-all duration-200 hover:-translate-y-[2px] hover:shadow-[0_12px_30px_rgba(37,99,235,0.12)]">
                <h3 className="mb-2 text-[20px] font-medium">Interaction</h3>
                <p className="text-base leading-[1.55] text-[#6B7280]">
                  Buttons follow the design system with soft hover and subtle elevation.
                </p>

                <div className="mt-6 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="rounded-[10px] bg-[#2563EB] px-6 py-3 text-sm font-medium text-white shadow-[0_8px_18px_rgba(37,99,235,0.2)] transition-all duration-200 hover:-translate-y-[1px] hover:bg-[#1D4ED8]"
                  >
                    Primary Action
                  </button>

                  <button
                    type="button"
                    className="rounded-[10px] border border-[#2563EB] bg-white px-6 py-3 text-sm font-medium text-[#2563EB] transition-all duration-200 hover:border-[#1D4ED8] hover:bg-[#F8FAFF] hover:text-[#1D4ED8]"
                  >
                    Secondary Action
                  </button>
                </div>
              </article>

              <article className="rounded-2xl border border-[rgba(37,99,235,0.12)] bg-white p-6 shadow-[0_4px_20px_rgba(0,0,0,0.05)] transition-all duration-200 hover:-translate-y-[2px] hover:shadow-[0_12px_30px_rgba(37,99,235,0.12)]">
                <h3 className="mb-2 text-[20px] font-medium">Status Styles</h3>
                <p className="text-base leading-[1.55] text-[#6B7280]">
                  Accent colors are semantic and intentionally light.
                </p>

                <div className="mt-4 flex flex-wrap gap-2">
                  <span className="rounded-full bg-[#E8F8F2] px-2.5 py-1.5 text-xs font-medium text-[#047857]">Healthy</span>
                  <span className="rounded-full bg-[#FFF5E5] px-2.5 py-1.5 text-xs font-medium text-[#92400E]">Warning</span>
                  <span className="rounded-full bg-[#FEE2E2] px-2.5 py-1.5 text-xs font-medium text-[#991B1B]">Error</span>
                </div>

                <p className="mt-2 text-sm text-[#6B7280]">Small text remains 14px with muted contrast.</p>
              </article>
            </section>

            <p className="text-sm text-[#6B7280]">Icon scale: topbar {ICON.topbar}px, nav {ICON.nav}px, meta {ICON.meta}px.</p>
          </main>
        </div>
      </div>
    </div>
  );
}
