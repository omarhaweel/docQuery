FROM nginx:alpine
ARG BACKEND_URL=http://127.0.0.1:8000
COPY frontend/index.html /tmp/index.html
RUN sed -i "s|__BACKEND_URL__|${BACKEND_URL}|g" /tmp/index.html && mv /tmp/index.html /usr/share/nginx/html/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
