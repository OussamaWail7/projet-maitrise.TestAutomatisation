# Frontend Dockerfile - Build multi-stage
FROM node:18-alpine AS builder

WORKDIR /app

# Copier les fichiers de dépendances
COPY package*.json ./

# Installer les dépendances
RUN npm ci --legacy-peer-deps

# Copier le code source
COPY . .

# Build de production
RUN npm run build

# Stage de production avec nginx
FROM nginx:alpine

# Copier le build
COPY --from=builder /app/dist /usr/share/nginx/html

# Copier la configuration nginx personnalisée
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Exposer le port
EXPOSE 80

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Démarrer nginx
CMD ["nginx", "-g", "daemon off;"]
