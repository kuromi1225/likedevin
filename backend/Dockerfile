# ベースイメージとしてPython 3.9-slimを使用
FROM python:3.9-slim

# パッケージマネージャのリストを更新し、gitをインストール
# --no-install-recommends は不要な推奨パッケージを省き、イメージを軽量に保ちます
RUN apt-get update && apt-get install -y git --no-install-recommends

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係ファイルをコピー
COPY requirements.txt .

# Pythonの依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt

# ソースコード全体をコピー
COPY . .

# FastAPIサーバーが使用するポートを指定
EXPOSE 8000

# コンテナ起動時にUvicornサーバーを起動
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]