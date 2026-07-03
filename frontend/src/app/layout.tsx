import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "PokePrecio — Comparador de precios Pokémon TCG Chile",
  description:
    "Compara precios de cartas, ETBs, booster boxes y más en tiendas chilenas. Historial real de precios.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="min-h-screen bg-base text-ink">

        {/* Top bar */}
        <div
          className="w-full py-1.5 text-center text-xs font-semibold tracking-wide"
          style={{ background: "var(--poke-blue)", color: "#fff" }}
        >
          Precios actualizados cada 6 horas · 6 tiendas chilenas monitoreadas
        </div>

        {/* Nav */}
        <header className="sticky top-0 z-50 bg-white border-b-2 border-border-dim shadow-sm">
          <nav className="mx-auto flex max-w-7xl items-center gap-5 px-4 sm:px-6 py-3">
            {/* Logo */}
            <Link href="/" className="flex-shrink-0 flex items-center gap-2">
              {/* Pokéball icon */}
              <div
                className="w-8 h-8 rounded-full flex-shrink-0 overflow-hidden flex flex-col"
                style={{ border: "2px solid #1a1a3e" }}
              >
                <div className="flex-1" style={{ background: "var(--poke-red)" }} />
                <div className="h-px" style={{ background: "#1a1a3e" }} />
                <div className="flex-1 bg-white" />
              </div>
              <span
                className="price-display text-2xl leading-none"
                style={{ fontFamily: "var(--font-bebas, Impact)", color: "var(--poke-blue)" }}
              >
                POKEPRECIO
              </span>
            </Link>

            {/* Search */}
            <form action="/productos" className="flex-1 max-w-md">
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-3 text-sm pointer-events-none">⌕</span>
                <input
                  name="q"
                  placeholder="Buscar ETB, Booster Box, Tin…"
                  className="w-full rounded-full border-2 border-border-dim bg-base pl-9 pr-4 py-2 text-sm text-ink placeholder:text-ink-3 focus:outline-none focus:border-violet transition-colors"
                />
              </div>
            </form>

            {/* Links */}
            <div className="hidden sm:flex items-center gap-1">
              <NavLink href="/">Ofertas</NavLink>
              <NavLink href="/preventas">Preventas</NavLink>
              <NavLink href="/productos">Catálogo</NavLink>
            </div>
          </nav>

          {/* Category quick bar */}
          <div className="border-t border-border-dim bg-base overflow-x-auto">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 flex items-center gap-1 py-1.5 w-max sm:w-auto">
              {CATEGORIES.map((c) => (
                <Link
                  key={c.slug}
                  href={`/productos?q=${encodeURIComponent(c.label)}`}
                  className="flex-shrink-0 flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold text-ink-2 hover:text-violet hover:bg-elevated transition-all border border-transparent hover:border-border-dim"
                >
                  <span>{c.icon}</span>
                  <span>{c.label}</span>
                </Link>
              ))}
            </div>
          </div>
        </header>

        <main className="relative mx-auto max-w-7xl px-4 sm:px-6 py-8">{children}</main>

        <footer className="mt-10 border-t-2 border-border-dim bg-white">
          <div className="mx-auto max-w-7xl px-6 py-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div
                className="w-7 h-7 rounded-full overflow-hidden flex flex-col flex-shrink-0"
                style={{ border: "2px solid #1a1a3e" }}
              >
                <div className="flex-1" style={{ background: "var(--poke-red)" }} />
                <div className="h-px" style={{ background: "#1a1a3e" }} />
                <div className="flex-1 bg-white" />
              </div>
              <span
                className="price-display text-2xl"
                style={{ fontFamily: "var(--font-bebas, Impact)", color: "var(--poke-blue)" }}
              >
                POKEPRECIO
              </span>
            </div>
            <p className="text-xs text-ink-3 max-w-sm">
              Precios recolectados automáticamente de tiendas chilenas. Verifica siempre en la
              tienda antes de comprar. No somos afiliados a ninguna tienda.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}

const CATEGORIES = [
  { slug: "etb", label: "ETB", icon: "📦" },
  { slug: "booster-box", label: "Booster Box", icon: "🗃️" },
  { slug: "sobres", label: "Sobres", icon: "🃏" },
  { slug: "bundle", label: "Bundle", icon: "🎁" },
  { slug: "tin", label: "Tin", icon: "🥫" },
  { slug: "blisters", label: "Blisters", icon: "📋" },
  { slug: "accesorios", label: "Accesorios", icon: "🛡️" },
  { slug: "preventa", label: "Preventas", icon: "🆕" },
];

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="px-3 py-1.5 text-sm font-semibold text-ink-2 hover:text-violet rounded-full hover:bg-elevated transition-all"
    >
      {children}
    </Link>
  );
}
