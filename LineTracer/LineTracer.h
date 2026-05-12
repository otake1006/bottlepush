#ifdef __cplusplus
extern "C" {
#endif

/* 下記の項目は各ロボットに合わせて変えること */

/* カラーセンサの輝度設定 */
#define WHITE_BRIGHTNESS  (40)
#define BLACK_BRIGHTNESS  (10)

/* ステアリング操舵量の係数 */
#define STEERING_COEF     (1.5F)

/* 走行基準スピード */
#define BASE_SPEED        (30)

/* ライントレースエッジ切り替え */
#define LEFT_EDGE         (1)
#define RIGHT_EDGE        (1)

/* グレー検出の連続判定回数(1回=100ms) 誤検知防止のデバウンス */
#define GRAY_DETECT_COUNT (3)

/* グレー検出後の停止待機サイクル数(1サイクル=100ms) */
#define STOP_WAIT_COUNT   (3)

/* グレー判定のHSV閾値 */
#define GRAY_S_MAX        (30)   /* 彩度上限: グレーは低彩度 */
#define GRAY_V_MIN        (20)   /* 明度下限: 黒を除外 */
#define GRAY_V_MAX        (80)   /* 明度上限: 白を除外 */

/* 90度回転に必要なモータ角度[度] ロボットのホイールベースと車輪径に合わせて調整 */
#define ROTATION_DEGREES  (200)

/* 90度回転時のモータ速度 */
#define ROTATION_SPEED    (40)

#include "pbio/port.h"  

  extern void LineTracer_Configure(pbio_port_id_t left_motor_port, pbio_port_id_t right_motor_port, pbio_port_id_t color_sensor_port);
  
#ifdef __cplusplus
}
#endif
