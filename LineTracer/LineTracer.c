#include "app.h"
#include "LineTracer.h"
#include <stdio.h>

#include "spike/pup/motor.h"
#include "spike/pup/colorsensor.h"

/* ライントレーサの内部状態 */
typedef enum {
    STATE_LINE_TRACING,  /* 通常ライントレース */
    STATE_STOPPING,      /* 停止待機中 */
    STATE_ROTATING,      /* 90度回転中 */
    STATE_DONE           /* 回転完了・停止 */
} TracerState;

/* 関数プロトタイプ宣言 */
static int16_t steering_amount_calculation(void);
static void    motor_drive_control(int16_t steering_amount);

static pup_motor_t  *fg_left_motor;
static pup_motor_t  *fg_right_motor;
static pup_device_t *fg_color_sensor;
static TracerState   fg_state               = STATE_LINE_TRACING;
static int32_t       fg_rotation_start      = 0;
static int32_t       fg_gray_detect_counter = 0;
static int32_t       fg_stop_counter        = 0;
static int32_t       fg_log_counter         = 0;

void LineTracer_Configure(pbio_port_id_t left_motor_port, pbio_port_id_t right_motor_port, pbio_port_id_t color_sensor_port)
{
    fg_color_sensor = pup_color_sensor_get_device(color_sensor_port);
    fg_left_motor   = pup_motor_get_device(left_motor_port);
    fg_right_motor  = pup_motor_get_device(right_motor_port);

    pup_motor_setup(fg_left_motor,  PUP_DIRECTION_COUNTERCLOCKWISE, true);
    pup_motor_setup(fg_right_motor, PUP_DIRECTION_CLOCKWISE, true);

    fg_rotation_start      = 0;
    fg_state               = STATE_LINE_TRACING;
    fg_gray_detect_counter = 0;
    fg_stop_counter        = 0;
    fg_log_counter         = 0;
}

/* ライントレースタスク(100msec周期で関数コールされる) */
void tracer_task(intptr_t unused) {
    pup_color_hsv_t hsv;
    int32_t         motor_count;

    switch (fg_state) {

    case STATE_LINE_TRACING:
        hsv = pup_color_sensor_hsv(fg_color_sensor, true);
        fg_log_counter++;
        if (fg_log_counter >= 1) {  /* 10サイクル=1秒ごとにHSV値を出力 */
            printf("HSV: h=%d s=%d v=%d (gray_s<=%d v=%d-%d cnt=%d)\n",
                   hsv.h, hsv.s, hsv.v,
                   GRAY_S_MAX, GRAY_V_MIN, GRAY_V_MAX,
                   fg_gray_detect_counter);
            fg_log_counter = 0;
        }
        if (hsv.s <= GRAY_S_MAX && hsv.v >= GRAY_V_MIN && hsv.v <= GRAY_V_MAX) {
            fg_gray_detect_counter++;
            if (fg_gray_detect_counter >= GRAY_DETECT_COUNT) {
                /* グレーをGRAY_DETECT_COUNT回連続検出 → まず停止 */
                printf("Gray detected (h=%d s=%d v=%d)! Stopping.\n",
                       hsv.h, hsv.s, hsv.v);
                pup_motor_set_power(fg_left_motor,  0);
                pup_motor_set_power(fg_right_motor, 0);
                fg_stop_counter = 0;
                fg_state = STATE_STOPPING;
            }
        } else {
            fg_gray_detect_counter = 0;
            motor_drive_control(steering_amount_calculation());
        }
        break;

    case STATE_STOPPING:
        fg_stop_counter++;
        if (fg_stop_counter >= STOP_WAIT_COUNT) {
            /* 停止完了 → その場で90度回転開始 */
            printf("Starting 90-degree rotation after gray detection.\n");
            fg_rotation_start = pup_motor_get_count(fg_left_motor);
            pup_motor_set_power(fg_left_motor,   ROTATION_SPEED);
            pup_motor_set_power(fg_right_motor, -ROTATION_SPEED);
            fg_state = STATE_ROTATING;
        }
        break;

    case STATE_ROTATING:
        motor_count = pup_motor_get_count(fg_left_motor) - fg_rotation_start;
        if (motor_count >= ROTATION_DEGREES) {
            pup_motor_set_power(fg_left_motor,  0);
            pup_motor_set_power(fg_right_motor, 0);
            printf("Rotation complete.\n");
            fg_state = STATE_DONE;
        }
        break;

    case STATE_DONE:
        pup_motor_set_power(fg_left_motor,  0);
        pup_motor_set_power(fg_right_motor, 0);
        break;
    }

    ext_tsk();
}

/* ステアリング操舵量の計算 */
static int16_t steering_amount_calculation(void) {
    uint16_t  target_brightness;
    float32_t diff_brightness;
    int16_t   steering_amount;
    int32_t   ref;

    target_brightness = (WHITE_BRIGHTNESS + BLACK_BRIGHTNESS) / 2;
    ref = pup_color_sensor_reflection(fg_color_sensor);
    diff_brightness = (float32_t)(target_brightness - ref);
    steering_amount = (int16_t)(diff_brightness * STEERING_COEF);

    return steering_amount;
}

/* 走行モータ制御 */
static void motor_drive_control(int16_t steering_amount) {
    int left_motor_power, right_motor_power;

    left_motor_power  = (int)(BASE_SPEED + (steering_amount * LEFT_EDGE));
    right_motor_power = (int)(BASE_SPEED - (steering_amount * LEFT_EDGE));

    pup_motor_set_power(fg_left_motor,  left_motor_power);
    pup_motor_set_power(fg_right_motor, right_motor_power);
}
