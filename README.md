# PokePrecio — Monitor de precios Pokémon TCG Chile

Plataforma para monitorear productos Pokémon en tiendas chilenas: scraping
respetuoso, catálogo canónico con matching entre tiendas, historial de precios,
comparador web y bot de Telegram con alertas.

## Arquitectura

```
backend/    FastAPI + SQLAlchemy 2.0 + APScheduler + python-telegram-bot
  app/
    scraping/   Adaptadores por PLATAFORMA (Shopify, WooCommerce, HTML frágil)
    matching/   Normalización + fuzzy matching → catálogo canónico
    services/   Ofertas reales (vs promedio histórico) + alertas deduplicadas
    api/        Endpoints públicos + admin (cola de revisión, salud)
    telegram/   Bot de comandos + notificador con throttling
    worker.py   Scheduler: escaneo completo 6h, preventas 1h
  stores/     Configuración YAML por tienda (agregar tienda = agregar archivo)
  tests/      Parser CLP, matching, deduplicación de alertas
frontend/   Next.js 15 + Tailwind + Recharts (dashboard, comparador, historial)
```

## Levantar todo con Docker

```bash
cp .env.example .env   # editar credenciales
docker compose up --build
```

- API: http://localhost:8000/docs
- Web: http://localhost:3000

## Desarrollo local (sin Docker)

```bash
# Backend
cd backend
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -e ".[dev]"
alembic revision --autogenerate -m "initial" && alembic upgrade head
uvicorn app.api.main:app --reload      # API
python -m app.worker                   # worker de scraping
python -m app.telegram.bot             # bot

# Frontend
cd frontend
npm install && npm run dev

# Tests
cd backend && python -m pytest
```

## Agregar una tienda

1. Detectar plataforma: `curl https://latienda.cl/collections/all/products.json`
   responde JSON → Shopify. `/wp-json/wc/store/v1/products` responde → WooCommerce.
2. Copiar `backend/stores/ejemplo-shopify.yaml`, ajustar slug, URL y mapeo de
   categorías. Cero código.
3. Solo tiendas custom requieren `plataforma: html` + selectores CSS
   (ver `ejemplo-html.yaml.disabled`) — ese adaptador es frágil por diseño:
   vigilar las alarmas de salud en el canal admin de Telegram.

## Decisiones de diseño clave

- **Descuento real ≠ descuento declarado**: las alertas usan el promedio
  histórico propio (30 días), no el precio de lista de la tienda.
- **Mínimo histórico requiere ≥14 días de historial** — evita spam el día 1.
- **Deduplicación de alertas** (`alerts_sent`): solo se re-alerta si el precio
  bajó más que la última alerta.
- **Scraping cortés**: 1 request concurrente por tienda, delays 2-5s,
  User-Agent identificable, sin proxies. Si una tienda responde 403/429 se
  pausa y se avisa al admin — no se evade.
- **Historial inmutable**: `price_history` solo inserta (cambios + checkpoint
  diario). Nunca update/delete.
