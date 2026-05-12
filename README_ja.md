# bottlepush プロジェクト 日本語ガイド

## プロジェクト概要

このプロジェクトは **RasPike-ART** 向けの ETRobocon アプリケーションです。

- **RasPike-ART**: Raspberry Pi と LEGO SPIKE Prime ハブを USB で接続するプラットフォーム
- Raspberry Pi 側は C 言語で記述し、TOPPERS/ASP3 RTOS 上で動作
- モーターやセンサーの操作には SPIKE-RT 互換の PUP API を使用

---

## ビルド・実行コマンド

コマンドはすべて **`sdk/workspace/`（このプロジェクトの親ディレクトリ）** から実行します。

| 操作 | コマンド |
|---|---|
| ビルド | `make img=bottlepush` |
| Raspberry Pi で実行 | `make start` |
| SPIKE ファームウェア更新 | `make -f ../common/Makefile.raspike-art update_spike` |
| ビルド成果物の削除 | `make clean` |
| RasPike-ART ライブラリの削除 | `make clean_art` |

> **注意**: SPIKE ファームウェアの更新には事前に DFU モードへの切り替えが必要です。  
> テストスイートはありません。動作確認は実機で行います。

---

## アーキテクチャ

### タスクモデル（TOPPERS/ASP3）

タスクと周期ハンドラは `app.cfg` に TOPPERS カーネルオブジェクトマクロ（`CRE_TSK`、`CRE_CYC`）で定義します。

| タスク | 動作 |
|---|---|
| `main_task`（`TA_ACT`） | 起動時に1回だけ実行。デバイス初期化 → スタートトリガー待機 → `sta_cyc()` で周期ハンドラを起動 |
| `tracer_task` | `CRE_CYC` により `LINE_TRACER_PERIOD`（100 ms）ごとに起動。**末尾で必ず `ext_tsk()` を呼ぶこと** |

スタックサイズ・優先度・周期は `app.h` で定義します。

### ファイル構成

```
app.h          — タスク優先度、周期、スタックサイズ、extern 宣言
app.c          — main_task: デバイス初期化、スタートトリガー、sta_cyc()
app.cfg        — TOPPERSカーネルオブジェクト定義（タスク、周期ハンドラ）
Makefile.inc   — USE_RASPIKE_ART=1、APPL_COBJS、APPL_DIRS、INCLUDES
LineTracer/    — APPL_DIRS 経由で個別にコンパイルされるコンポーネントモジュール
```

---

## SPIKE PUP API

ヘッダは `spike/pup/` または `spike/hub/` からインクルードします。  
`ev3api.h` ではなく **`spikeapi.h`** を使用してください。

| ヘッダ | 主な関数 |
|---|---|
| `spike/pup/motor.h` | `pup_motor_get_device`、`pup_motor_setup`、`pup_motor_set_power`、`pup_motor_get_count` |
| `spike/pup/colorsensor.h` | `pup_color_sensor_get_device`、`pup_color_sensor_color`（→ `pup_color_hsv_t`）、`pup_color_sensor_reflection` |
| `spike/pup/forcesensor.h` | `pup_force_sensor_get_device`、`pup_force_sensor_touched` |
| `spike/hub/imu.h` | 3軸IMU |
| `spike/hub/display.h` | ハブのディスプレイ |

### カラーセンサーの注意点

`pup_color_sensor_color(pdev, surface)` の戻り値は **`pup_color_hsv_t`** 構造体です。

| フィールド | 意味 | 範囲 |
|---|---|---|
| `h` | 色相（Hue） | 0〜359° |
| `s` | 彩度（Saturation） | 0〜100% |
| `v` | 明度（Value） | 0〜100% |

色名の enum は存在しないため、**HSV の数値範囲で色を判定**してください。

---

## ポート割り当て（このプロジェクト）

| ポート | デバイス |
|---|---|
| A | 右モーター（`PUP_DIRECTION_CLOCKWISE`） |
| B | 左モーター（`PUP_DIRECTION_COUNTERCLOCKWISE`） |
| D | フォースセンサー（スタートトリガー） |
| E | カラーセンサー |

---

## 新しいモジュールの追加手順

1. サブディレクトリを作成する（例: `MyModule/MyModule.c`、`MyModule/MyModule.h`）

2. `Makefile.inc` に以下を追記する：
   ```makefile
   APPL_COBJS += MyModule.o
   APPL_DIRS  += $(mkfile_path)MyModule
   INCLUDES   += -I$(mkfile_path)MyModule
   ```

3. `app.cfg` に `ATT_MOD` を追加する（`app.o` は既に登録済みのため不要）：
   ```
   ATT_MOD("MyModule.o");
   ```

---

## 青色検出の HSV しきい値リファレンス

青色の色相中心は **240°** です。床やラインと区別するための典型的なしきい値：

```c
hsv.h >= 200 && hsv.h <= 280   // 青色の色相範囲
hsv.s >= 50                    // グレー・白を除外
hsv.v >= 30                    // 黒を除外
```
