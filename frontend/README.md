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

議事録の追加後はメモリ抽出を続けて実行します。抽出が失敗しても議事録は残り、「未抽出」の回から再実行できます。文字数制限による切り詰めと用語正規化の結果も画面に表示します。

Google連携を解除すると、その連携で作成した定例のカレンダー同期が停止します。旧エージェント向けの画面やAPIは使用しません。

## データとテスト

- `src/features/series/types.ts` はシリーズAPIのレスポンス型です。辞書の型は `src/features/dictionary/types.ts` にあります。
- クエリキーは `seriesKeys` / `calendarKeys` に集約しています。シリーズの変更は詳細配下と一覧を無効化し、メモリの変更は返却されたボードでキャッシュを置き換えます。
- セッションのユーザーIDが変わったときはクエリキャッシュを全消去します。同じユーザーのトークン更新では消去しません。
- APIの400〜499エラーはクエリを再試行しません。サーバー・ネットワークエラーの再試行回数と待機時間はReact Queryの既定値を維持します。
- カレンダー・Slackのエラーコードは共通の対応表で日本語に変換します。カレンダーエラーは、参加者には作成者への確認を案内し、作成者には具体的な原因を表示します。
- Vitest・React Testing Library・MSWで、実際のコンポーネントからHTTP境界までを検証します。

品質確認:

```sh
npm run check && npm run type-check && npm run test -- --run && npm run build
```
