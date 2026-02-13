FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm config set strict-ssl false && npm install

COPY . .

EXPOSE 4000

CMD ["npx", "tsx", "watch", "src/index.ts"]
