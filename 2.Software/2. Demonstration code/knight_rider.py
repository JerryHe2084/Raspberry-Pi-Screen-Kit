#!/usr/bin/env python3
import time
import threading
import board
import neopixel

# =========================
# LED 配置
# =========================
LED_COUNT = 20
LED_PIN = board.D12  # GPIO12 = PWM0
BRIGHTNESS = 0.5
ORDER = neopixel.GRB

pixels = neopixel.NeoPixel(
    LED_PIN, LED_COUNT, brightness=BRIGHTNESS, auto_write=False, pixel_order=ORDER
)

RED = (255, 0, 0)
BLUE = (0, 0, 255)
OFF = (0, 0, 0)

current_mode = None
run_flag = True  # 总控制标志

mode_lock = threading.Lock()  # 避免访问冲突


def clear():
    pixels.fill(OFF)
    pixels.show()


# =========================
# 光效模式
# =========================
def kitt_80s():
    trail = 5
    delay = 0.04
    pos = 0
    direction = 1

    while run_flag:
        with mode_lock:
            if current_mode != "kitt_80s":
                return

        for i in range(LED_COUNT):
            distance = abs(i - pos)
            if distance < trail:
                brightness = max(0, 255 - distance * 60)
                pixels[i] = (brightness, 0, 0)
            else:
                pixels[i] = OFF

        pixels.show()
        pos += direction
        if pos >= LED_COUNT - 1 or pos <= 0:
            direction *= -1
        time.sleep(delay)


def kitt_2008():
    trail = 5               # 尾巴长度
    delay = 0.05            # 每步延时
    pause = 0.05            # 方向切换暂停
    head_brightness = 255   # 灯头亮度
    color = RED             # 灯珠颜色
    anim_range = range(0, LED_COUNT // 2)  # 左半边动画
    tail_intensity = [head_brightness * (1 - i / trail) for i in range(trail)]

    while run_flag:
        with mode_lock:
            if current_mode != "kitt_2008":
                return

        # 双向循环
        for direction in [1, -1]:
            if direction == 1:
                start = -trail + 1
                end = len(anim_range) + trail
                step = 1
            else:
                start = len(anim_range) + trail - 1
                end = -trail
                step = -1

            for head in range(start, end, step):
                with mode_lock:
                    if current_mode != "kitt_2008":
                        return

                pixels.fill(OFF)

                # 绘制彗星尾巴
                for i in range(trail):
                    pos = head + direction * i
                    if pos in anim_range:
                        intensity = tail_intensity[i]
                        c = tuple(int(c_ * intensity / 255) for c_ in color)
                        pixels[pos] = c
                        # 镜像绘制
                        mirror_pos = LED_COUNT - 1 - pos
                        pixels[mirror_pos] = c

                pixels.show()
                time.sleep(delay)

            time.sleep(pause)


def police():
    flash_cycle = 6
    delay = 0.1
    t = 0

    while run_flag:
        with mode_lock:
            if current_mode != "police":
                return

        pixels.fill(OFF)

        state_left = (t % 2 == 0)
        for i in range(0, 3):
            pixels[i] = RED if state_left else OFF

        state_red = (t % flash_cycle) < 3
        for i in range(3, 10):
            pixels[i] = RED if state_red else OFF

        state_blue = not state_red
        for i in range(10, 17):
            pixels[i] = BLUE if state_blue else OFF

        for i in range(17, 20):
            pixels[i] = BLUE if state_left else OFF

        pixels.show()
        t += 1
        time.sleep(delay)


mode_functions = {
    "kitt_80s": kitt_80s,
    "kitt_2008": kitt_2008,
    "police": police
}


# =========================
# 灯光线程主循环
# =========================
def light_loop():
    while run_flag:
        if current_mode in mode_functions:
            clear()
            mode_functions[current_mode]()
        else:
            time.sleep(0.05)


# =========================
# 主程序
# =========================
if __name__ == "__main__":
    t = threading.Thread(target=light_loop)
    t.daemon = True
    t.start()

    try:
        print("Knight Rider LED Modes Ready")
        print("模式选择：kitt_80s / kitt_2008 / police")
        print("按 Ctrl+C 退出")

        while True:
            mode = input("> ").strip()
            with mode_lock:
                if mode in mode_functions:
                    current_mode = mode
                    print(f"√ 当前模式： {mode}")
                else:
                    print("X 未知模式，请重新输入")

    except KeyboardInterrupt:
        run_flag = False
        clear()
        t.join()
        print("\n 退出并关闭LED √")
