FROM nginxinc/nginx-unprivileged:1.27-alpine

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY index.html styles.css /usr/share/nginx/html/
COPY src /usr/share/nginx/html/src

ENV API_URL=http://api:8000 PORT=8080
EXPOSE 8080
HEALTHCHECK --interval=5s --timeout=3s --retries=10 \
  CMD wget -q --spider http://127.0.0.1:8080/ || exit 1
