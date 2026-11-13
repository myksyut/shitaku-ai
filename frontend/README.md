# Shitaku.ai フロントエンド

React 19・TypeScript・Vite・Tailwind CSS v4。APIの契約は[定例シリーズのチーム共有化設計書](../docs/design/team-owned-meeting-series.md)を参照してください。

## 開発

`.env.example` を参考に Supabase と API の接続先を設定し、`npm install`、`npm run dev` を実行します。ログインは Supabase の Google 認証を使用します。

## 画面

| URL | 内容 |
|---|---|
| `/` | 参加中の定例一覧と、Googleカレンダーからの追加 |
| `/series/:seriesId` | 回・チームメモリ・辞書・作成者向け設定 |
| `/series/:seriesId/occurrences/:occurrenceId` | 議題の投稿、アジェンダ、議事録・ナレッジ |
| `/settings/google` | 自分のGoogle連携 |
| `/settings/slack` | 自分のSlack連携 |

参加者は閲覧、未来のキャンセルされていない回への議題の投稿、自分の議題の取り下げ、アクションアイテムの完了・取り下げ・再オープンができます。その他の編集・生成・抽出・削除は作成者だけに表示します。認可の最終判断はAPIが行います。

開始済みの回では議事録の追加後にメモリ抽出を続けて実行します。未来の回では議事録だけを保存し、開始後に抽出できます。抽出が失敗しても議事録は残り、開始済みの「未抽出」の回から再実行できます。文字数制限による切り詰めと用語正規化の結果も画面に表示します。

Google連携を解除すると、その連携で作成した定例のカレンダー同期が停止します。旧エージェント向けの画面やAPIは使用しません。

## データとテスト

- `src/features/series/types.ts` はシリーズAPIのレスポンス型です。辞書の型は `src/features/dictionary/types.ts` にあります。
- クエリキーは `seriesKeys` / `calendarKeys` に集約しています。メモリ変更は返却されたボードを即時反映し、定例詳細と一覧だけを無効化します。その他の変更も対象の回・辞書・設定だけを無効化し、無関係なメモリやライブのMeet候補を再取得しません。
- 認証済みユーザーごとに独立したQueryClientを作成します。ユーザー切り替え・ログアウト時には以前のクライアントを切り離し、進行中の変更が別ユーザーのキャッシュに反映されることを防ぎます。同じユーザーのトークン更新ではクライアントを維持します。
- APIの400〜499エラーはクエリを再試行しません。サーバー・ネットワークエラーの再試行回数と待機時間はReact Queryの既定値を維持します。
- カレンダー・Slackのエラーコードは共通の対応表で日本語に変換します。カレンダーエラーは、参加者には作成者への確認を案内し、作成者には具体的な原因を表示します。
- Vitest・React Testing Library・MSWで、実際のコンポーネントからHTTP境界までを検証します。

品質確認:

```sh
npm run check && npm run type-check && npm run test -- --run && npm run build
```
