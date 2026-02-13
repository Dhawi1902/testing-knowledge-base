FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm config set strict-ssl false && npm install

COPY . .

EXPOSE 5173

CMD ["npx", "vite", "--host"]
