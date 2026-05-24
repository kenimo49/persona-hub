# persona-hub

[English](./README.md) · **日本語**

> 軽量なペルソナ評価 SDK と最小限の永続化 API。ドメイン特化型の性格診断クイズを、サービス横断で同じペルソナとして扱うための基盤です。

**ステータス**: Pre-alpha — 設計と scaffold は完了、`evaluate()` と API エンドポイントは未実装（[#3](https://github.com/kenimo49/persona-hub/issues/3) / [#5](https://github.com/kenimo49/persona-hub/issues/5)）。本番運用にはまだ使えません。

## 動くと、こうなります

自分のサイトに 5 問程度のクイズを置きます。SDK はブラウザでその場で採点します。任意で persona-hub サーバに結果を POST すると、同じユーザーが関連サイトに来たときも同じプロファイルを引き継げます。

```ts
import { evaluate } from '@persona-hub/core'
import fragranceProfile from '@persona-hub/profiles/fragrance.json'

// answers: { q1: 'a', q2: 'c', ... }
const result = evaluate(answers, fragranceProfile)
// → { type: 'citrus', scores: { citrus: 0.83, woody: 0.41, ... }, confidence: 0.78 }
```

これが SDK 側です。API 側は 4 つのエンドポイント（`POST /personas`、`POST /personas/:id/signals`、`GET /personas/:id`、`GET /personas/:id/aggregate`）で、まるごと任意です — API を使わなくてもクイズは動きます。

## なぜ persona-hub が要るのか

既存のツールはどれも 1 ピースだけを担います。

- **CDP**（Segment / PostHog / RudderStack）— サービス横断のイベントは集約できますが、クイズの採点はできません
- **パーソナリティ API**（Crystal Knows / Truity / Big 5 Assessments）— 採点はできますが、複数サービス・複数ドメインでプロファイルを共有する仕組みがありません
- **クイズ SaaS**（Outgrow / Typeform / Riddle）— 埋め込みウィジェットは出せますが、各サービスは孤立したままです
- **フィーチャーフラグ SDK**（LaunchDarkly）— 「SDK + 永続化ストア」のアーキは正しいものの、ドメインがフラグであってペルソナではありません

persona-hub はこの 3 つのパターンを統合します。クライアント SDK でドメイン特化のクイズ評価をやり、任意で薄い API に投げてサービス横断のペルソナ集約までを担います。

## アーキテクチャ

```
[利用側サービス]                  [persona-hub API — 任意]

  Quiz UI                         POST /personas          (source service が署名)
    +                             POST /personas/:id/signals
  @persona-hub/core (SDK)         GET  /personas/:id
    +                             GET  /personas/:id/aggregate
  @persona-hub/profiles/*.json
```

各サービスはローカルで評価します（0ms、ネットワーク不要、初期状態で GDPR フレンドリー）。永続化はオプトイン方式で、結果を POST すると `persona_id` が払い出され、他サービスから後で読み出せます（ブラウザはストレージを origin ごとに分離するため、明示的な署名付きハンドオフ経由で受け渡します）。

設計の全体像とセキュリティ・プライバシーモデルは [ARCHITECTURE.md](./ARCHITECTURE.md) を参照してください。

## プロファイルパック

- `@persona-hub/profiles/fragrance` — 香水・ホームフレグランスの好み（kaoriq.com）
- `@persona-hub/profiles/pc` — PC ビルドの好み（mypcrig.com、予定）
- `@persona-hub/profiles/whisky` — ウィスキーの好み（legacydram.com、予定）

プロファイルは「設問・選択肢・タイプ・スコア重み」を JSON で定義したものです。誰でも自分のパックを公開できます — [CONTRIBUTING.md](./CONTRIBUTING.md) を参照してください。

## 設計上の参照先

- **LaunchDarkly** — バージョン管理されたルールセットを SDK でメモリ評価し、永続化ストアは任意で添える。persona-hub は「ローカル高速パス + 任意のリモート」という型を借りています（Phase 0 では streaming transport は導入しません）
- **Twilio Segment Engage** — サービス横断のプロファイル集約と派生属性。persona-hub は同種の集約を、セルフホスト可能で SDK ファーストな形で目指します
- **Stripe Elements / Algolia InstantSearch** — SDK + 薄い API を設計のコントラクトとする型

## persona-hub が「やらない」こと

- 認証システムではありません（Auth0 / Clerk / Stytch を使ってください）
- CDP ではありません（汎用イベント収集は Segment / PostHog を）
- クイズビルダー UI でもありません（SDK はヘッドレスで、UI は利用側サービスが自分で組みます）

## 商標と免責

MBTI、DiSC、Big Five、Enneagram、StrengthsFinder への言及は、内部の集約エンジンが扱う概念フレームワークを指すものです。persona-hub は各商標保持者（The Myers-Briggs Foundation、Wiley、Gallup など）と提携・推薦・スポンサー関係はありません。内部の集約エンジンは、Big Five の IPIP など公開項目プールを使えるところで使います。

## ライセンス

Apache 2.0 です。将来的にはマネージドのホスティングサービスを提供する可能性がありますが、このリポジトリのソースコードは引き続き Apache 2.0 で公開します。

## コントリビュート・セキュリティ

- 設計議論: [Issue](https://github.com/kenimo49/persona-hub/issues) を開いてください
- コードのコントリビュート: [CONTRIBUTING.md](./CONTRIBUTING.md) を参照
- セキュリティ報告: [SECURITY.md](./SECURITY.md) を参照
- コミュニティ規範: [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) を参照

## 開発手順

**2 つの独立したサブシステム**を抱える monorepo 構成です。TypeScript パッケージ（SDK）と Python API サービスはそれぞれ別管理で、pnpm ワークスペースの対象は `packages/*` のみ、`apps/api/` は自前の Python 環境を持ちます。

```
persona-hub/
├── packages/
│   ├── core/             # @persona-hub/core — 評価 SDK (TypeScript)
│   └── profiles/         # @persona-hub/profiles — プロファイルパック (JSON)
└── apps/
    └── api/              # 永続化 + 集約 API (FastAPI)
```

作業対象のサブシステムだけセットアップすれば動きます。

### TypeScript SDK (packages/)

Node 20+ と pnpm 9+ が必要です。

```bash
pnpm install
pnpm -r typecheck
pnpm -r test
```

### Python API (apps/api/)

Python 3.12+（uv 推奨）。詳細は [`apps/api/README.md`](./apps/api/README.md) を参照してください。

```bash
cd apps/api
uv venv && source .venv/bin/activate    # または: python -m venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"              # または: pip install -e ".[dev]"
pytest
uvicorn app.main:app --reload
```

SDK 側を触るだけなら Python は不要、API 側を触るだけなら Node は不要です。

## ステータスとロードマップ

設計判断は [Issue #1: Architecture](https://github.com/kenimo49/persona-hub/issues/1) に、実装計画はオープン Issue 一覧にあります。
