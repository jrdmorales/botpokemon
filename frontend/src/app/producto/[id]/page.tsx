import { api, formatCLP, Listing } from "@/lib/api";
import { PriceChart } from "@/components/PriceChart";
import { notFound } from "next/navigation";
import Link from "next/link";

export const revalidate = 300;

export default async function ProductoPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const productId = Number(id);
  if (Number.isNaN(productId)) notFound();

  const [product, history] = await Promise.all([
    api.product(productId).catch(() => null),
    api.priceHistory(productId).catch(() => []),
  ]);
  if (!product) notFound();

  const fresh = product.listings.filter(
    (l) => !l.is_stale && l.status === "activo" && (l.current_sale_price ?? l.current_price)
  );
  const bestPrice =
    fresh.length > 0
      ? Math.min(...fresh.map((l) => l.current_sale_price ?? l.current_price ?? Infinity))
      : null;
  const bestStore = fresh.find(
    (l) => (l.current_sale_price ?? l.current_price) === bestPrice
  );

  const allMin = history.flatMap((s) => (s.min_price !== null ? [s.min_price] : []));
  const allMax = history.flatMap((s) => (s.max_price !== null ? [s.max_price] : []));
  const allAvg = history.flatMap((s) => (s.avg_price !== null ? [s.avg_price] : []));
  const historicMin = allMin.length > 0 ? Math.min(...allMin) : null;
  const historicMax = allMax.length > 0 ? Math.max(...allMax) : null;
  const historicAvg =
    allAvg.length > 0 ? Math.round(allAvg.reduce((a, b) => a + b, 0) / allAvg.length) : null;

  const sorted = [...product.listings].sort(
    (a, b) =>
      (a.current_sale_price ?? a.current_price ?? Infinity) -
      (b.current_sale_price ?? b.current_price ?? Infinity)
  );

  return (
    <div className="space-y-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-xs text-ink-3">
        <Link href="/" className="hover:text-violet transition-colors font-medium">Ofertas</Link>
        <span>/</span>
        <Link href="/productos" className="hover:text-violet transition-colors font-medium">Catálogo</Link>
        <span>/</span>
        <span className="text-ink-2 line-clamp-1">{product.display_name}</span>
      </nav>

      {/* Product hero */}
      <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr_260px] gap-6 items-start">
        {/* Image */}
        <div className="bg-white rounded-2xl border-2 border-border-dim flex items-center justify-center h-56 overflow-hidden">
          {product.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={product.image_url} alt={product.display_name} className="h-full w-full object-contain p-4" />
          ) : (
            <span className="text-7xl">🃏</span>
          )}
        </div>

        {/* Info */}
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Badge>{product.language}</Badge>
            {product.set_code && <Badge accent>{product.set_code}</Badge>}
            {product.product_type && <Badge>{product.product_type}</Badge>}
          </div>

          <h1 className="text-2xl sm:text-3xl font-bold text-ink leading-tight">
            {product.display_name}
          </h1>

          <p className="text-sm text-ink-2">
            {product.listings.length} tienda{product.listings.length !== 1 ? "s" : ""} monitoreada{product.listings.length !== 1 ? "s" : ""}
            {fresh.length > 0 && (
              <> · <span className="font-semibold text-holo">{fresh.length} con stock</span></>
            )}
          </p>

          {/* Historic stats */}
          {historicMin !== null && (
            <div className="flex flex-wrap gap-3 pt-2">
              <StatPill label="Mín. histórico" value={formatCLP(historicMin)} color="#16a34a" />
              <StatPill label="Máx. histórico" value={formatCLP(historicMax)} color="#dc2626" />
              <StatPill label="Promedio 30d" value={formatCLP(historicAvg)} color="#4a5270" />
            </div>
          )}
        </div>

        {/* Price box */}
        {bestPrice && bestStore ? (
          <div className="bg-white rounded-2xl border-2 border-border-dim overflow-hidden">
            <div className="h-1 w-full" style={{ background: "var(--poke-yellow)" }} />
            <div className="p-5 flex flex-col gap-4">
              <div>
                <p className="text-xs font-bold text-ink-3 uppercase tracking-widest mb-1">Mejor precio actual</p>
                <span
                  className="price-display text-4xl block"
                  style={{ fontFamily: "var(--font-bebas, Impact)", color: "var(--poke-blue)" }}
                >
                  {formatCLP(bestPrice)}
                </span>
                <p className="text-xs text-ink-3 mt-1">{bestStore.store_name}</p>
              </div>
              <a
                href={bestStore.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block w-full rounded-full py-3 text-center text-sm font-bold text-white transition-all hover:opacity-90"
                style={{ background: "var(--poke-blue)" }}
              >
                Comprar ahora →
              </a>
              {fresh.length > 1 && (
                <p className="text-xs text-ink-3 text-center">
                  +{fresh.length - 1} tienda{fresh.length > 2 ? "s" : ""} con stock disponible
                </p>
              )}
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border-2 border-dashed border-border-dim p-5 text-center">
            <p className="text-ink-2 font-semibold text-sm">Sin stock fresco</p>
            <p className="text-ink-3 text-xs mt-1">Dato desactualizado o agotado</p>
          </div>
        )}
      </div>

      {/* Store comparison */}
      <section>
        <p className="section-label mb-4">Comparar tiendas</p>
        <div className="bg-white rounded-2xl border-2 border-border-dim overflow-hidden">
          <table className="data-table">
            <thead>
              <tr>
                <th>Tienda</th>
                <th>Precio</th>
                <th>Estado</th>
                <th className="hidden sm:table-cell">Actualizado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((l) => {
                const price = l.current_sale_price ?? l.current_price;
                const isBest = !l.is_stale && l.status === "activo" && price === bestPrice;
                return <StoreRow key={l.id} listing={l} price={price} isBest={isBest} />;
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Chart */}
      {history.length > 0 && (
        <section>
          <p className="section-label mb-4">Historial de precios</p>
          <div className="bg-white rounded-2xl border-2 border-border-dim p-5">
            <PriceChart series={history} />
          </div>
        </section>
      )}
    </div>
  );
}

