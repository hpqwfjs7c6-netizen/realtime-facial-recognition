# --- Étape de build ---
FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# NEXT_PUBLIC_* est figé au build : passer l'URL backend en build arg.
ARG NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
ENV NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL
RUN npm run build

# --- Étape de production (standalone) ---
FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
# Le serveur standalone doit écouter sur toutes les interfaces (pas localhost)
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
# Le serveur standalone tourne sous l'utilisateur non-root fourni par l'image node.
USER node
EXPOSE 3000
CMD ["node", "server.js"]
