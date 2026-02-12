# Despliegue — Facturador

## Estructura

```
docker-compose.yml          # Base: servicios comunes (postgres, redis, api, worker)
docker-compose.dev.yml      # Override DEV: puertos, hot reload, volúmenes de código
docker-compose.prod.yml     # Override PROD: nginx estático, proxy_net, restart policies
```

## Desarrollo (DEV)

```bash
# Primer inicio
cp .env.example .env
make up-build               # equivale a: docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
make migrate
make seed

# Uso diario
make up                     # levantar
make down                   # apagar
make logs                   # ver logs
make test                   # correr tests
```

**Puertos expuestos en DEV:**
| Servicio   | Puerto |
|-----------|--------|
| Frontend  | 5173   |
| API       | 5003   |
| PostgreSQL| 5432   |
| Redis     | 6379   |

El frontend corre como dev server de Vite con hot reload. El código fuente se monta como volumen para que los cambios se reflejen en tiempo real.

## Producción (PROD)

### Requisitos previos

1. Red externa `proxy_net` creada (compartida con Nginx Proxy Manager u otro reverse proxy):
   ```bash
   docker network create proxy_net
   ```

2. Archivo `.env` con valores de producción:
   ```bash
   cp .env.example .env
   # Editar .env con valores reales:
   #   SECRET_KEY, JWT_SECRET_KEY — claves seguras
   #   POSTGRES_PASSWORD — password fuerte
   #   ENCRYPTION_KEY — exactamente 32 caracteres
   #   ARCA_AMBIENTE=production
   #   CORS_ORIGINS=https://facturador.tudominio.com
   ```

### Levantar

```bash
make up-build ENV=prod
make migrate ENV=prod
make seed ENV=prod          # solo la primera vez
```

### Containers en PROD

| Container              | Red interna | Red proxy_net | Puerto interno |
|------------------------|:-----------:|:-------------:|:--------------:|
| facturador_api         |     si      |      si       |     5000       |
| facturador_frontend    |     si      |      si       |       80       |
| facturador_worker      |     si      |      no       |      —         |
| postgres               |     si      |      no       |     5432       |
| redis                  |     si      |      no       |     6379       |

**Ningún puerto se expone al host en producción.** El acceso es a través del reverse proxy conectado a `proxy_net`.

### Configuración del Reverse Proxy (Nginx Proxy Manager)

Crear dos proxy hosts apuntando a la red `proxy_net`:

1. **Frontend:** `facturador.tudominio.com` → `facturador_frontend:80`
2. **API (si se necesita acceso directo):** `api.facturador.tudominio.com` → `facturador_api:5000`

> El frontend ya proxea `/api/*` al backend internamente via nginx, por lo que normalmente solo se necesita el proxy host del frontend.

## Comandos útiles

```bash
# DEV (default)
make up-build                   # build + start
make test                       # tests del backend
make pre-push                   # tests + lint + build frontend
make shell-api                  # bash en el container API
make db-shell                   # psql

# PROD
make up-build ENV=prod          # build + start en prod
make logs ENV=prod              # logs de producción
make ps ENV=prod                # estado de los containers
make restart ENV=prod           # reiniciar servicios
```

## Volúmenes

- `facturador_postgres_data` — datos persistentes de PostgreSQL (no se elimina con `make down`)
- Para reiniciar la base de datos: `make reset` (ELIMINA todos los datos)
