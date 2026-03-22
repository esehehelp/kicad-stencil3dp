# KiCad Stencil 3DP Plugin

KiCadのPCBから半田ペーストステンシルのSTLを自動生成するActionPluginです。
F.Paste / B.Paste レイヤーのパッド形状をKiCad APIで直接読み取り、OpenSCADで3Dプリント用STLを出力します。

## 特徴

- **DXF不要** — KiCad APIからパッド座標・形状を直接取得してOpenSCADスクリプトを生成
- **各種パッド形状に対応** — 矩形 / 楕円 / 円 / 丸角矩形（スタジアム形状含む）
- **ペーストマージン反映** — パッド・フットプリント・ボードのペーストマージン設定をPLOT_CONTROLLERと同様に解決
- **開口サイズ調整** — offsetパラメータで開口を一律拡大・縮小可能（デフォルト `-0.05mm`）
- **マージン付きプレート** — ステンシル外周にテープ貼り付け用の余白を自動追加（デフォルト10mm）
- **位置決めピン穴** — マージン四隅に任意径のピン穴を追加可能
- **細ピッチ検出** — 0.5mm未満のパッド間距離を持つフットプリントを事前警告
- **設定永続化** — ダイアログの設定をJSONで保存・復元

## 動作環境

- KiCad 9.0以降
- [OpenSCAD](https://openscad.org/) (Nightly推奨)
- Windows / macOS / Linux

## 開発環境セットアップ

[uv](https://docs.astral.sh/uv/) を使用しています。

```bash
uv sync          # 仮想環境作成・dev依存インストール
uv run ruff check stencil3dp/   # lint
```

## インストール

```bash
uv run install.py
```

`stencil3dp/` フォルダと `gen_stl.scad` を KiCadプラグインディレクトリへコピーします。

| OS | インストール先 |
|---|---|
| Windows | `%USERPROFILE%\Documents\KiCad\9.0\scripting\plugins\` |
| macOS | `~/Library/Preferences/kicad/9.0/scripting/plugins/` |
| Linux | `~/.local/share/kicad/9.0/scripting/plugins/` |

KiCadを再起動後、**Tools → External Plugins → Stencil 3DP** から起動します。

## 使い方

1. KiCadでPCBファイルを開く
2. **Tools → External Plugins → Stencil 3DP** を実行
3. ダイアログで各パラメータを確認・調整してOK
4. 出力先フォルダに `<boardname>-stencil.scad` と `<boardname>-stencil.stl` が生成される

## ダイアログのパラメータ

| パラメータ | デフォルト | 説明 |
|---|---|---|
| Layer | F.Paste | 対象レイヤー（F.Paste / B.Paste） |
| Thickness (mm) | 0.16 | ステンシル厚み |
| Offset (mm) | -0.05 | 開口拡張量（負=縮小、正=拡大） |
| Registration pin holes | ON | 位置決めピン穴をマージン四隅に追加 |
| Pin diameter (mm) | 1.5 | ピン穴径 |
| Fine-pitch warning | ON | パッド間距離0.5mm未満を警告 |
| Output directory | boardと同じ | 出力先ディレクトリ |
| OpenSCAD path | 自動検出 | openscad実行ファイルのパス |

## 注意事項

- F.Pasteレイヤーが無効なパッドはステンシルに含まれません。コネクタ等でVBUS/GNDピンが開口されない場合は、フットプリントエディタでそれらのパッドにF.Pasteレイヤーを追加してください。
- B.Paste選択時はX軸ミラーで出力します。

## ファイル構成

```
kicad-stencil3dp/
├── stencil3dp/
│   ├── __init__.py          # プラグイン登録
│   ├── plugin.py            # ActionPlugin本体・細ピッチ検出
│   ├── dialog.py            # 設定ダイアログ（JSON永続化）
│   ├── scad_generator.py    # KiCad APIからSCADを直接生成
│   └── openscad_runner.py   # OpenSCAD CLIラッパー
├── gen_stl.scad             # Makefile手動実行用SCADスクリプト
├── Makefile                 # make runでDXFから手動生成
├── install.py               # KiCadプラグインディレクトリへインストール
├── pyproject.toml           # プロジェクト設定（uv / ruff）
└── presets/
    └── Bambu Lab A1 0.2 nozzle.bbscfg
```

## Makefileによる手動実行

KiCadなしでDXFから直接STLを生成したい場合：

```bash
make run \
  SOURCE=path/to/board-F_Paste.dxf \
  TARGET=out.stl \
  WIDTH=80 HEIGHT=60 \
  THICKNESS=0.16 OFFSET=-0.05
```

## スライサープリセット

`presets/` フォルダにBambu Studioのプリセットファイルを用意しています。

| ファイル | プリンター | ノズル | レイヤー高さ |
|---|---|---|---|
| `Bambu Lab A1 0.2 nozzle.bbscfg` | Bambu Lab A1 | 0.2mm | 0.06mm |

### インポート手順（Bambu Studio）

1. Bambu Studioを開く
2. **File → Import → Import Configs** を選択
3. `presets/Bambu Lab A1 0.2 nozzle.bbscfg` を選択

プロセス名 **`0.06mm Print Stencil @BBL A1 0.2 nozzle`** がインポートされます。
0.2mmノズルで0.06mmの薄層印刷を行うステンシル専用設定です。
