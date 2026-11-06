# Development image: runs the Vite dev server. Source is bind-mounted by compose.yaml.
FROM docker.io/library/node:24-slim

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
