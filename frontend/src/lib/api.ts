// NEXT_PUBLIC_API_URL: URL que usa el BROWSER (client-side)
// API_INTERNAL_URL: URL que usa Next.js en SSR dentro de Docker (server-side)
// Si no está definida la interna, cae a la pública.
const API_URL =
  (typeof window === "undefined"
    ? process.env.API_INTERNAL_URL
    : process.env.NEXT_PUBLIC_API_URL) ?? "http://localhost:8000";

export interface Listing {
  id: number;
  store_id: number;
  store_name: string;
  raw_name: string;
  language: string;
  url: string;
  image_url: string | null;
  status: string;
  current_price: number | null;
  current_sale_price: number | null;
  currency: string;
  last_seen_at: string | null;
  is_stale: boolean;
}

export interface Product {
  id: number;
  display_name: string;
  set_code: string | null;
  product_type: string | null;
  language: string;
  image_url: string | null;
  best_price: number | null;
  best_price_store: string | null;
}

export interface ProductDetail extends Product {
  listings: Listing[];
}

export interface Deal {
  listing: Listing;
  effective_price: number;
  baseline_avg: number;
  discount_pct: number;
  is_historic_min: boolean;
}

export interface Preorder {
  id: number;
  listing: Listing;
  detected_at: string;
  release_date: string | null;
  confidence: string;
}

export interface PricePoint {
  price: number;
  sale_price: number | null;
  availability: string;
  recorded_at: string;
}

export interface PriceSeries {
  store_name: string;
  listing_id: number;
  points: PricePoint[];
  min_price: number | null;
  max_price: number | null;
  avg_price: number | null;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
}

async function get<T>(path: string): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const res = await fetch(`${API_URL}${path}`, {
      next: { revalidate: 300 },
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
    return res.json();
  } finally {
    clearTimeout(timeout);
  }
}

export const api = {
  products: (params = "") => get<Paginated<Product>>(`/products?${params}`),
  product: (id: number) => get<ProductDetail>(`/products/${id}`),
  deals: (params = "") => get<Deal[]>(`/deals?${params}`),
  preorders: () => get<Preorder[]>(`/preorders`),
  priceHistory: (productId: number) => get<PriceSeries[]>(`/price-history/${productId}`),
};

export function formatCLP(value: number | null): string {
  if (value === null) return "—";
  return `$${value.toLocaleString("es-CL")}`;
}
