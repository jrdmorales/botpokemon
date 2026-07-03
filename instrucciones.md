Actúa como un Arquitecto de Software Senior especializado en Python, Web Scraping, Automatización, Bases de Datos y Sistemas de Monitoreo de Precios.

Necesito desarrollar una plataforma completa para monitorear productos Pokémon en tiendas chilenas.

## Objetivo General

Crear un ecosistema compuesto por:

1. Bot de scraping de tiendas Pokémon chilenas.
2. Catálogo canónico de productos con matching entre tiendas.
3. Base de datos histórica de precios.
4. Sitio web comparador de precios.
5. Bot de Telegram para alertas de ofertas y preventas.

---

# Requerimientos Técnicos

## Stack

Backend:

* Python 3.12+
* FastAPI
* PostgreSQL 16
* SQLAlchemy 2.0 (async) como ORM
* Alembic para migraciones
* APScheduler para tareas programadas (escaneos periódicos)

Scraping:

* Playwright (solo para tiendas con JavaScript pesado)
* httpx + BeautifulSoup (preferido cuando la tienda sirve HTML estático — más liviano y rápido)
* Asyncio

Matching de productos:

* rapidfuzz para fuzzy matching de nombres
* Normalización por reglas (sets, ediciones, idioma)

Frontend:

* Next.js 15
* TypeScript
* TailwindCSS
* Recharts para gráficos

Notificaciones:

* Telegram Bot API (python-telegram-bot)

Contenedores:

* Docker
* Docker Compose

Observabilidad:

* Logging estructurado (structlog)
* Tabla de salud de scrapers + alertas internas vía Telegram al canal de administración

---

# Módulo 1: Scraping

El sistema debe rastrear múltiples tiendas chilenas dedicadas a productos Pokémon TCG en inglés y español.

## Tiendas iniciales (fase 1)

Definir adaptadores para 3-5 tiendas concretas al inicio. Candidatas a evaluar (verificar que permitan scraping razonable):

* Card Universe / tiendas TCG especializadas chilenas
* Tiendas generalistas con sección Pokémon (ej. Weplay, Microplay)
* La lista final se define tras inspeccionar cada sitio (estructura HTML, robots.txt, si exponen API/JSON interno)

Regla: antes de incorporar una tienda, detectar su plataforma (Shopify, WooCommerce, Vtex, custom). La plataforma determina el adaptador a usar — ver "Arquitectura de adaptadores".

## Categorías de producto

* cartas sueltas (singles) — fase posterior, alto volumen
* booster packs
* booster boxes
* ETB (Elite Trainer Box)
* collection boxes
* bundles
* tins
* accesorios Pokémon

## Arquitectura de adaptadores (por plataforma, NO por tienda)

No construir un scraper por tienda. Definir una interfaz `StoreAdapter` con método `fetch_products(category)` y tres implementaciones concretas según la plataforma detectada:

* **`ShopifyAdapter`** — usa `/collections/{handle}/products.json`, paginación `?page=N`, límite 250 productos por página
* **`WooCommerceAdapter`** — usa la Store API (`/wp-json/wc/store/v1/products`), paginación `?page=N&per_page=100`
* **`HtmlScraperAdapter`** — fallback con selectores CSS configurables; marcado explícitamente como "frágil" en código, docstrings y tests (es el único que se rompe cuando la tienda cambia su HTML)

Cada tienda se configura como **dato, no como código nuevo** — archivo YAML/JSON por tienda:

```yaml
nombre: tienda-ejemplo
base_url: https://tienda-ejemplo.cl
plataforma: shopify          # shopify | woocommerce | html
mapeo_categorias:
  etb: elite-trainer-boxes   # handle/slug/selector según plataforma
  booster_box: booster-boxes
# solo para plataforma html:
selectores:
  producto: ".product-card"
  nombre: ".product-title"
  precio: ".price"
```

Agregar una tienda Shopify o WooCommerce nueva = agregar un archivo de configuración, cero código. Solo las tiendas custom requieren configurar selectores para el `HtmlScraperAdapter`.

La detección estructurada de preventas y los topes de precio por categoría también se definen en la configuración de cada tienda.

