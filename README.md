# custom_ai_bot

## 概要
このプロジェクトは、Google Gemini APIを活用したAI Discordボットです。テキスト質問や画像生成、ファイル（画像・音声）を使ったAI応答が可能です。  
![Image](https://github.com/user-attachments/assets/ef7d2a7a-ba23-4c94-bf1b-737bde73758e)

## 主な機能
- `/ask`：AIにテキストで質問できます（画像・音声ファイルは主要な形式に対応）[Grounding with Google Search](https://ai.google.dev/gemini-api/docs/google-search?hl=ja)による検索と[URL Context](https://ai.google.dev/gemini-api/docs/url-context?hl=ja)によるWebへのアクセスに対応
- `/image`：AIによる画像生成（Geminiの画像生成モデルを利用）
- `/info`：利用中のモデル情報表示
- `/help`：コマンド一覧の表示
- Discordの埋め込みメッセージ([Embed](https://discord.com/safety/using-webhooks-and-embeds))によるリッチな応答

## セットアップ・デプロイ方法

### 1. Discord側の準備

#### 1.1 Discord Botの作成
1. [Discord Developer Portal](https://discord.com/developers/applications)にアクセス
2. 「New Application」をクリックして新しいアプリケーションを作成
3. アプリケーション名を入力して「Create」をクリック
4. 左側のメニューから「Bot」を選択
5. 「Add Bot」をクリックしてBotを作成
6. 「Token」セクションで「Reset Token」をクリックしてトークンを生成・コピー
   - このトークンが環境変数 `TOKEN` に必要です

#### 1.2 Bot権限の設定
1. プライベートなコミュニティでの利用では、PUBLIC BOTをオフにすることを推奨します。
   - 「Installation」ページの「Install Link」をNoneに設定
   - 「Bot」ページの「PUBLIC BOT」をオフにする
2. 「OAuth2」→「OAuth2 URL Generator」
3. 「Scopes」で「bot」と「applications.commands」をチェック
4. 「Bot Permissions」で以下の権限をチェック：
   - Send Messages（メッセージ送信）
   - Send Messages in Threads
   - Use Slash Commands（スラッシュコマンド使用）
   - Attach Files（ファイル添付）
   - Embed Links（埋め込みリンク）
5. 生成されたURLをコピー

#### 1.3 BotをDiscordサーバーに招待
1. 上記で生成したURLをブラウザで開く
2. Botを追加したいDiscordサーバーを選択
3. 「認証」をクリックしてBotをサーバーに追加

#### 1.4 サーバーIDの取得
1. Discordで開発者モードを有効化：
   - ユーザー設定 → 詳細設定 → 開発者モード をオンにする
2. Botを追加したサーバー名を右クリック
3. 「IDをコピー」を選択
   - このIDが環境変数 `GUILD_ID` に必要です

### 2. Google Gemini APIの準備
1. [Google AI Studio](https://aistudio.google.com/)にアクセス
2. Googleアカウントでログイン
3. 「Get API key」をクリック
4. 新しいAPIキーを作成してコピー
   - このAPIキーが環境変数 `GEMINI_API_KEY` に必要です

### 3. 必要な環境変数
- `TOKEN`：Discord BotのトークンSD（上記1.1で取得）
- `GUILD_ID`：Botを動作させるDiscordサーバID（上記1.4で取得）
- `GEMINI_API_KEY`：Google Gemini APIキー（上記2で取得）
- `MODEL`：（任意）テキスト生成モデル名（例: gemini-2.0-flash-exp）
- `IMAGE_MODEL`：（任意）画像生成モデル名（例: imagen-3.0-generate-001）

### 4. Dockerでのローカル実行
1. リポジトリのClone
```bash
git clone https://github.com/ellettie/custom-ai-bot
cd custom-ai-bot
```
2. .env.exampleに従い.envをプロジェクトルートに配置
3. イメージをbuildしコンテナを作成、起動
```bash
docker build -t custom_ai_bot .
docker run --env-file .env custom_ai_bot
```

### 5. GitHub Actions + fly.io でのデプロイ
1. このリポジトリをforkする
2. [fly.io](https://fly.io/)でアカウントを作成し、アプリを作成
3. GitHubのリポジトリ設定から「Settings」→「Secrets and variables」→「Actions」を選択
4. 以下のシークレットを追加：
   - `FLY_API_TOKEN`：Fly.ioのAPIトークン
   - `TOKEN`：Discord Botのトークン
   - `GUILD_ID`：DiscordサーバーID
   - `GEMINI_API_KEY`：Gemini APIキー
   - `MODEL`：使用するテキスト生成モデル名
   - `IMAGE_MODEL`：使用する画像生成モデル名
5. `main`ブランチにpushすると、`.github/workflows/fly-deploy.yml` により自動的にfly.ioへデプロイされます

詳細は[fly.io公式ドキュメント](https://fly.io/docs/)や[fly.io公式のGitHub Actionsによるデプロイ手順](https://fly.io/docs/launch/continuous-deployment-with-github-actions/)を参照してください。

### 6. その他クラウドサービスへのデプロイ
Dockerイメージを利用できる任意のクラウドサービス（例: AWS ECS, Google Cloud Run, Azure Container Apps等）でも同様にデプロイ可能です。各サービスの方法で必要な環境変数を設定してください。

## 使用方法
Botがサーバーに追加され、正常に起動すると、以下のスラッシュコマンドが使用できます：

### コマンド一覧
- `/ask テキストでAIに質問 画像、音声ファイルの添付に対応`
- `/image 画像を生成`
- `/info モデル情報表示`
- `/help コマンド一覧表示`

### 使用例
```
/ask 今日の天気について教えて
/ask 画像を説明して（画像ファイルを添付）
/image 美しい夕日の風景
/info
```

## 依存ライブラリとライセンス
- **discord.py==2.5.2**
  - [MITライセンス](https://github.com/Rapptz/discord.py/blob/master/LICENSE)
- **google-genai==1.21.1**
  - [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)
- **Pillow==11.2.1**
  - [MITライセンス（PIL & Pillow）](https://github.com/python-pillow/Pillow/blob/master/LICENSE)

> これらのライブラリは商用利用も可能ですが、再配布時は各ライセンス条項に従ってください。

## ファイル構成
- `run.py`：エントリーポイント
- `bot/`：Bot本体・AI連携・ユーティリティ
  - `__init__.py`：Discordコマンド・Bot本体
  - `gemini.py`：Gemini API連携
  - `myutils.py`：メッセージ分割等の補助関数
- `discord.log`：Botのログ
- `Dockerfile`：Docker用設定
- `.github/workflows/fly-deploy.yml`：GitHub ActionsによるFly.io自動デプロイ

## ライセンス
このプロジェクト自体はMITライセンスです（[LICENSE](./LICENSE)ファイル参照）。
