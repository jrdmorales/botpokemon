import Link from "next/link";
import { api, formatCLP } from "@/lib/api";

export const revalidate = 300;

const LANGS = [
  { value: "", label: "Todos" },
  { value: "EN", label: "🇺🇸 Inglés" },
  { value: "ES", label: "🇪🇸 Español" },
];

export default async function Productos({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; language?: string; page?: string }>;
}) {
  const params = await searchParams;
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.language) query.set("language", params.language);
  query.set("page", params.page ?? "1");
  query.set("per_page", "24");

  const data = await api.products(query.toString()).catch(() => null);
  const page = Number(params.page ?? "1");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <p className="section-label mb-2">Catálogo completo</p>
          <h1
            className="price-display text-5xl text-ink"
            style={{ fontFamily: "var(--font-bebas, Impact)" }}
          >
            TODOS LOS PRODUCTOS
          </h1>
        </div>
        {data && (
          <span className="text-sm text-ink-2 bg-white border border-border-dim rounded-full px-3 py-1 flex-shrink-0">
            {data.total} productos
          </span>
        )}
      </div>

      {/* Filter bar */}
      <form
        action="/productos"
        className="flex flex-wrap gap-3 p-4 rounded-xl border-2 border-border-dim bg-white items-end"
      >
        <div className="flex-1 min-w-48">
          <label className="block text-xs font-bold text-ink-2 uppercase tracking-wider mb-1.5">Buscar</label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-3 pointer-events-none">⌕</span>
            <input
              name="q"
              defaultValue={params.q ?? ""}
              placeholder="ETB, Booster Box, Tin…"
              className="w-full rounded-full border-2 border-border-dim bg-base pl-8 pr-4 py-2 text-sm text-ink placeholder:text-ink-3 focus:outline-none focus:border-violet transition-colors"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-bold text-ink-2 uppercase tracking-wider mb-1.5">Idioma</label>
          <div className="flex rounded-full overflow-hidden border-2 border-border-dim">
            {LANGS.map((l) => (
              <label key={l.value} className="relative cursor-pointer">
                <input
                  type="radio"
                  name="language"
                  value={l.value}
                  defaultChecked={(params.language ?? "") === l.value}
                  className="sr-only peer"
                />
                <span className="block px-4 py-2 text-xs font-semibold text-ink-2 bg-base peer-checked:bg-violet peer-checked:text-white transition-all select-none">
                  {l.label}
                </span>
              </label>
            ))}
          </div>
        </div>

        <button
          type="submit"
          className="rounded-full px-6 py-2 text-sm font-bold text-white transition-all hover:opacity-90"
          style={{ background: "var(--poke-blue)" }}
        >
          Filtrar
        </button>

        {(params.q || params.language) && (
          <Link
            href="/productos"
            className="rounded-full px-4 py-2 text-sm font-semibold text-ink-2 hover:text-ink border-2 border-border-dim hover:border-violet transition-all"
          >
            × Limpiar
          </Link>
        )}
      </form>

      {/* Grid */}
      {!data || data.items.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-border-dim bg-white p-16 text-center">
          <p className="text-2xl mb-2">🔍</p>
          <p className="text-ink-2 font-semibold">Sin resultados</p>
          <p className="text-ink-3 text-sm mt-1">Intenta con otro término de búsqueda.</p>
          <Link href="/productos" className="mt-4 inline-block text-sm font-semibold text-violet hover:underline">
            Ver todo el catálogo
          </Link>
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 stagger-grid">
            {data.items.map((p, i) => (
              <Link
                key={p.id}
                href={`/producto/${p.id}`}
                className="holo-card animate-fade-up bg-white rounded-xl border-2 border-border-dim flex flex-col overflow-hidden group"
                style={{ animationDelay: `${(i % 12) * 40}ms` }}
              >
                {/* Top stripe */}
                <div className="h-1 w-full" style={{ background: "var(--poke-yellow)" }} />

                {/* Image */}
                <div className="relative bg-base mx-3 mt-3 rounded-xl h-40 flex items-center justify-center overflow-hidden">
                  {p.image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={p.image_url} alt={p.display_name} className="h-full w-full object-contain p-2" />
                  ) : (
                    <span className="text-5xl">🃏</span>
                  )}
                  <span
                    className="absolute top-2 left-2 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide"
                    style={{ background: "rgba(59,76,202,0.1)", color: "var(--poke-blue)" }}
                  >
                    {p.language}
                  </span>
                </div>

                {/* Info */}
                <div className="flex flex-col flex-1 p-4 gap-2">
                  <p className="text-sm font-semibold text-ink line-clamp-2 leading-snug">{p.display_name}</p>
                  {p.set_code && <p className="text-xs text-ink-3">{p.set_code}</p>}

                  <div className="mt-auto pt-2 border-t border-border-dim flex items-center justify-between">
                    <div>
                      {p.best_price ? (
                        <>
                          <p className="text-[10px] font-bold text-ink-3 uppercase tracking-wide">desde</p>
                          <span
                            className="price-display text-2xl"
                            style={{ fontFamily: "var(--font-bebas, Impact)", color: "var(--poke-blue)" }}
                          >
                            {formatCLP(p.best_price)}
                          </span>
                        </>
                      ) : (
                        <span className="text-sm font-semibold text-ink-3">Sin stock</span>
                      )}
                    </div>
                    <span
                      className="text-xs font-bold rounded-full px-3 py-1 text-white group-hover:opacity-100 transition-all"
                      style={{ background: "var(--poke-blue)" }}
                    >
                      Ver →
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {/* Pagination */}
          <div className="flex justify-center items-center gap-3 pt-4">
            {page > 1 && (
              <Link
                href={`/productos?${new URLSearchParams({ ...params, page: String(page - 1) })}`}
                className="rounded-full border-2 border-border-dim px-5 py-2 text-sm font-semibold text-ink-2 hover:text-violet hover:border-violet transition-all"
              >
                ← Anterior
              </Link>
            )}
            <span className="text-sm text-ink-3">Pág. {page} · {data.total} total</span>
            {page * data.per_page < data.total && (
              <Link
                href={`/productos?${new URLSearchParams({ ...params, page: String(page + 1) })}`}
                className="rounded-full border-2 border-border-dim px-5 py-2 text-sm font-semibold text-ink-2 hover:text-violet hover:border-violet transition-all"
              >
                Siguiente →
              </Link>
            )}
          </div>
        </>
      )}
    </div>
  );
}
