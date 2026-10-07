# 📐 数学教材ジェネレーター (MathLessonGenerator)

中学校数学（1〜3年・全23単元）の学習プリント／定期テストを自動生成するWebアプリです。
数研出版 StudyAid D.B. の便利さはそのままに、「学級の実態に合わせた自動書き換え」と「1枚に収まる自動レイアウト」を目指しました（StudyAid超え仕様）。

- 🌐 Web版（Vercel）：ブラウザだけで使えます
- 💻 Windows版：`dist/MathLessonGenerator.exe`（πアイコン付き、ダブルクリック起動）

## ✨ 主な機能

| 分類 | 機能 |
|---|---|
| 問題生成 | 全23単元・題材つき、毎回ランダム（シード指定で再現可） |
| 連立方程式 | 7パターン（加減基本／標準／代入／かっこ／小数／分数／ミックス）＋途中式の自動生成、教科書通りの波括弧｛表示（Word数式オブジェクト） |
| 図・グラフ | 一次関数・比例・反比例・2次関数のグラフ、円・相似・三平方・箱ひげ図・おうぎ形・立体・作図下図を自動描画（補助線つき2段階図あり） |
| 難易度 | 基礎／標準／発展／入試レベル／基礎＋標準同時 |
| 解答欄 | A:1行完結／B:左右分割／C:定期テスト型（2段＋右端集約） |
| 印刷 | A4・B5・B4・A3×縦横、文字・余白・解答欄幅の調整、印刷パターン4種（通り／答空欄／解説空欄／答・解説空欄）、表紙＋配点チェック |
| 出力 | Word(.docx)／PDF（教科書体埋め込み）／スライド(.pptx)／StudyAid流し込みtxt／タブレット配信＋QR |
| 支援配慮 | 計算手順ヒント／ポイント解説／ゆったり解答欄／作図拡大／証明穴埋め |
| 評価 | 観点別ルーブリック自動付帯、集計→所見文案、採点チェック |
| 資産化 | 問題DB・履歴検索、誤答分析→補習プリント、遡り診断、教科書ページ対応、学年共有zip、図ストック再利用 |
| 授業 | フラッシュ小テスト（タイマー・ランダム順） |

詳しい操作手順は [MANUAL.md](MANUAL.md) をご覧ください。

## 🚀 使い方（5分スタート）

### Web版
https://suugaku-kyouzai.vercel.app をブラウザで開くだけです。

### Windows版（Python）
```bat
pip install -r requirements.txt
python app.py
```
→ http://127.0.0.1:5000 を開く

### Windows版（EXE・Python不要）
`MathLessonGenerator起動.bat` をダブルクリック（ブラウザが自動で開きます）。

## 🖥️ 開発者向け

- `app.py` … Flask本体・Word生成・全ルート
- `templates.py` … 問題生成ロジック（単元カタログつき）
- `units_extra.py` … 図形・データ系の追加生成器
- `exporters.py` … PDF／スライド出力
- `smart_tools.py` … DB・誤答推定・所見・診断・教科書対応
- `templates/index.html` … 画面（リボン＋左引き出しUI）
- `api/index.py` … Vercel用エントリ

EXE再ビルド（開発PCのみ。`pyinstaller` が別途必要）：
```
pip install pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name MathLessonGenerator --icon math_icon.ico --add-data "templates;templates" app.py
```

## 📝 ライセンス・注意
- 教科書の図や市販ワークの図を取り込む場合は、著作権にご注意ください（自作・共有可の素材推奨）。
- UDデジタル教科書体は Windows 同梱フォントを利用しています。
