FROM node:24-alpine
WORKDIR /app
COPY package.json ./
COPY package-lock.json ./
RUN npm ci --omit=dev
COPY src ./src
EXPOSE 4000
USER node
CMD ["node", "src/server.js"]