## Datos a extraer

Por cada producto (listing de tienda):

* nombre (crudo, tal como aparece en la tienda)
* descripción
* categoría
* **idioma del producto (EN / ES / desconocido)** — campo obligatorio; producto en inglés y en español NO son el mismo ítem
* precio normal (entero, CLP — sin decimales)
* precio oferta (entero, CLP)
* moneda (explícita, default CLP)
* disponibilidad (en_stock / sin_stock / preventa)
* URL producto
* URL imagen
* SKU o ID interno de la tienda si existe (clave para detectar el mismo producto entre scrapes)
* tienda
* fecha extracción

### Parsing de precios — reglas obligatorias

Los precios chilenos usan punto como separador de miles ("$45.990" = 45990 CLP). El parser debe:

* Eliminar símbolos y separadores de miles, nunca interpretar punto como decimal
* Almacenar como entero (CLP no usa decimales)
* Rechazar valores absurdos: precio ≤ 0, precio > tope configurable por categoría (ej. un booster pack a $2.000.000 es error de parsing)
* Si precio_oferta > precio_normal, marcar el registro como sospechoso y no generar alerta

---

## Catálogo canónico y matching entre tiendas (CRÍTICO)

El comparador solo funciona si el sistema sabe que "ETB Scarlet & Violet 151" en la tienda A es el mismo producto que "Elite Trainer Box SV 151 Inglés" en la tienda B.

Modelo de dos niveles:

* **Producto canónico**: entidad maestra (set, tipo de producto, idioma, nombre normalizado)
* **Listing**: la publicación concreta de una tienda, vinculada a un producto canónico

Pipeline de matching:

1. Normalización del nombre crudo: minúsculas, quitar tildes, expandir abreviaciones conocidas (ETB → elite trainer box, SV → scarlet violet, etc.)
2. Extracción de atributos: set/expansión (mantener diccionario de sets de Pokémon TCG), tipo de producto, idioma
3. Match exacto por atributos extraídos; si falla, fuzzy matching (rapidfuzz) con umbral alto (≥ 92)
4. Matches con score intermedio (85-92) van a una **cola de revisión manual** (endpoint de administración + comando admin en Telegram para aprobar/rechazar)
5. Sin match: se crea producto canónico nuevo automáticamente

Nunca fusionar automáticamente productos de distinto idioma.

---

## Detección de ofertas

Calcular automáticamente:

* descuento porcentual **contra el promedio histórico propio de los últimos 30 días**, no solo contra el "precio normal" declarado por la tienda (las tiendas inflan el precio de lista para simular descuentos)
* descuento declarado por la tienda (se guarda, pero se etiqueta como "declarado")
* diferencia contra el mejor precio actual de la competencia (vía producto canónico)

Una oferta es "real" solo si el precio actual está bajo el promedio histórico propio.

---

## Detección de preventas

Detección en dos capas:

1. **Estructurada**: cada tienda suele marcar preventas de forma estructurada (tag de Shopify, categoría de WooCommerce, badge en HTML). La regla se define en la configuración YAML de la tienda y la interpreta el adaptador de su plataforma — es la señal confiable.
2. **Por keywords como respaldo**: "preventa", "pre-venta", "preorder", "reserva", "pre-order". Resultado de keywords se marca con confianza baja y pasa por la cola de revisión antes de generar alerta pública.

Guardar:

* fecha detección
* fecha lanzamiento si existe (extraer del texto cuando sea posible)
* condiciones de pago si existen (abono / pago completo)
* tienda

Ciclo de vida: cuando un producto pasa de preventa a stock regular, registrar la transición (no crear producto duplicado).

---

## Estados y ciclo de vida de listings

Distinguir explícitamente:

* `activo` — visible y comprable
* `sin_stock` — visible pero agotado (mantener en seguimiento, el precio histórico sigue siendo válido)
* `no_visto` — desapareció del catálogo; tras N scrapes consecutivos sin aparecer (configurable, ej. 4 = 24h), marcar `descontinuado`
* `descontinuado` — fuera de seguimiento activo; historial se conserva

Nunca borrar listings ni historial.

