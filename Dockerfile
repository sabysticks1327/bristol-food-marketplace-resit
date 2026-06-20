# Docker setup will be completed during Django setup
FROM python:3.11-slim

WORKDIR /app

COPY . /app

CMD ["echo", "Docker skeleton ready"]