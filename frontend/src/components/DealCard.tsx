import { Deal, formatCLP } from "@/lib/api";

export function DealCard({ deal, index = 0 }: { deal: Deal; index?: number }) {
  const l = deal.listing;
  const effectiveDelay = `${index * 60}ms`;

  return (
    <a
      href={l.url}
      target="_blank"
      rel="noopener noreferrer"
      className={`holo-card animate-fade-up block rounded-xl border border-border-dim bg-surface p-5 ${
        l.is_stale ? "opacity-40 grayscale" : ""
      }`}
      style={{
        animationDelay: effectiveDelay,
        background: "linear-gradient(145deg, #0d0d1e 0%, #0a0a18 100%)",
      }}
    >
      {/* Holo border top accent */}
      <div
        className="absolute inset-x-0 top-0 h-px rounded-t-xl opacity-60"
        style={{
          background:
            "linear-gradient(90deg, transparent, rgba(124,58,237,0.6), rgba(0,196,238,0.4), transparent)",
        }}
      />

      <div className="relative z-10 flex gap-4">
        {/* Image */}
        {l.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={l.image_url}
            alt={l.raw_name}
            className="h-24 w-20 flex-shrink-0 rounded-lg object-contain"
            style={{ background: "rgba(255,255,255,0.03)" }}
          />
        ) : (
          <div className="h-24 w-20 flex-shrink-0 rounded-lg bg-elevated flex items-center justify-center text-ink-3 text-2xl">
            🃏
          </div>
        )}

        <div className="min-w-0 flex-1 flex flex-col justify-between">
          {/* Header */}
          <div>
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-medium text-ink leading-snug line-clamp-2">{l.raw_name}</p>
              {deal.is_historic_min && (
                <span className="flex-shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold tracking-wide uppercase text-warn bg-warn/10 border border-warn/20">
                  Mín ↓
                </span>
              )}
            </div>
            <p className="mt-1 text-xs text-ink-2">
              {l.store_name}
              <span className="mx-1.5 text-ink-3">·</span>
              <span className="text-ink-3">{l.language}</span>
              {l.is_stale && (
                <span className="ml-1.5 text-warn/60 text-[10px]">dato antiguo</span>
              )}
            </p>
          </div>

          {/* Price */}
          <div className="flex items-end justify-between mt-3">
            <div>
              <span
                className="price-display text-3xl text-holo"
                style={{ fontFamily: "var(--font-bebas, Impact)" }}
              >
                {formatCLP(deal.effective_price)}
              </span>
              <span className="ml-2 text-xs text-ink-3 line-through">
                {formatCLP(Math.round(deal.baseline_avg))}
              </span>
            </div>
            <span
              className="rounded-md px-2.5 py-1 text-sm font-bold tabular-nums"
              style={{
                background: "rgba(0,255,135,0.12)",
                color: "#00ff87",
                border: "1px solid rgba(0,255,135,0.2)",
                fontFamily: "var(--font-bebas, Impact)",
                letterSpacing: "0.05em",
              }}
            >
              -{deal.discount_pct}%
            </span>
          </div>
        </div>
      </div>
    </a>
  );
}