---

## Frecuencia

* Escaneo completo cada 6 horas
* Escaneo rápido de secciones de preventas/novedades cada 1 hora
* Orquestado con APScheduler dentro de un worker dedicado (contenedor separado del API)
* Jitter aleatorio en los horarios para no escanear todas las tiendas al mismo segundo

---

## Anti-bloqueo y cortesía (scraping responsable)

Las tiendas objetivo son comercios chilenos pequeños/medianos. Prioridad: no molestar, no evadir.

Implementar:

* Respetar robots.txt y términos de servicio de cada tienda
* Rate limit por dominio: máximo 1 request concurrente por tienda, delay aleatorio 2-5s entre requests
* User-Agent identificable y honesto (no suplantar navegadores si se usa httpx; incluir contacto)
* Retry con backoff exponencial (máx. 3 intentos); si la tienda responde 429/403, pausar esa tienda y alertar al admin
* Caché condicional (ETag / Last-Modified) cuando la tienda lo soporte

NO implementar rotación de proxies/IPs en fase inicial: contradice el objetivo de tráfico no agresivo y añade costo/complejidad. Si una tienda bloquea pese al rate limit cortés, evaluar contactarla o descartarla, no evadirla.

---

## Salud de scrapers (CRÍTICO)

Un scraper roto en silencio produce datos viejos y comparaciones falsas. Implementar:

* Tabla `scraper_runs`: tienda, inicio, fin, productos encontrados, errores, estado
* Alarma si un scrape devuelve 0 productos o una caída > 50% respecto al promedio de los últimos 7 días (probable cambio de HTML)
* Alarma si una tienda lleva > 24h sin scrape exitoso
* `last_successful_scrape` visible por tienda en el API y en el frontend ("datos actualizados hace X horas")
* El comparador debe excluir o marcar visualmente listings cuya tienda tenga datos viejos (> 12h)

---

# Módulo 2: Base de Datos

Diseñar modelo PostgreSQL con SQLAlchemy 2.0 + Alembic.

Tablas:

* `stores` — tiendas
* `canonical_products` — producto maestro (set, tipo, idioma, nombre normalizado)
* `listings` — publicación por tienda, FK a store y canonical_product (nullable hasta matching), SKU de tienda, estado de ciclo de vida
* `price_history` — cada cambio de precio: listing_id, precio_normal, precio_oferta, disponibilidad, timestamp. **Insertar solo cuando algo cambió** + un snapshot diario de checkpoint aunque no cambie (permite reconstruir series). Índice compuesto (listing_id, timestamp)
* `preorders` — preventas: listing_id, fecha detección, fecha lanzamiento, condiciones, estado, confianza
* `categories` — categorías
* `match_review_queue` — matches pendientes de revisión manual
* `scraper_runs` — salud de scrapers
* `alerts_sent` — alertas ya enviadas: tipo, listing_id, valor que la disparó, timestamp (para deduplicación)
* `telegram_users` — usuarios del bot y sus preferencias de alerta

Reglas:

* Nunca sobrescribir historial. Trazabilidad completa.
* Precios como `INTEGER` (CLP sin decimales) + columna `currency`.
* `price_history` crecerá: planificar particionamiento por rango de fecha desde el diseño (PostgreSQL native partitioning).

---

# Módulo 3: API

Crear API REST con FastAPI.

Endpoints públicos:

* `GET /products` — productos canónicos, con mejor precio actual agregado
* `GET /products/{id}` — detalle + listings de todas las tiendas
* `GET /stores` — incluye `last_successful_scrape`
* `GET /deals` — ofertas "reales" (bajo promedio histórico)
* `GET /preorders`
* `GET /price-history/{product_id}` — serie agregada por tienda

Filtros:

* tienda
* categoría
* idioma (EN/ES)
* rango de precios
* descuento mínimo (sobre promedio histórico)

Endpoints de administración (protegidos con API key):

* `GET/POST /admin/match-queue` — revisar y resolver matches pendientes
* `GET /admin/scraper-health`

Incluir paginación en todos los listados y rate limiting básico.

---

# Módulo 4: Comparador Web

