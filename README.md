# LikeDevin

Devin.aiをLlama4 Maverickを使って実装したAIエージェントアプリケーション

## 概要

このプロジェクトは、Devin.aiのようなAIエージェント機能を提供するWebアプリケーションです。フロントエンドにNext.js、バックエンドにFastAPI、AIモデルにOllamaを使用しています。

## 技術スタック

- **フロントエンド**: Next.js 14.2.3, React 18, TypeScript, Tailwind CSS
- **バックエンド**: FastAPI, Python 3.9, WebSocket
- **AIモデル**: Ollama (Llama4 Maverick)
- **コンテナ**: Docker, Docker Compose

## 機能

- AIエージェントとのチャット機能
- ファイルエクスプローラー
- タスク実行機能
- リアルタイム通信（WebSocket）
- 設定管理

## セットアップ

### 前提条件

- Docker
- Docker Compose

### 起動方法

1. リポジトリをクローン:
```bash
git clone https://github.com/kuromi1225/likedevin.git
cd likedevin
git checkout develop
```

2. Docker Composeで起動:
```bash
docker compose up -d
```

3. ブラウザで以下のURLにアクセス:
- フロントエンド: http://localhost:3000
- バックエンドAPI: http://localhost:8000
- Ollama API: http://localhost:11434

## 使用方法

1. ブラウザでhttp://localhost:3000にアクセス
2. タスクプロンプトを入力
3. "Start Task"ボタンをクリック
4. AIエージェントがタスクを実行

## 開発

### ディレクトリ構造

```
likedevin/
├── frontend/          # Next.jsフロントエンド
├── backend/           # FastAPIバックエンド
├── workspace/         # エージェント作業ディレクトリ
├── ollama/           # Ollamaデータ
└── docker-compose.yml # Docker Compose設定
```

### 環境変数

`.env`ファイルで以下の環境変数を設定:

```
OLLAMA_API_URL=http://ollama:11434
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## トラブルシューティング

### コンテナが起動しない場合

```bash
docker compose logs
```

でログを確認してください。

### ポートが使用中の場合

他のアプリケーションがポート3000、8000、11434を使用していないか確認してください。

