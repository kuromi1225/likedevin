# ベースイメージとしてNode.js v20-alpineを使用
FROM node:20-alpine

# 作業ディレクトリを設定
WORKDIR /app

# 最初にpackage.jsonとpackage-lock.jsonをコピー
COPY package*.json ./

# npm ci を使って、package-lock.jsonから依存関係をクリーンインストール
# これにより、ビルドの再現性が高まります
RUN npm ci

# アプリケーションのソースコード全体をコピー
COPY . .

# 開発サーバー用のポートを開放
EXPOSE 3000

# Next.jsの開発サーバーを起動
CMD ["npm", "run", "dev"]