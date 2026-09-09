# instagram-stories-auto

島田脳神経外科の Instagram ストーリーを毎朝自動投稿する仕組み。

- 起動: 毎朝 **07:00 JST**（cron-job.org → GitHub Actions）／保険で GitHub の schedule も走る
- 二重投稿は自動で防止される（同じ日に2回走っても、投稿済みの分はスキップされる）

## 毎日なにが投稿されるか

優先順位はこの順で決まる。

| 優先 | 条件 | 投稿されるもの |
|---|---|---|
| 1 | `no_post_dates.json` に登録された日 | **なにも投稿しない**（お盆休み等の休業日） |
| 2 | `closures.json` に登録された日 | `closure-video.mp4` **のみ**（終日休診の日） |
| 3 | `announcements.json` に **mode: replace** の指定がある日 | 曜日画像を**出さず**、指定ファイルのみ |
| 4 | 上記以外 | 曜日画像（`monday.png` 〜 `sunday.png` ／祝日は `holiday.png`） |

さらに、**mode: add** の指定がある日は、上のどれであっても**そのあとに追加で**投稿される。
また7日以内に `closures.json` の休診日があると、予告として `closure-video.mp4` が追加される。

---

## ✏️ 特定の日だけ別の画像・動画に差し替えたいとき

`announcements.json` を編集するだけでよい。**コードを触る必要はない。**

### 例1：当日は曜日画像を出さず、お知らせだけ出す

```json
{
  "start": "2026-09-11",
  "end": "2026-09-11",
  "media": "20260911-oshirase.mp4",
  "mode": "replace",
  "label": "9/11 当日（曜日画像を出さず、これだけ投稿）"
}
```

### 例2：前日は通常どおり投稿したうえで、予告として追加する

```json
{
  "start": "2026-09-10",
  "end": "2026-09-10",
  "media": "20260911-oshirase.mp4",
  "mode": "add",
  "label": "9/11 の予告（曜日画像のあとに追加）"
}
```

### 各項目の意味

| キー | 意味 |
|---|---|
| `start` / `end` | 投稿する期間（**両端を含む**）。1日だけなら同じ日付を入れる |
| `media` | 投稿するファイル名。**画像（.png/.jpg）でも動画（.mp4/.mov）でもよい**。拡張子で自動判別される |
| `mode` | `add`（曜日画像の**あとに追加**）／ `replace`（曜日画像を**出さずに差し替え**）。省略すると `add` |
| `label` | 人間が読むためのメモ。動作には影響しない |

### 手順

1. 画像・動画ファイルを**リポジトリ直下**に置く
2. `announcements.json` にエントリを追加する
3. commit して **push する**（pushしないと反映されない）

期間（`end`）を過ぎると**自動的に元の運用に戻る**。後片付けは不要。

---

## ⚠️ 注意点

- **ファイル名は半角英数字にする。** 日本語ファイル名は使えない
  （GitHubのURL経由でInstagramに渡す仕組みのため、日本語だと取得に失敗する）
  例: `20260911お知らせ.mp4` ❌ → `20260911-oshirase.mp4` ✅
- **動画の要件**: mp4（H.264）・9:16（1080×1920）・3〜60秒
- `closures.json` は**終日休診**の日に使う。「午後だけ休診」の日には使わない
  （終日休診として告知されてしまう。午後だけの日は `mode: replace` を使う）
- **3つの設定ファイルの使い分け**
  - `no_post_dates.json` … その日は**なにも投稿しない**（お盆休み・年末年始などの休業）
  - `closures.json` … その日は**休診動画だけ**を投稿する（終日休診）
  - `announcements.json` … その日の投稿内容を**差し替える／追加する**（時間変更・午後だけ休診など）
- 現在 `closure-video.mp4` は**リポジトリに存在しない**。`closures.json` を使う日が来たら、
  先にこのファイルを置くこと。置かずに登録すると投稿が失敗する

---

## ファイル構成

| ファイル | 役割 |
|---|---|
| `post_story.py` | 本体。投稿予定を組み立てて Instagram に投稿する |
| `announcements.json` | 期間限定の差し替え・追加投稿の設定 |
| `closures.json` | 終日休診の日（休診動画を投稿する） |
| `no_post_dates.json` | 休業日（そもそも投稿しない日） |
| `monday.png` 〜 `sunday.png` / `holiday.png` | 曜日ごとの通常画像 |
| `create_monthly_plan.py` | 月間投稿計画のissueを作る |
| `refresh_token.py` | Instagramの長期トークンを更新する（毎月1日） |

## 動作確認のしかた（投稿せずに予定だけ見る）

```bash
python3 -c "
import post_story as ps
from datetime import date
c = ps.load_closures()
for d in ['2026-09-10','2026-09-11','2026-09-12']:
    t = date.fromisoformat(d)
    print(d, ps.build_plan(t, c, ps.load_announcements_for(t)))
"
```
