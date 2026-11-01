# syntax=docker/dockerfile:1
FROM node:22.14.0-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=secret,id=host_ca,required=false \
    NODE_EXTRA_CA_CERTS=/run/secrets/host_ca npm ci

FROM dependencies AS test
COPY . .
RUN npm run test

FROM dependencies AS build
ARG VITE_GOOGLE_CLIENT_ID=
ENV VITE_GOOGLE_CLIENT_ID=${VITE_GOOGLE_CLIENT_ID}
COPY . .
RUN npm run build

FROM nginx:1.27.4-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
RUN chown -R nginx:nginx /usr/share/nginx/html \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid \
    && mkdir -p /var/cache/nginx/client_temp /var/cache/nginx/proxy_temp \
    && chown -R nginx:nginx /var/cache/nginx
USER nginx
EXPOSE 8080
CMD nginx -g 'daemon off;'
