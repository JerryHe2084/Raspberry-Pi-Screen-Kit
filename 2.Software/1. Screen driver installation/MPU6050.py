import smbus
import math
import time
import os
import subprocess

# MPU6050 I2C 物理地址
MPU6050_ADDR=0x68

# MPU6050寄存器
MPU6050_SMPLRT_DIV=0x19
MPU6050_CONFIG=0x1a
MPU6050_GYRO_CONFIG=0x1b
MPU6050_ACCEL_CONFIG=0x1c
MPU6050_PWR_MGMT_1=0x6b

MPU6050_ACCX_DATA=0x3b
MPU6050_ACCY_DATA=0x3d
MPU6050_ACCZ_DATA=0x3f

# MPU6050 3轴陀螺仪的数据地址
MPU6050_GYROX_DATA=0x43
MPU6050_GYROY_DATA=0x45
MPU6050_GYROZ_DATA=0x47

class MPU6050(object):
    def __init__(self, address = MPU6050_ADDR, bus = 10,scal_acc=4,scal_gyro=1000,
                    threshold=4.0, eps=0.0, initial="normal"):
        self.bus = smbus.SMBus(bus)
        self.address = address
        
        self.bus.write_byte_data(self.address,MPU6050_SMPLRT_DIV,0x00)
        self.bus.write_byte_data(self.address,MPU6050_CONFIG,0x00)
        self.bus.write_byte_data(self.address,MPU6050_GYRO_CONFIG,0x08)
        self.bus.write_byte_data(self.address,MPU6050_ACCEL_CONFIG,0x00)
        self.bus.write_byte_data(self.address,MPU6050_PWR_MGMT_1,0x00)
        # ---------- 初始化完成，立即禁用不需要的传感器 ----------
        self.disable_sensors()


        self.scal_acc = 65536.0/scal_acc/9.8
        self.scal_gyro = 65536.0/scal_gyro

        self.T = float(threshold)
        self.eps = float(eps)
        self.state = initial
        self.prev_ax = None
        self.prev_ay = None

  
    def red_word_2c(self,addr):
        high = self.bus.read_byte_data(self.address,addr)
        low = self.bus.read_byte_data(self.address,addr + 1)
        val = (high<<8)+low
        if (val>=0x8000):
            return -((65535-val)+1)
        else: 
            return val
                
    def get_rawAcc(self):
        rawAccX = self.red_word_2c(MPU6050_ACCX_DATA);
        rawAccY = self.red_word_2c(MPU6050_ACCY_DATA);
        rawAccZ = self.red_word_2c(MPU6050_ACCZ_DATA);
        return rawAccX,rawAccY,rawAccZ
        
    def get_ACC(self):
        rawAccX,rawAccY,rawAccZ = self.get_rawAcc()
        accX = rawAccX/self.scal_acc
        accY = rawAccY/self.scal_acc
        accZ = rawAccZ/self.scal_acc
        return accX,accY,accZ
        
    # 禁用相关采样（省电）
    def disable_sensors(self):
        self.bus.write_byte_data(self.address, 0x6C, 0x07)  # 0000 0111 禁用陀螺仪
        current_pwr_mgmt_1 = self.bus.read_byte_data(self.address, 0x6B)
        self.bus.write_byte_data(self.address, 0x6B, current_pwr_mgmt_1 | 0x08)  # 禁用温度传感器
        self.bus.write_byte_data(self.address, 0x6A, 0x00)  # 禁用DMP   

    # 正向判断
    @staticmethod
    def _cross_pos(prev_v, v, thr, eps):
        return prev_v is not None and prev_v <= (thr - eps) and v > (thr + eps)

    # 反向判断
    @staticmethod
    def _cross_neg(prev_v, v, thr, eps):
        return prev_v is not None and prev_v >= (-thr + eps) and v < (-thr - eps)

    # 函数：判断方向并返回旋转值
    def update(self, ax, ay):
        if self.prev_ax is None or self.prev_ay is None:
            self.prev_ax, self.prev_ay = float(ax), float(ay)
            return self.state  # 初始给出默认状态

        ax, ay = float(ax), float(ay)
        prev_state = self.state  # 保存当前状态以便比较

        # === 顺序检测，哪个先满足就切换 ===
        # 注意：不检测当前状态，只检测另外三个
        if self.state != "90" and self._cross_pos(self.prev_ax, ax, self.T, self.eps):
            self.state = "90"
        elif self.state != "270" and self._cross_neg(self.prev_ax, ax, self.T, self.eps):
            self.state = "270"
        elif self.state != "normal" and self._cross_pos(self.prev_ay, ay, self.T, self.eps):
            self.state = "normal"
        elif self.state != "180" and self._cross_neg(self.prev_ay, ay, self.T, self.eps):
            self.state = "180"

        # 更新历史值
        self.prev_ax, self.prev_ay = ax, ay

        # 检查状态是否变化
        if self.state != prev_state:
            return self.state
        return None
        
# 主循环
if __name__ == "__main__":
    m_MPU = MPU6050(address = 0x68)
    current_rotation = "normal" # 初始化默认值
    env = os.environ.copy()
    env["WAYLAND_DISPLAY"] = "wayland-0"
    env["XDG_RUNTIME_DIR"] = "/run/user/1000"  # 替换成你实际查到的值

    try:
        while True:
            acc_x,acc_y,acc_z=m_MPU.get_ACC()
            # 判断 MPU-6050 X/Y轴加速度值，并
            new_rotation = m_MPU.update(acc_x, acc_y)

            if new_rotation and new_rotation != current_rotation:
                # 执行命令（设置环境变量）
                cmd = ["wlr-randr", "--output", "DSI-1", "--transform", new_rotation]

                try:
                    subprocess.run(cmd, env=env, check=True)
                    current_rotation = new_rotation
                except Exception:  # 静默忽略所有错误
                    pass
    
            time.sleep(0.5)  # 每 0.5 秒检查一次，避免高负载    
        
    except Exception:  # 静默退出
            pass
        
        
      
        
        