Desarrollar una aplicación Next.js.

## Dashboard

Mostrar:

* mejores ofertas del día (ofertas "reales")
* nuevas preventas
* mayores descuentos vs promedio histórico
* productos recientemente bajados de precio

(Nota: "productos más vistos" requiere tracking de visitas — postergar a fase 2; si se implementa, registrar vistas en el API con un endpoint `POST /products/{id}/view` y agregación diaria.)

## Comparador

Al seleccionar un producto canónico, mostrar todas las tiendas que lo venden.

Tabla:

* tienda
* idioma del producto
* precio
* descuento real (vs histórico)
* stock
* frescura del dato ("actualizado hace 3h")
* link compra

Destacar automáticamente el mejor precio entre tiendas con datos frescos. Listings con datos viejos (> 12h) se muestran atenuados con advertencia.

## Historial

Gráficos con Recharts:

* evolución del precio por tienda (una serie por tienda)
* precio mínimo histórico
* precio máximo histórico
* promedio 30 días

## Página de Producto

Mostrar:

* imagen (servida vía proxy/caché propio — no hotlinkear directo a la tienda: las URLs se rompen y algunas tiendas bloquean hotlinking)
* nombre, idioma, set
* descripción
* mejor precio actual
* historial
* ofertas disponibles
* enlaces de compra a cada tienda

---

# Módulo 5: Telegram

Crear bot de Telegram.

Comandos:

* `/ofertas` — ofertas reales del día
* `/preventas` — preventas activas
* `/mejores` — mayores descuentos vs histórico
* `/buscar <texto>` — busca en productos canónicos
* `/alertas` — configurar preferencias: categorías de interés, idioma (EN/ES/ambos), descuento mínimo para notificar

## Alertas Automáticas

Enviar mensaje cuando:

* aparezca una nueva preventa (solo confianza alta; las de keywords esperan revisión)
* exista un descuento > 20% **sobre el promedio histórico propio** (no sobre el precio declarado por la tienda)
* un producto alcance su mínimo histórico — **solo si tiene ≥ 14 días de historial** (sin esta regla, el día 1 todo producto está en "mínimo histórico" y el bot spamea)

### Deduplicación de alertas (obligatorio)

Antes de enviar, consultar `alerts_sent`: no re-alertar el mismo evento (mismo listing, mismo tipo, mismo precio) — sin esto, cada escaneo de 6h repite todas las alertas. Re-alertar solo si el precio bajó aún más respecto a la última alerta enviada.

Respetar las preferencias del usuario (`/alertas`). Respetar rate limits de la API de Telegram (cola de envío con throttling).

Formato del mensaje:

* Nombre producto + idioma
* Tienda
* Precio (y precio anterior)
* Descuento real
* Link compra

---

# Arquitectura

Genera:

1. estructura completa de carpetas (monorepo: `backend/`, `scraper/`, `frontend/`, `bot/`, `docker/`)
2. modelos SQLAlchemy + migraciones Alembic
3. interfaz `StoreAdapter` + los tres adaptadores por plataforma (Shopify, WooCommerce, HTML fallback) + esquema de configuración YAML por tienda con validación (pydantic)
4. servicio de matching/normalización con tests
5. servicios de scraping con manejo de salud y rate limiting
6. API FastAPI
7. frontend Next.js
8. integración Telegram (comandos + worker de alertas)
9. Docker Compose (servicios: postgres, api, scraper-worker, bot, frontend)
10. variables de entorno (`.env.example` documentado)
11. roadmap de implementación por fases:
    * Fase 1: BD + `ShopifyAdapter` + 1 tienda configurada + matching básico + API mínima
    * Fase 2: `WooCommerceAdapter` + `HtmlScraperAdapter` + 3-5 tiendas configuradas + frontend comparador + salud de scrapers
    * Fase 3: Telegram + alertas + preventas
    * Fase 4: singles (cartas sueltas), analytics de vistas

Priorizar código mantenible, escalable y preparado para producción.

Incluir tests para: parsing de precios chilenos, normalización/matching de nombres, deduplicación de alertas.

Incluir ejemplos completos de código para cada módulo.