function Badge({ children, accent }: { children: React.ReactNode; accent?: boolean }) {
  return (
    <span
      className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider"
      style={{
        background: accent ? "rgba(59,76,202,0.1)" : "#eef1ff",
        color: accent ? "var(--poke-blue)" : "#4a5270",
        border: accent ? "1px solid rgba(59,76,202,0.2)" : "1px solid #dde3f0",
      }}
    >
      {children}
    </span>
  );
}

function StatPill({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="rounded-xl border-2 border-border-dim bg-base px-4 py-2.5 flex-shrink-0">
      <p className="text-[10px] font-bold text-ink-3 uppercase tracking-widest mb-0.5">{label}</p>
      <p className="price-display text-lg" style={{ fontFamily: "var(--font-bebas, Impact)", color }}>
        {value}
      </p>
    </div>
  );
}

function StoreRow({ listing: l, price, isBest }: { listing: Listing; price: number | null; isBest: boolean }) {
  return (
    <tr style={{ opacity: l.is_stale ? 0.5 : 1, background: isBest ? "rgba(59,76,202,0.04)" : undefined }}>
      <td>
        <div className="flex items-center gap-2">
          <span className="font-semibold text-ink">{l.store_name}</span>
          {isBest && (
            <span
              className="text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full text-white"
              style={{ background: "var(--poke-blue)" }}
            >
              Mejor precio
            </span>
          )}
        </div>
      </td>
      <td>
        <div className="flex items-baseline gap-2">
          <span
            className="price-display text-xl"
            style={{ fontFamily: "var(--font-bebas, Impact)", color: isBest ? "var(--poke-blue)" : "#1a1a3e" }}
          >
            {formatCLP(price)}
          </span>
          {l.current_sale_price && l.current_price && (
            <span className="text-xs text-ink-3 line-through">{formatCLP(l.current_price)}</span>
          )}
        </div>
      </td>
      <td><StatusBadge status={l.status} /></td>
      <td className="hidden sm:table-cell text-xs text-ink-2 tabular-nums">
        {l.last_seen_at ? new Date(l.last_seen_at).toLocaleString("es-CL") : "—"}
        {l.is_stale && <span className="ml-1 text-warn text-[10px]">⚠ antiguo</span>}
      </td>
      <td>
        <a
          href={l.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-xs font-bold text-white transition-all hover:opacity-80 whitespace-nowrap"
          style={{ background: isBest ? "var(--poke-blue)" : "#4a5270" }}
        >
          Comprar →
        </a>
      </td>
    </tr>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; color: string; bg: string }> = {
    activo: { label: "En stock", color: "#16a34a", bg: "#dcfce7" },
    sin_stock: { label: "Agotado", color: "#dc2626", bg: "#fee2e2" },
    preventa: { label: "Preventa", color: "#0369a1", bg: "#e0f2fe" },
    no_visto: { label: "No disponible", color: "#64748b", bg: "#f1f5f9" },
    descontinuado: { label: "Discontinuado", color: "#64748b", bg: "#f1f5f9" },
  };
  const s = map[status] ?? { label: status, color: "#64748b", bg: "#f1f5f9" };
  return (
    <span
      className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide px-2.5 py-1 rounded-full"
      style={{ color: s.color, background: s.bg }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: s.color }} />
      {s.label}
    </span>
  );
}
