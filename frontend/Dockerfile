FROM node:20-alpine

WORKDIR /app

# 依存関係のインストール
COPY package*.json ./
RUN npm ci

# アプリケーションコードのコピー
COPY . .

# 非rootユーザーで実行
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001
USER nextjs

EXPOSE 3000

CMD ["npm", "run", "dev"]
