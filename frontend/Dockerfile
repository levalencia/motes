# Frontend Dockerfile for Motes
FROM node:22-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ .
RUN npm run build

FROM node:22-alpine

WORKDIR /app
COPY --from=build /app/build ./build
COPY --from=build /app/package.json .

EXPOSE 3000

CMD ["node", "build"]
