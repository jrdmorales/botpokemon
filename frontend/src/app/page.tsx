import Link from "next/link";
import { api, formatCLP, type Deal, type Preorder } from "@/lib/api";

export const revalidate = 300;

export default async function Dashboard() {
  const [deals, preorders] = await Promise.all([
    api.deals("min_discount=10&limit=12").catch(() => [] as Deal[]),
    api.preorders().catch(() => [] as Preorder[]),
  ]);

  return (
    <div className="space-y-12">

      {/* Hero banner */}
      <section
        className="rounded-2xl overflow-hidden relative"
        style={{ background: "linear-gradient(135deg, var(--poke-blue) 0%, #2d3aad 100%)" }}
      >
        {/* Pokéball decoration */}
        <div
          className="absolute right-0 top-0 w-72 h-72 rounded-full opacity-10 translate-x-16 -translate-y-16"
          style={{ border: "40px solid white" }}
        />
        <div
          className="absolute right-16 top-32 w-48 h-48 rounded-full opacity-5"
          style={{ border: "30px solid white" }}
        />

        <div className="relative z-10 px-8 py-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
          <div>
            <p className="text-sm font-semibold uppercase tracking-widest mb-2" style={{ color: "rgba(255,255,255,0.7)" }}>
              Comparador de precios · Chile
            </p>
            <h1
              className="price-display text-6xl sm:text-7xl text-white leading-none mb-3"
              style={{ fontFamily: "var(--font-bebas, Impact)" }}
            >
              MEJORES
              <br />
              <span style={{ color: "var(--poke-yellow)" }}>PRECIOS HOY</span>
            </h1>
            <p className="text-sm text-white/70 max-w-sm">
              Descuentos calculados contra el historial real de cada producto. Sin trampa de precio inflado.
            </p>
          </div>

          {/* Stats */}
          <div className="flex gap-6 flex-shrink-0">
            <StatBox label="Tiendas" value="6+" />
            <StatBox label="Ofertas" value={String(deals.length)} highlight />
            <StatBox label="Escaneo" value="c/6h" />
          </div>
        </div>
      </section>

      {/* Deal grid */}
      <section>
        <div className="flex items-center justify-between mb-5">
          <h2 className="section-label text-base">Ofertas del momento</h2>
          <Link href="/productos" className="text-xs font-semibold text-violet hover:underline">
            Ver catálogo →
          </Link>
        </div>

        {deals.length === 0 ? (
          <div className="rounded-xl border-2 border-dashed border-border-dim bg-white p-16 text-center">
            <p className="text-ink-2 font-medium">Sin ofertas reales todavía</p>
            <p className="text-ink-3 text-sm mt-1">El sistema acumula historial antes de declarar descuentos reales.</p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 stagger-grid">
            {deals.map((deal, i) => (
              <DealCard key={deal.listing.id} deal={deal} index={i} />
            ))}
          </div>
        )}
      </section>

      {/* Preventas */}
      {preorders.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <span
                className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide text-white"
                style={{ background: "var(--poke-red)" }}
              >
                Preventa
              </span>
              <h2 className="text-lg font-bold text-ink">Próximos lanzamientos</h2>
            </div>
            <Link href="/preventas" className="text-xs font-semibold text-violet hover:underline">
              Ver todas →
            </Link>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 stagger-grid">
            {preorders.slice(0, 8).map((p, i) => (
              <PreorderCard key={p.id} preorder={p} index={i} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

/* ── Components ── */

function DealCard({ deal, index }: { deal: Deal; index: number }) {
  const l = deal.listing;
  return (
    <div
      className="holo-card animate-fade-up bg-white rounded-xl border-2 border-border-dim flex flex-col overflow-hidden"
      style={{ animationDelay: `${(index % 8) * 50}ms` }}
    >
      {/* Yellow top stripe for discount */}
      <div className="h-1 w-full" style={{ background: `linear-gradient(90deg, var(--poke-yellow) ${deal.discount_pct}%, #eef1ff ${deal.discount_pct}%)` }} />

      {/* Image */}
      <div className="relative bg-base mx-3 mt-3 rounded-xl overflow-hidden flex items-center justify-center h-40">
        {l.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={l.image_url} alt={l.raw_name} className="h-full w-full object-contain p-2" />
        ) : (
          <span className="text-5xl">🃏</span>
        )}
        {/* Discount badge */}
        <span
          className="absolute top-2 right-2 rounded-lg px-2 py-0.5 text-sm font-bold price-display text-white"
          style={{ background: "var(--poke-red)", fontFamily: "var(--font-bebas, Impact)" }}
        >
          -{deal.discount_pct}%
        </span>
        {deal.is_historic_min && (
          <span
            className="absolute top-2 left-2 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase"
            style={{ background: "var(--poke-yellow)", color: "#1a1a3e" }}
          >
            Precio mín ↓
          </span>
        )}
      </div>

      {/* Info */}
      <div className="flex flex-col flex-1 p-4 gap-3">
        <div>
          <p className="text-sm font-semibold text-ink line-clamp-2 leading-snug">{l.raw_name}</p>
          <p className="text-xs text-ink-3 mt-0.5">{l.store_name}</p>
        </div>

        <div className="flex items-end justify-between mt-auto">
          <div>
            <span
              className="price-display text-2xl"
              style={{ fontFamily: "var(--font-bebas, Impact)", color: "var(--poke-blue)" }}
            >
              {formatCLP(deal.effective_price)}
            </span>
            <span className="ml-2 text-xs text-ink-3 line-through">{formatCLP(Math.round(deal.baseline_avg))}</span>
          </div>
        </div>

        <a
          href={l.url}
          target="_blank"
          rel="noopener noreferrer"
          className="block w-full rounded-lg py-2.5 text-center text-sm font-bold text-white transition-all hover:opacity-90"
          style={{ background: "var(--poke-blue)" }}
        >
          Ir a tienda →
        </a>
      </div>
    </div>
  );
}

function PreorderCard({ preorder: p, index }: { preorder: Preorder; index: number }) {
  const price = p.listing.current_sale_price ?? p.listing.current_price;
  return (
    <a
      href={p.listing.url}
      target="_blank"
      rel="noopener noreferrer"
      className="holo-card animate-fade-up bg-white rounded-xl border-2 border-border-dim flex gap-4 p-4 items-center"
      style={{ animationDelay: `${(index % 8) * 50}ms` }}
    >
      {p.listing.image_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={p.listing.image_url} alt={p.listing.raw_name} className="h-16 w-14 flex-shrink-0 rounded-lg object-contain bg-base" />
      ) : (
        <div className="h-16 w-14 flex-shrink-0 rounded-lg bg-base flex items-center justify-center text-xl">🃏</div>
      )}
      <div className="min-w-0">
        <span
          className="inline-block mb-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide text-white"
          style={{ background: "var(--poke-red)" }}
        >
          Preventa
        </span>
        <p className="text-sm font-semibold text-ink line-clamp-2 leading-snug">{p.listing.raw_name}</p>
        <p className="text-xs text-ink-3 mt-0.5">{p.listing.store_name}</p>
        <div className="flex items-center gap-2 mt-1">
          <span className="price-display text-lg" style={{ fontFamily: "var(--font-bebas, Impact)", color: "var(--poke-blue)" }}>
            {formatCLP(price)}
          </span>
          {p.release_date && (
            <span className="text-xs text-ink-3">
              {new Date(p.release_date).toLocaleDateString("es-CL")}
            </span>
          )}
        </div>
      </div>
    </a>
  );
}

function StatBox({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="text-center">
      <p
        className="price-display text-4xl sm:text-5xl"
        style={{ fontFamily: "var(--font-bebas, Impact)", color: highlight ? "var(--poke-yellow)" : "white" }}
      >
        {value}
      </p>
      <p className="text-xs uppercase tracking-widest text-white/60">{label}</p>
    </div>
  );
}
