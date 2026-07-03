import { api, formatCLP, type Preorder } from "@/lib/api";

export const revalidate = 300;

export default async function Preventas() {
  const preorders = await api.preorders().catch(() => [] as Preorder[]);
  const HIGH = preorders.filter((p) => p.confidence === "HIGH");
  const LOW = preorders.filter((p) => p.confidence !== "HIGH");

  return (
    <div className="space-y-10">
      {/* Header */}
      <div
        className="rounded-2xl overflow-hidden relative"
        style={{ background: "linear-gradient(135deg, var(--poke-red) 0%, #a80000 100%)" }}
      >
        {/* Pokéball decoration */}
        <div
          className="absolute right-0 top-0 w-64 h-64 rounded-full opacity-10 translate-x-12 -translate-y-12"
          style={{ border: "35px solid white" }}
        />
        <div className="relative z-10 px-8 py-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <p className="text-sm font-bold uppercase tracking-widest text-white/70 mb-2">Próximos lanzamientos</p>
            <h1
              className="price-display text-6xl sm:text-7xl text-white leading-none"
              style={{ fontFamily: "var(--font-bebas, Impact)" }}
            >
              PREVENTAS
            </h1>
            <p className="mt-2 text-sm text-white/70">
              {preorders.length} producto{preorders.length !== 1 ? "s" : ""} en preventa detectados
            </p>
          </div>
          <div className="flex gap-5 flex-shrink-0">
            <div className="text-center">
              <p className="price-display text-5xl text-white" style={{ fontFamily: "var(--font-bebas, Impact)" }}>{HIGH.length}</p>
              <p className="text-xs font-bold uppercase tracking-widest text-white/60">confirmados</p>
            </div>
            <div className="text-center">
              <p className="price-display text-5xl" style={{ fontFamily: "var(--font-bebas, Impact)", color: "var(--poke-yellow)" }}>{LOW.length}</p>
              <p className="text-xs font-bold uppercase tracking-widest text-white/60">posibles</p>
            </div>
          </div>
        </div>
      </div>

      {preorders.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-border-dim bg-white p-16 text-center">
          <p className="text-3xl mb-3">🃏</p>
          <p className="text-ink-2 font-semibold">Sin preventas activas por ahora</p>
          <p className="text-ink-3 text-sm mt-1">El scraper detecta preventas automáticamente en cada escaneo.</p>
        </div>
      ) : (
        <>
          {HIGH.length > 0 && (
            <section>
              <div className="flex items-center gap-3 mb-5">
                <span
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{ background: "var(--poke-red)", boxShadow: "0 0 0 3px rgba(204,0,0,0.15)" }}
                />
                <h2 className="font-bold text-ink">Fechas confirmadas</h2>
                <span className="text-xs text-ink-3 bg-white border border-border-dim rounded-full px-2 py-0.5">
                  {HIGH.length} producto{HIGH.length !== 1 ? "s" : ""}
                </span>
              </div>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 stagger-grid">
                {HIGH.map((p, i) => <PreorderCard key={p.id} preorder={p} index={i} />)}
              </div>
            </section>
          )}

          {LOW.length > 0 && (
            <section>
              <div className="flex items-center gap-3 mb-5">
                <span
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{ background: "var(--poke-yellow)", boxShadow: "0 0 0 3px rgba(255,222,0,0.2)" }}
                />
                <h2 className="font-bold text-ink">Posibles preventas</h2>
                <span className="text-xs text-ink-3 bg-white border border-border-dim rounded-full px-2 py-0.5">
                  detectadas por keywords
                </span>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 stagger-grid">
                {LOW.map((p, i) => <PreorderCard key={p.id} preorder={p} index={i} low />)}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}

function PreorderCard({ preorder: p, index, low }: { preorder: Preorder; index: number; low?: boolean }) {
  const price = p.listing.current_sale_price ?? p.listing.current_price;
  const accent = low ? "var(--poke-yellow)" : "var(--poke-red)";

  return (
    <div
      className="holo-card animate-fade-up bg-white rounded-xl border-2 border-border-dim flex flex-col overflow-hidden"
      style={{ animationDelay: `${(index % 8) * 50}ms` }}
    >
      {/* Top stripe */}
      <div className="h-1 w-full flex-shrink-0" style={{ background: accent }} />

      {/* Image */}
      <div className="relative bg-base mx-3 mt-3 rounded-xl h-40 flex items-center justify-center overflow-hidden">
        {p.listing.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={p.listing.image_url} alt={p.listing.raw_name} className="h-full w-full object-contain p-2" />
        ) : (
          <span className="text-5xl">🃏</span>
        )}
        <span
          className="absolute top-2 right-2 rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white"
          style={{ background: accent === "var(--poke-yellow)" ? "#b59800" : accent }}
        >
          {low ? "Posible" : "Preventa"}
        </span>
      </div>

      {/* Info */}
      <div className="flex flex-col flex-1 p-4 gap-3">
        <div>
          <p className="text-sm font-semibold text-ink line-clamp-2 leading-snug">{p.listing.raw_name}</p>
          <p className="text-xs text-ink-3 mt-0.5">{p.listing.store_name}</p>
          {p.release_date && (
            <p className="text-xs font-semibold mt-1" style={{ color: low ? "#b59800" : "var(--poke-red)" }}>
              📅 {new Date(p.release_date).toLocaleDateString("es-CL", {
                day: "numeric", month: "long", year: "numeric"
              })}
            </p>
          )}
        </div>

        <div className="mt-auto">
          <span
            className="price-display text-2xl"
            style={{ fontFamily: "var(--font-bebas, Impact)", color: "var(--poke-blue)" }}
          >
            {formatCLP(price)}
          </span>
        </div>

        <a
          href={p.listing.url}
          target="_blank"
          rel="noopener noreferrer"
          className="block w-full rounded-full py-2.5 text-center text-sm font-bold text-white transition-all hover:opacity-90"
          style={{ background: low ? "#b59800" : "var(--poke-red)" }}
        >
          Pre-ordenar →
        </a>
      </div>
    </div>
  );
}
