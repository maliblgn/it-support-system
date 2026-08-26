# syntax=docker/dockerfile:1.7

FROM node:22-alpine AS build

WORKDIR /app

ARG VITE_APP_NAME="Destek Takip"
ARG VITE_PUBLIC_REGISTRATION_ENABLED="false"
ENV VITE_APP_NAME=$VITE_APP_NAME \
    VITE_PUBLIC_REGISTRATION_ENABLED=$VITE_PUBLIC_REGISTRATION_ENABLED

COPY package.json package-lock.json ./
RUN npm ci

COPY index.html vite.config.js ./
COPY public ./public
COPY src ./src
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.28-alpine

COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["wget", "-qO-", "http://127.0.0.1:8080/healthz"]
