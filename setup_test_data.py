# -*- coding: utf-8 -*-
"""一键重置数据库并填充测试数据（每个子类至少一个物料）"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from warehouse_mcp.db.database import init_db, get_db, CATEGORIES

# ---- 第 1 步：重建数据库 ----
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "warehouse.db")
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
init_db()

print("[1/3] 数据库已重建")

# ---- 第 2 步：创建标签库 ----
tags_data = [
    # 产品系列标签
    ("Arduino Uno", "ATmega328P 微控制器，5V逻辑，14路数字IO/6路模拟输入，入门级开发板，Arduino IDE，丰富的Shield扩展生态"),
    ("Arduino Mega", "ATmega2560，54路数字IO，16路模拟输入，256KB Flash，适合大型项目"),
    ("ESP32", "乐鑫双核MCU @240MHz，内置WiFi 802.11b/g/n和BLE 4.2，520KB SRAM，支持Arduino/MicroPython/ESP-IDF，IoT首选"),
    ("ESP32-S3", "乐鑫双核Xtensa LX7 @240MHz，WiFi+BLE5.0，自带神经网络加速器，适合边缘AI"),
    ("ESP8266", "乐鑫单核WiFi MCU @80/160MHz，低功耗低成本，NodeMCU固件，适合简单IoT"),
    ("STM32F1", "ARM Cortex-M3 @72MHz，经典入门MCU，HAL库/标准库，STM32CubeIDE，教学和工业控制常用"),
    ("STM32F4", "ARM Cortex-M4 @168MHz，带DSP+FPU，高性能，适合信号处理和实时控制"),
    ("树莓派4B", "Broadcom BCM2711，四核Cortex-A72，4GB/8GB RAM，双HDMI，Linux系统，适合视觉、边缘计算、教学"),
    ("树莓派Pico", "RP2040双核M0+ @133MHz，264KB SRAM，支持MicroPython/C/C++，超低成本入门板"),
    ("K210", "RISC-V双核+KPU神经网络加速器，适合边缘AI和视觉识别"),

    # 传感类
    ("HC-SR04", "超声波测距模块，2cm-400cm，5V，TRIG/ECHO接口，用于避障、距离检测、液位测量"),
    ("MPU6050", "6轴IMU（3轴加速度+3轴陀螺仪），I2C接口，DMP姿态解算，用于平衡车、无人机、姿态检测"),
    ("DHT11", "数字温湿度传感器，精度±2°C/±5%RH，单总线，低成本环境监测入门"),
    ("DHT22", "高精度数字温湿度，精度±0.5°C/±2%RH，比DHT11更准确，适合精密环境监测"),
    ("红外避障", "红外对管传感器，检测距离2-30cm可调，数字输出，用于循迹小车、避障"),
    ("光敏电阻", "光敏传感器模块，模拟+数字双输出，阈值可调，光控开关和亮度检测"),

    # 驱动/电机类
    ("L298N", "双H桥电机驱动模块，驱动电压5-35V，峰值2A，可驱动2个直流电机或1个步进电机，散热好但效率一般"),
    ("TB6612", "双H桥MOSFET电机驱动，峰值3.2A，比L298N效率高发热少，适合电池供电小车"),
    ("A4988", "步进电机驱动模块，最大2A，支持1/16微步进，适合3D打印机和CNC"),
    ("TT直流电机", "小型直流减速电机，1:48减速比，常用3-6V，适合教学小车和模型"),
    ("MG996R", "金属齿轮大扭力舵机，180°，堵转10kg·cm，适合机械臂和大型模型"),
    ("SG90", "微型塑料齿轮舵机，180°，1.2kg·cm，适合小型关节和教学"),

    # 通信类
    ("HC-05", "蓝牙2.0串口透传模块，主从一体，AT指令配置，短距离无线通信"),
    ("NRF24L01", "2.4GHz无线收发，SPI接口，126频道，低功耗，多对一通信，适合组网"),
    ("LoRa", "SX1278低功耗远距离无线模块，433MHz，3-5km视距，适合户外IoT和农业监测"),
    ("ESP8266-WiFi", "WiFi 802.11b/g/n，支持AP+Station模式，适合物联网接入"),

    # 显示类
    ("OLED", "SSD1306驱动，0.96寸128x64，I2C/SPI，蓝/白色，小巧显示模块"),
    ("LCD1602", "16x2字符液晶，I2C转接，蓝底白字，经典信息显示"),
    ("WS2812", "可编程RGB LED灯带，单线控制，256级亮度，适合氛围灯和创意项目"),

    # 电源类
    ("18650电池", "锂离子电池3.7V，容量2500-3500mAh，可充电，常见于移动电源和模型供电"),
    ("LM2596", "DC-DC降压模块，输入4.5-40V，输出1.25-37V可调，最大3A，高效率"),
    ("TP4056", "单节锂电池充电模块，miniUSB输入，带保护板，1A充电"),

    # 电子元件类
    ("电阻", "碳膜/金属膜电阻，1/4W，常用E12系列阻值"),
    ("电容", "电解/陶瓷/钽电容，去耦/滤波/储能"),
    ("74HC595", "8位移位寄存器，串入并出，SPI驱动，扩展IO口"),
    ("AMS1117", "低压差线性稳压器，固定3.3V输出，SOT-223封装"),

    # 连接/结构类
    ("杜邦线", "公-母/母-母排线，40P彩色，2.54mm间距，实验连接必备"),
    ("面包板", "830孔免焊实验板，自带电源轨，2.54mm间距，快速原型验证"),
    ("排针排母", "2.54mm间距排针排母，单排/双排，焊接或压接"),

    # 工具
    ("万用表", "数字多用表，电压/电流/电阻/通断/二极管，自动量程"),
    ("电烙铁", "936可调温焊台，60W，200-480°C，焊接电子元件"),
    ("螺丝刀套装", "精密螺丝刀多合一，十字/一字/六角/梅花，拆装电子产品"),

    # 耗材
    ("焊锡丝", "无铅或63/37有铅焊锡丝，0.8mm，助焊剂芯，焊接耗材"),
    ("热缩管", "聚烯烃热缩套管，2:1收缩比，绝缘保护"),
    ("电工胶带", "PVC电气绝缘胶带，耐压600V，线束包扎绝缘"),

    # 补充：第二轮丰富 — 更多常见产品系列
    ("STM32F103C8T6", "意法半导体 Cortex-M3 @72MHz 核心板（Blue Pill），低成本高性能，STM32入门和通用控制首选"),
    ("MPU9250", "9轴IMU（3轴加速度+3轴陀螺仪+3轴磁力计），I2C/SPI，姿态解算，适合四轴和导航"),
    ("ADXL345", "三轴加速度计，I2C/SPI，±2/4/8/16g可调，低功耗，适合运动检测和计步"),
    ("HX711", "24位高精度称重传感器ADC，配套压力传感器，适合电子秤和压力检测"),
    ("PIR人体红外", "HC-SR501热释电红外传感器，检测人体移动，适合安防和自动感应"),
    ("BH1750", "数字光照度传感器，I2C，1-65535lux，适合环境光检测和自动调光"),
    ("火焰传感器", "红外火焰检测，数字+模拟输出，适合火焰报警和机器人灭火"),
    ("土壤湿度", "电容式/电阻式土壤湿度检测，适合智能灌溉和农业IoT"),
    ("SHT30", "高精度数字温湿度传感器，I2C，±0.3°C/±2%RH，工业级，适合精密监测"),
    ("MLX90614", "非接触式红外测温传感器，I2C，-70~380°C，适合体温和工业测温"),
    ("无刷电调", "无刷电机电子调速器，PWM调速，适合四轴无人机和无刷电机驱动"),
    ("L9110", "双H桥电机驱动模块，2.5-12V，适合小型直流电机驱动"),
    ("DRV8825", "步进电机驱动模块，最大2.2A，支持1/32微步进，比A4988电流更大"),
    ("MG90S", "金属齿轮微型舵机，180°，2kg·cm，比SG90更耐用的升级款"),
    ("微型水泵", "DC3-6V微型隔膜泵/潜水泵，适合浇水和循环系统"),
    ("电磁阀", "12V常闭电磁阀，控制液体/气体通断，适合自动灌溉和流体控制"),
    ("振动马达", "微型偏心振动电机，适合手机振动提示和触觉反馈"),
    ("LCD12864", "128x64点阵液晶，带字库，ST7920驱动，适合中文显示和菜单"),
    ("数码管", "共阴/共阳7段数码管，显示数字和简单字符"),
    ("无源蜂鸣器", "无源蜂鸣器，PWM驱动发声，适合提示音和简单音乐"),
    ("按钮开关", "轻触按键/自锁开关，输入控制和电源开关"),
    ("MP1584", "DC-DC降压模块，输入4.5-28V，输出可调，最大3A，高效率小体积"),
    ("太阳能板", "5V/6V小型太阳能电池板，适合户外供电和太阳能充电项目"),
    ("电池盒", "1-4节5号/18650电池盒，带开关和导线，便携供电"),
    ("LED", "5mm/3mm直插发光二极管，红绿蓝白多种颜色，指示和照明"),
    ("电位器", "旋转式可调电阻，10K/100K常用，分压和调参"),
    ("信号发生器", "函数信号发生器，输出正弦/方波/三角波，电路测试"),
    ("热熔胶枪", "热熔胶枪+胶棒，快速固定和绝缘"),
    ("助焊膏", "免清洗助焊膏，提高焊接质量和润湿性"),
    ("吸锡带", "铜编织吸锡带，去除多余焊锡，返修必备"),
    ("导热硅脂", "导热硅脂，CPU/功率器件散热填充"),
    ("PLA耗材", "3D打印PLA耗材，1.75mm，多种颜色，快速原型"),

    # 项目/用途类标签
    ("物联网", "IoT项目：传感器采集+无线传输+云平台，常用ESP32/LoRa/MQTT"),
    ("智能小车", "循迹/避障/遥控小车项目，需要电机、驱动板、传感器、电池"),
    ("无人机", "四轴/六轴飞行器，需要飞控、无刷电机、电调、IMU、电池、遥控"),
    ("机器人", "机器臂/仿生机器人，需要舵机/步进电机、结构件、控制器"),
    ("智能家居", "家庭自动化：温湿度/光照采集+继电器控制+无线通信"),
    ("环境监测", "温湿度/气压/PM2.5采集+数据上传，适合农业和气象"),
    ("低功耗", "电池供电场景，需要低功耗MCU、睡眠唤醒、高效电源"),
    ("教学入门", "适合课程实验和教学演示，使用Arduino/STM32入门板"),
    ("无线通信", "WiFi/蓝牙/LoRa/2.4GHz射频，各种无线连接方案"),

    # 机械元件类标签
    ("紧固件", "螺丝/螺母/垫片/塞打螺丝等机械连接紧固件，结构组装必备"),
    ("齿轮齿条", "直齿轮与齿条，模数1常用，用于直线运动与传动"),
    ("丝杆传动", "T8丝杆+螺母，用于直线运动、3D打印机Z轴和机械臂升降"),
    ("轴承", "深沟球/法兰轴承，用于旋转支撑和减小摩擦"),
    ("碳板", "碳纤维板材，轻质高强，适合无人机机架和机械臂结构"),
    ("环氧板", "FR4玻纤环氧树脂板，绝缘耐温，适合电路底座和结构件"),
    ("角码", "L型直角连接件，用于铝型材和板材的直角固定"),
    ("铝型材", "2020欧标铝型材，用于搭建机器人框架和结构"),
    ("机械结构", "机械传动与结构件，齿轮/丝杆/轴承/紧固件等"),
]

conn = get_db()
try:
    for name, desc in tags_data:
        conn.execute("INSERT OR REPLACE INTO tags (name, description) VALUES (?, ?)", (name, desc))
    conn.commit()
finally:
    conn.close()

print(f"[2/3] 标签库已创建：{len(tags_data)} 个标签")

# ---- 第 3 步：填充物料数据 ----
from warehouse_mcp.tools.add_material import add_material

def add(name, cat, sub, **kw):
    """快捷入库，忽略返回值"""
    kwargs = {"name": name, "category": cat, "sub_category": sub}
    kwargs.update(kw)
    r = add_material(**kwargs)
    if "成功" not in r:
        print(f"  WARN: {r}")
    return r

test_data = [
    # ==================== 主控板 MC ====================
    # MCU/单片机
    ("Arduino Uno R3 开发板",  "主控板", "MCU/单片机", {"model": "Uno R3", "quantity": 5, "tags": ["Arduino Uno", "教学入门"]}),
    ("STM32F407 开发板",       "主控板", "MCU/单片机", {"model": "STM32F407VET6", "quantity": 3, "tags": ["STM32F4"]}),
    ("ESP32-S3 开发板",         "主控板", "MCU/单片机", {"model": "ESP32-S3-DevKitC", "quantity": 4, "tags": ["ESP32-S3", "物联网", "无线通信"]}),

    # 单板机SBC
    ("树莓派 4B",             "主控板", "单板机SBC", {"model": "Raspberry Pi 4B 4GB", "quantity": 2, "tags": ["树莓派4B", "物联网"]}),
    ("树莓派 Pico",           "主控板", "单板机SBC", {"model": "RP2040", "quantity": 6, "tags": ["树莓派Pico", "教学入门"]}),

    # FPGA/CPLD
    ("EP4CE6 FPGA 开发板",     "主控板", "FPGA/CPLD", {"model": "EP4CE6E22C8N", "quantity": 1, "tags": []}),

    # DSP
    ("TMS320F28335 DSP开发板", "主控板", "DSP", {"model": "TMS320F28335", "quantity": 1, "tags": []}),

    # 其他主控
    ("Arduino Mega 2560",     "主控板", "其他", {"model": "Mega 2560", "quantity": 2, "tags": ["Arduino Mega", "机器人"]}),

    # ==================== 传感模块 SN ====================
    # 距离/位置
    ("HC-SR04 超声波测距模块", "传感模块", "距离/位置", {"model": "HC-SR04", "quantity": 8, "tags": ["HC-SR04", "智能小车"]}),
    ("VL53L0X 激光测距模块",   "传感模块", "距离/位置", {"model": "VL53L0X", "quantity": 3, "tags": ["机器人", "高精度"]}),

    # 温度/湿度
    ("DHT11 温湿度传感器",     "传感模块", "温度/湿度", {"model": "DHT11", "quantity": 10, "tags": ["DHT11", "环境监测", "教学入门"]}),
    ("DHT22 温湿度传感器",     "传感模块", "温度/湿度", {"model": "DHT22", "quantity": 4, "tags": ["DHT22", "环境监测", "高精度"]}),
    ("DS18B20 防水温度探头",   "传感模块", "温度/湿度", {"model": "DS18B20", "quantity": 5, "tags": ["环境监测"]}),

    # 运动/姿态(IMU)
    ("MPU6050 六轴传感器模块", "传感模块", "运动/姿态(IMU)", {"model": "MPU6050 GY-521", "quantity": 4, "tags": ["MPU6050", "无人机", "机器人"]}),

    # 光/颜色/图像
    ("光敏电阻传感器模块",    "传感模块", "光/颜色/图像", {"model": "KY-018", "quantity": 6, "tags": ["光敏电阻", "智能家居", "教学入门"]}),
    ("TCS34725 颜色传感器",   "传感模块", "光/颜色/图像", {"model": "TCS34725", "quantity": 2, "tags": ["机器人"]}),

    # 环境(气压/气体/声音)
    ("BMP280 气压温度传感器", "传感模块", "环境(气压/气体/声音)", {"model": "BMP280", "quantity": 3, "tags": ["环境监测", "无人机"]}),
    ("MQ-2 烟雾气体传感器",    "传感模块", "环境(气压/气体/声音)", {"model": "MQ-2", "quantity": 2, "tags": ["智能家居"]}),

    # 电流/电压
    ("INA219 电流电压传感器",  "传感模块", "电流/电压", {"model": "INA219", "quantity": 3, "tags": ["低功耗"]}),

    # 生物/医学
    ("MAX30102 心率血氧传感器","传感模块", "生物/医学", {"model": "MAX30102", "quantity": 2, "tags": []}),

    # 其他传感
    ("红外避障传感器模块",    "传感模块", "其他", {"model": "TCRT5000", "quantity": 6, "tags": ["红外避障", "智能小车", "教学入门"]}),

    # ==================== 执行/驱动 AC ====================
    # 直流电机
    ("TT 直流减速电机",         "执行/驱动", "直流电机", {"model": "TT Motor 1:48", "quantity": 8, "tags": ["TT直流电机", "智能小车"]}),
    ("N20 微型减速电机",        "执行/驱动", "直流电机", {"model": "N20 6V 100RPM", "quantity": 4, "tags": ["机器人"]}),

    # 步进电机
    ("28BYJ-48 步进电机+驱动板","执行/驱动", "步进电机", {"model": "28BYJ-48 5V", "quantity": 4, "tags": ["机器人"]}),
    ("NEMA17 步进电机",         "执行/驱动", "步进电机", {"model": "42BYGH 1.8deg", "quantity": 2, "tags": []}),

    # 舵机/伺服
    ("SG90 微型舵机",           "执行/驱动", "舵机/伺服", {"model": "SG90", "quantity": 6, "tags": ["SG90", "教学入门", "机器人"]}),
    ("MG996R 大扭力舵机",       "执行/驱动", "舵机/伺服", {"model": "MG996R", "quantity": 3, "tags": ["MG996R", "机器人"]}),

    # 电机驱动板
    ("L298N 电机驱动模块",     "执行/驱动", "电机驱动板", {"model": "L298N", "quantity": 5, "tags": ["L298N", "智能小车"]}),
    ("TB6612 电机驱动模块",    "执行/驱动", "电机驱动板", {"model": "TB6612FNG", "quantity": 3, "tags": ["TB6612", "智能小车", "低功耗"]}),
    ("A4988 步进电机驱动模块",  "执行/驱动", "电机驱动板", {"model": "A4988", "quantity": 4, "tags": ["A4988"]}),

    # 继电器/接触器
    ("2路继电器模块",           "执行/驱动", "继电器/接触器", {"model": "SRD-05VDC 2CH", "quantity": 4, "tags": ["智能家居"]}),
    ("4路继电器模块",           "执行/驱动", "继电器/接触器", {"model": "SRD-05VDC 4CH", "quantity": 2, "tags": ["智能家居"]}),

    # 气动/液压
    ("微型真空泵",             "执行/驱动", "气动/液压", {"model": "DC12V 120kPa", "quantity": 1, "tags": []}),

    # 其他执行
    ("PCA9685 16路舵机驱动板", "执行/驱动", "其他", {"model": "PCA9685", "quantity": 2, "tags": ["机器人"]}),

    # ==================== 通信模块 CM ====================
    # 蓝牙
    ("HC-05 蓝牙串口模块",     "通信模块", "蓝牙", {"model": "HC-05", "quantity": 6, "tags": ["HC-05", "无线通信"]}),

    # WiFi
    ("ESP-01S WiFi模块",       "通信模块", "WiFi", {"model": "ESP8266-01S", "quantity": 5, "tags": ["ESP8266-WiFi", "物联网", "无线通信"]}),

    # LoRa/NB-IoT
    ("LoRa SX1278 433MHz模块", "通信模块", "LoRa/NB-IoT", {"model": "SX1278 433M", "quantity": 3, "tags": ["LoRa", "物联网", "低功耗", "环境监测"]}),
    ("LoRa SX1262 868MHz模块", "通信模块", "LoRa/NB-IoT", {"model": "SX1262 868M", "quantity": 2, "tags": ["LoRa", "低功耗"]}),

    # 射频/NFC
    ("NRF24L01 2.4G无线模块",  "通信模块", "射频/NFC", {"model": "NRF24L01+", "quantity": 5, "tags": ["NRF24L01", "无线通信"]}),
    ("RC522 RFID/NFC模块",     "通信模块", "射频/NFC", {"model": "MFRC522", "quantity": 3, "tags": []}),

    # 以太网/CAN/485
    ("ENC28J60 以太网模块",    "通信模块", "以太网/CAN/485", {"model": "ENC28J60", "quantity": 2, "tags": ["物联网"]}),
    ("MAX485 RS485模块",       "通信模块", "以太网/CAN/485", {"model": "MAX485", "quantity": 4, "tags": ["环境监测"]}),

    # 其他通信
    ("IR 红外接收发射模块",    "通信模块", "其他", {"model": "VS1838B+IR LED", "quantity": 5, "tags": ["智能家居"]}),

    # ==================== 显示/交互 DP ====================
    # OLED/LCD
    ("0.96寸 OLED显示屏(蓝)",  "显示/交互", "OLED/LCD", {"model": "SSD1306 I2C", "quantity": 5, "tags": ["OLED"]}),
    ("1602 LCD 液晶屏(I2C)",   "显示/交互", "OLED/LCD", {"model": "LCD1602 I2C", "quantity": 4, "tags": ["LCD1602"]}),

    # LED/数码管
    ("WS2812 RGB灯带(1m 60灯)", "显示/交互", "LED/数码管", {"model": "WS2812B 60LED/m", "quantity": 3, "tags": ["WS2812"]}),
    ("TM1637 4位数码管模块",   "显示/交互", "LED/数码管", {"model": "TM1637", "quantity": 4, "tags": []}),

    # 按键/旋钮
    ("旋转编码器模块",         "显示/交互", "按键/旋钮", {"model": "KY-040", "quantity": 5, "tags": []}),

    # 蜂鸣器/扬声器
    ("有源蜂鸣器模块",         "显示/交互", "蜂鸣器/扬声器", {"model": "5V Active Buzzer", "quantity": 8, "tags": ["教学入门"]}),

    # 触摸屏
    ("3.5寸 TFT触摸屏",        "显示/交互", "触摸屏", {"model": "ILI9488 3.5in", "quantity": 2, "tags": ["物联网"]}),

    # 其他显示
    ("MAX7219 8x8点阵模块",   "显示/交互", "其他", {"model": "MAX7219", "quantity": 3, "tags": []}),

    # ==================== 电源模块 PW ====================
    # 电池
    ("18650 锂电池",            "电源模块", "电池", {"model": "18650 3.7V 2600mAh", "quantity": 10, "tags": ["18650电池", "智能小车", "低功耗"]}),
    ("9V 方块电池",             "电源模块", "电池", {"model": "6F22 9V", "quantity": 6, "tags": ["教学入门"]}),

    # 稳压/升降压
    ("LM2596 DC-DC 降压模块",   "电源模块", "稳压/升降压", {"model": "LM2596", "quantity": 8, "tags": ["LM2596", "智能小车"]}),
    ("MT3608 DC-DC 升压模块",   "电源模块", "稳压/升降压", {"model": "MT3608 2A", "quantity": 5, "tags": ["低功耗"]}),
    ("AMS1117-3.3V 稳压模块",   "电源模块", "稳压/升降压", {"model": "AMS1117-3.3", "quantity": 10, "tags": ["AMS1117"]}),

    # 充电管理
    ("TP4056 锂电池充电模块",   "电源模块", "充电管理", {"model": "TP4056 miniUSB", "quantity": 6, "tags": ["TP4056"]}),

    # 电源适配器
    ("12V 2A 电源适配器",       "电源模块", "电源适配器", {"model": "DC12V 2A", "quantity": 3, "tags": []}),

    # 其他电源
    ("面包板专用电源模块",     "电源模块", "其他", {"model": "MB-102 3.3V/5V", "quantity": 5, "tags": ["面包板"]}),

    # ==================== 电子元件 EC ====================
    # 电阻
    ("1/4W 电阻套装(30种阻值)", "电子元件", "电阻", {"model": "E12 10R-1M", "quantity": 3, "tags": ["电阻", "教学入门"], "is_consumable": True}),

    # 电容
    ("电解电容套装(12种容值)",  "电子元件", "电容", {"model": "10uF-1000uF", "quantity": 2, "tags": ["电容"], "is_consumable": True}),

    # 电感/磁珠
    ("色环电感套装",           "电子元件", "电感/磁珠", {"model": "1uH-1mH", "quantity": 2, "tags": [], "is_consumable": True}),

    # 二极管
    ("1N4007 整流二极管",       "电子元件", "二极管", {"model": "1N4007 1A 1000V", "quantity": 50, "tags": [], "is_consumable": True}),
    ("1N4148 开关二极管",       "电子元件", "二极管", {"model": "1N4148", "quantity": 50, "tags": [], "is_consumable": True}),

    # 三极管/MOS
    ("2N2222 NPN三极管",       "电子元件", "三极管/MOS", {"model": "2N2222", "quantity": 20, "tags": [], "is_consumable": True}),
    ("IRF520 MOSFET驱动模块",   "电子元件", "三极管/MOS", {"model": "IRF520", "quantity": 4, "tags": []}),

    # IC/运放
    ("NE555 定时器模块",        "电子元件", "IC/运放", {"model": "NE555", "quantity": 5, "tags": ["教学入门"]}),
    ("74HC595 移位寄存器",      "电子元件", "IC/运放", {"model": "74HC595", "quantity": 6, "tags": ["74HC595"]}),
    ("LM358 双运放模块",        "电子元件", "IC/运放", {"model": "LM358", "quantity": 4, "tags": []}),

    # 晶振
    ("晶振套装(常用频率)",      "电子元件", "晶振", {"model": "8M/11.0592M/12M/16M", "quantity": 3, "tags": [], "is_consumable": True}),

    # 其他电子元件
    ("光耦隔离模块",           "电子元件", "其他", {"model": "PC817 4CH", "quantity": 3, "tags": []}),

    # ==================== 连接/结构 CN ====================
    # 导线/排线
    ("公母杜邦线(40P 20cm)",   "连接/结构", "导线/排线", {"model": "M-F 40P 20cm", "quantity": 10, "tags": ["杜邦线", "教学入门"], "is_consumable": True}),
    ("母母杜邦线(40P 20cm)",   "连接/结构", "导线/排线", {"model": "F-F 40P 20cm", "quantity": 8, "tags": ["杜邦线"], "is_consumable": True}),

    # 接插件/排针
    ("排针排母套装",           "连接/结构", "接插件/排针", {"model": "2.54mm 40P M+F", "quantity": 5, "tags": ["排针排母"], "is_consumable": True}),
    ("USB-B 母座转DIP",        "连接/结构", "接插件/排针", {"model": "USB-B Female DIP", "quantity": 8, "tags": [], "is_consumable": True}),

    # 面包板/洞洞板
    ("830孔面包板",            "连接/结构", "面包板/洞洞板", {"model": "830TiePoints MB-102", "quantity": 6, "tags": ["面包板", "教学入门"]}),
    ("5x7cm 洞洞板",           "连接/结构", "面包板/洞洞板", {"model": "5x7cm 2.54mm", "quantity": 10, "tags": [], "is_consumable": True}),

    # 紧固件
    ("M3 螺丝螺母铜柱套装",    "连接/结构", "紧固件", {"model": "M3 6mm-20mm", "quantity": 3, "tags": ["机器人"], "is_consumable": True}),

    # 结构件(支架/底盘/轮子)
    ("智能小车底盘(亚克力)",   "连接/结构", "结构件(支架/底盘/轮子)", {"model": "2WD Chassis", "quantity": 3, "tags": ["智能小车"]}),
    ("麦克纳姆轮套装(4个)",    "连接/结构", "结构件(支架/底盘/轮子)", {"model": "Mecanum 60mm", "quantity": 1, "tags": ["机器人"]}),

    # 其他连接
    ("XT60 电源接头(公母对)",  "连接/结构", "其他", {"model": "XT60 M+F", "quantity": 10, "tags": [], "is_consumable": True}),

    # ==================== 工具 TL ====================
    # 测量仪器
    ("数字万用表",             "工具", "测量仪器", {"model": "VC890C+", "quantity": 2, "tags": ["万用表"]}),
    ("USB 逻辑分析仪",         "工具", "测量仪器", {"model": "Saleae Clone 8CH", "quantity": 2, "tags": []}),

    # 焊接工具
    ("936 恒温焊台",           "工具", "焊接工具", {"model": "936 60W", "quantity": 2, "tags": ["电烙铁"]}),
    ("烙铁头套装(5种)",        "工具", "焊接工具", {"model": "900M tips x5", "quantity": 2, "tags": ["电烙铁"], "is_consumable": True}),

    # 拆装工具
    ("精密螺丝刀套装(31合1)",  "工具", "拆装工具", {"model": "31in1", "quantity": 2, "tags": ["螺丝刀套装"]}),
    ("防静电镊子套装",         "工具", "拆装工具", {"model": "ESD tweezers x4", "quantity": 3, "tags": []}),

    # 电源/信号源
    ("DC可调电源模块",         "工具", "电源/信号源", {"model": "DPS3005", "quantity": 1, "tags": []}),

    # 其他工具
    ("热风枪",                "工具", "其他", {"model": "858D 700W", "quantity": 1, "tags": []}),

    # ==================== 耗材 CS ====================
    # 焊料/助焊剂
    ("无铅焊锡丝(0.8mm 100g)",  "耗材", "焊料/助焊剂", {"model": "Sn-Cu 0.8mm", "quantity": 5, "tags": ["焊锡丝"], "is_consumable": True}),
    ("松香助焊剂",              "耗材", "焊料/助焊剂", {"model": "Rosin Flux 50g", "quantity": 3, "tags": [], "is_consumable": True}),

    # 胶带/胶水
    ("电工绝缘胶带(黑色)",      "耗材", "胶带/胶水", {"model": "PVC 18mmx10m", "quantity": 4, "tags": ["电工胶带"], "is_consumable": True}),

    # 热缩管
    ("热缩管套装(5色 2.0-6.0mm)", "耗材", "热缩管", {"model": "2:1 ratio x5 sizes", "quantity": 3, "tags": ["热缩管"], "is_consumable": True}),

    # 清洁/防静电
    ("防静电手环",              "耗材", "清洁/防静电", {"model": "ESD Wrist Strap", "quantity": 5, "tags": []}),

    # 其他耗材
    ("扎带(3x100mm 100根)",    "耗材", "其他", {"model": "3x100mm", "quantity": 3, "tags": [], "is_consumable": True}),

    # ==================== 第二轮丰富 ====================
    # 主控板
    ("STM32F103C8T6 核心板",   "主控板", "MCU/单片机", {"model": "STM32F103C8T6 Blue Pill", "quantity": 8, "tags": ["STM32F103C8T6", "STM32F1", "教学入门"]}),
    ("Arduino Nano 开发板",    "主控板", "MCU/单片机", {"model": "Nano ATmega328P", "quantity": 6, "tags": ["Arduino Nano", "教学入门"]}),
    ("ESP8266 NodeMCU 开发板",  "主控板", "MCU/单片机", {"model": "NodeMCU V3", "quantity": 6, "tags": ["ESP8266", "物联网", "无线通信"]}),
    ("51单片机最小系统板",      "主控板", "MCU/单片机", {"model": "STC89C52RC", "quantity": 10, "tags": ["51单片机", "教学入门"]}),
    ("GD32F103 开发板",        "主控板", "MCU/单片机", {"model": "GD32F103C8T6", "quantity": 3, "tags": ["STM32F1"]}),
    ("树莓派 Pico W",          "主控板", "单板机SBC", {"model": "RP2040 + WiFi", "quantity": 4, "tags": ["树莓派Pico", "物联网"]}),

    # 传感模块
    ("MPU9250 九轴传感器模块", "传感模块", "运动/姿态(IMU)", {"model": "MPU9250 GY-9250", "quantity": 3, "tags": ["MPU9250", "无人机", "机器人"]}),
    ("ADXL345 三轴加速度模块", "传感模块", "运动/姿态(IMU)", {"model": "ADXL345", "quantity": 3, "tags": ["ADXL345", "低功耗"]}),
    ("HX711 称重传感器模块",   "传感模块", "其他", {"model": "HX711+1kg LoadCell", "quantity": 3, "tags": ["HX711", "压力/称重"]}),
    ("HC-SR501 人体红外模块",  "传感模块", "其他", {"model": "HC-SR501 PIR", "quantity": 5, "tags": ["PIR人体红外", "智能家居", "红外传感器"]}),
    ("A3144 霍尔传感器模块",   "传感模块", "其他", {"model": "A3144E", "quantity": 8, "tags": ["霍尔传感器"]}),
    ("LM393 声音传感器模块",   "传感模块", "环境(气压/气体/声音)", {"model": "LM393 Sound", "quantity": 5, "tags": ["声音传感器", "教学入门"]}),
    ("BH1750 光照传感器模块",  "传感模块", "光/颜色/图像", {"model": "BH1750 GY-302", "quantity": 4, "tags": ["BH1750", "光敏传感器", "智能家居"]}),
    ("火焰传感器模块",         "传感模块", "光/颜色/图像", {"model": "KY-026", "quantity": 4, "tags": ["火焰传感器"]}),
    ("电容式土壤湿度传感器",   "传感模块", "其他", {"model": "Capacitive Soil", "quantity": 6, "tags": ["土壤湿度", "环境监测"]}),
    ("SHT30 高精度温湿度模块", "传感模块", "温度/湿度", {"model": "SHT30-D", "quantity": 2, "tags": ["SHT30", "环境监测", "高精度"]}),
    ("MLX90614 红外测温模块",  "传感模块", "温度/湿度", {"model": "MLX90614", "quantity": 2, "tags": ["MLX90614"]}),
    ("NEO-6M GPS 定位模块",    "传感模块", "其他", {"model": "NEO-6M", "quantity": 2, "tags": ["GPS/北斗"]}),
    ("GP2Y1010AU0F 粉尘传感器", "传感模块", "环境(气压/气体/声音)", {"model": "GP2Y1010AU0F", "quantity": 2, "tags": ["气体传感器", "环境监测"]}),

    # 执行/驱动
    ("A2212 无刷电机",         "执行/驱动", "其他", {"model": "A2212 1000KV", "quantity": 4, "tags": ["无刷电机", "无人机"]}),
    ("30A 无刷电调",           "执行/驱动", "其他", {"model": "30A ESC", "quantity": 4, "tags": ["无刷电调", "无人机"]}),
    ("JGA25-370 编码减速电机", "执行/驱动", "直流电机", {"model": "JGA25-370 12V", "quantity": 4, "tags": ["编码电机", "机器人", "减速电机"]}),
    ("L9110 电机驱动模块",     "执行/驱动", "电机驱动板", {"model": "L9110S", "quantity": 4, "tags": ["L9110", "智能小车"]}),
    ("DRV8825 步进驱动模块",   "执行/驱动", "电机驱动板", {"model": "DRV8825", "quantity": 3, "tags": ["DRV8825"]}),
    ("MG90S 金属舵机",         "执行/驱动", "舵机/伺服", {"model": "MG90S", "quantity": 5, "tags": ["MG90S", "机器人"]}),
    ("微型隔膜水泵",           "执行/驱动", "气动/液压", {"model": "DC12V 370", "quantity": 2, "tags": ["微型水泵"]}),
    ("12V 电磁阀",             "执行/驱动", "气动/液压", {"model": "12V N/C", "quantity": 2, "tags": ["电磁阀"]}),
    ("微型振动马达",           "执行/驱动", "其他", {"model": "DC3V 10mm", "quantity": 10, "tags": ["振动马达"]}),

    # 通信模块
    ("CH340 USB转TTL模块",     "通信模块", "其他", {"model": "CH340G", "quantity": 8, "tags": ["USB转串口", "教学入门"]}),
    ("CP2102 USB转TTL模块",    "通信模块", "其他", {"model": "CP2102", "quantity": 4, "tags": ["USB转串口"]}),
    ("CC2530 Zigbee 模块",     "通信模块", "其他", {"model": "CC2530", "quantity": 3, "tags": ["Zigbee", "物联网"]}),
    ("HM-10 BLE 蓝牙模块",     "通信模块", "蓝牙", {"model": "HM-10 CC2541", "quantity": 4, "tags": ["无线通信"]}),
    ("Air724UG 4G模块",        "通信模块", "其他", {"model": "Air724UG", "quantity": 2, "tags": ["物联网"]}),

    # 显示/交互
    ("LCD12864 液晶屏(带字库)", "显示/交互", "OLED/LCD", {"model": "ST7920", "quantity": 3, "tags": ["LCD12864"]}),
    ("0.91寸 OLED显示屏",      "显示/交互", "OLED/LCD", {"model": "SSD1306 0.91in", "quantity": 4, "tags": ["OLED"]}),
    ("共阴7段数码管(4位)",     "显示/交互", "LED/数码管", {"model": "4-digit CC", "quantity": 6, "tags": ["数码管"], "is_consumable": True}),
    ("无源蜂鸣器",             "显示/交互", "蜂鸣器/扬声器", {"model": "5V Passive", "quantity": 10, "tags": ["无源蜂鸣器", "教学入门"], "is_consumable": True}),
    ("轻触按键模块",           "显示/交互", "按键/旋钮", {"model": "Tact Switch x4", "quantity": 5, "tags": ["按钮开关", "教学入门"]}),

    # 电源模块
    ("MP1584 DC-DC 降压模块",  "电源模块", "稳压/升降压", {"model": "MP1584 3A", "quantity": 6, "tags": ["MP1584", "降压模块"]}),
    ("5V 6W 太阳能板",         "电源模块", "电池", {"model": "5V 1.2A", "quantity": 2, "tags": ["太阳能板"]}),
    ("2节18650 电池盒",        "电源模块", "电池", {"model": "2x18650 with switch", "quantity": 6, "tags": ["电池盒"]}),
    ("4节5号电池盒",           "电源模块", "电池", {"model": "4xAA with switch", "quantity": 8, "tags": ["电池盒"]}),
    ("CR2032 纽扣电池",        "电源模块", "电池", {"model": "CR2032 3V", "quantity": 20, "tags": [], "is_consumable": True}),
    ("7.4V 2S 航模锂电池",     "电源模块", "电池", {"model": "2S 2200mAh 25C", "quantity": 2, "tags": ["无人机"]}),

    # 电子元件
    ("5mm LED 发光二极管套装", "电子元件", "其他", {"model": "5mm R/G/B/Y/W x100", "quantity": 5, "tags": ["LED", "教学入门"], "is_consumable": True}),
    ("1N4733 稳压二极管套装",  "电子元件", "二极管", {"model": "1N47xx 3.3-12V", "quantity": 20, "tags": [], "is_consumable": True}),
    ("保险丝套装",             "电子元件", "其他", {"model": "5x20mm 0.5-10A", "quantity": 3, "tags": [], "is_consumable": True}),
    ("10K 电位器",             "电子元件", "其他", {"model": "WH148 10K", "quantity": 20, "tags": ["电位器"], "is_consumable": True}),
    ("轻触开关(6x6x5mm)",      "电子元件", "其他", {"model": "Tact 6x6x5", "quantity": 100, "tags": ["按钮开关"], "is_consumable": True}),
    ("S8050/S8550 三极管套装", "电子元件", "三极管/MOS", {"model": "S8050+S8550", "quantity": 10, "tags": [], "is_consumable": True}),
    ("AO3400 N沟道MOS管",      "电子元件", "三极管/MOS", {"model": "AO3400", "quantity": 20, "tags": [], "is_consumable": True}),
    ("7805 三端稳压管",        "电子元件", "IC/运放", {"model": "L7805CV", "quantity": 15, "tags": [], "is_consumable": True}),
    ("陶瓷电容套装(12种容值)", "电子元件", "电容", {"model": "10pF-100nF", "quantity": 4, "tags": ["电容"], "is_consumable": True}),
    ("NTC 热敏电阻(10K)",      "电子元件", "电阻", {"model": "NTC 10K 1%", "quantity": 20, "tags": [], "is_consumable": True}),

    # 连接/结构
    ("USB 转接线套装",         "连接/结构", "导线/排线", {"model": "micro/mini/typeC x3", "quantity": 5, "tags": ["教学入门"], "is_consumable": True}),
    ("5.08mm 接线端子",        "连接/结构", "接插件/排针", {"model": "5.08mm 2P/3P", "quantity": 10, "tags": [], "is_consumable": True}),
    ("航空插头(GX16 4芯)",     "连接/结构", "接插件/排针", {"model": "GX16-4", "quantity": 5, "tags": [], "is_consumable": True}),
    ("面包板跳线套装",         "连接/结构", "导线/排线", {"model": "140P mixed", "quantity": 6, "tags": ["面包板", "教学入门"], "is_consumable": True}),
    ("亚克力板套装",           "连接/结构", "结构件(支架/底盘/轮子)", {"model": "3mm 200x300mm x5", "quantity": 2, "tags": ["亚克力板"]}),
    ("联轴器套装(5x8mm)",      "连接/结构", "结构件(支架/底盘/轮子)", {"model": "5x8mm x5", "quantity": 5, "tags": ["联轴器"]}),
    ("橡胶轮(直径65mm)",       "连接/结构", "结构件(支架/底盘/轮子)", {"model": "65mm", "quantity": 10, "tags": ["小车底盘"], "is_consumable": True}),
    ("万向轮",                 "连接/结构", "结构件(支架/底盘/轮子)", {"model": "swivel caster", "quantity": 8, "tags": ["小车底盘"], "is_consumable": True}),

    # 工具
    ("数字示波器",             "工具", "测量仪器", {"model": "DSO138/2CH", "quantity": 1, "tags": ["示波器"]}),
    ("函数信号发生器",         "工具", "电源/信号源", {"model": "DDS 60MHz", "quantity": 1, "tags": ["信号发生器"]}),
    ("剥线钳",                 "工具", "拆装工具", {"model": "0.2-6mm", "quantity": 2, "tags": []}),
    ("热熔胶枪",               "工具", "其他", {"model": "40W", "quantity": 2, "tags": ["热熔胶枪"]}),
    ("万用表表笔",             "工具", "测量仪器", {"model": "20A test lead", "quantity": 4, "tags": ["万用表"], "is_consumable": True}),

    # 耗材
    ("免清洗助焊膏",           "耗材", "焊料/助焊剂", {"model": "Flux Paste 50g", "quantity": 3, "tags": ["助焊膏"], "is_consumable": True}),
    ("吸锡带",                 "耗材", "焊料/助焊剂", {"model": "2.5mm x1.5m", "quantity": 4, "tags": ["吸锡带"], "is_consumable": True}),
    ("导热硅脂",               "耗材", "其他", {"model": "Thermal Grease 5g", "quantity": 3, "tags": ["导热硅脂"], "is_consumable": True}),
    ("PLA 3D打印耗材(1.75mm)", "耗材", "其他", {"model": "PLA 1kg white", "quantity": 2, "tags": ["PLA耗材"], "is_consumable": True}),
    ("无尘布",                 "耗材", "清洁/防静电", {"model": "Lint-free 100pcs", "quantity": 2, "tags": [], "is_consumable": True}),

    # ==================== 第三轮丰富：机械元件 ====================
    # 紧固件
    ("塞打螺丝套装",           "连接/结构", "紧固件", {"model": "M3/M4/M5 轴肩混合", "quantity": 4, "tags": ["紧固件", "机械结构"], "is_consumable": True}),
    ("M3 尼龙防松螺母",        "连接/结构", "紧固件", {"model": "M3 DIN985 自锁", "quantity": 100, "tags": ["紧固件"], "is_consumable": True}),
    ("内六角螺丝套装",         "连接/结构", "紧固件", {"model": "M2/M2.5/M3/M4 各长度", "quantity": 5, "tags": ["紧固件", "机械结构"], "is_consumable": True}),
    ("平垫弹垫套装",           "连接/结构", "紧固件", {"model": "M2-M5 混合", "quantity": 3, "tags": ["紧固件"], "is_consumable": True}),
    ("尼龙隔离柱套装",         "连接/结构", "紧固件", {"model": "M3 5-20mm", "quantity": 5, "tags": ["紧固件", "机械结构"], "is_consumable": True}),

    # 结构件
    ("环氧玻纤板 FR4",         "连接/结构", "结构件(支架/底盘/轮子)", {"model": "3mm 200x300mm", "quantity": 5, "tags": ["环氧板", "机械结构"]}),
    ("碳纤维板 3K",            "连接/结构", "结构件(支架/底盘/轮子)", {"model": "2mm 200x300mm", "quantity": 2, "tags": ["碳板", "机械结构"]}),
    ("L型铝角码",              "连接/结构", "结构件(支架/底盘/轮子)", {"model": "20x20mm 直角", "quantity": 40, "tags": ["角码", "机械结构"], "is_consumable": True}),
    ("2020铝型材",             "连接/结构", "结构件(支架/底盘/轮子)", {"model": "2020欧标 1m", "quantity": 4, "tags": ["铝型材", "机械结构"]}),

    # 传动件
    ("直齿轮套装",             "连接/结构", "传动件", {"model": "模数1 12-60齿", "quantity": 3, "tags": ["齿轮齿条", "机械结构"], "is_consumable": True}),
    ("齿条",                   "连接/结构", "传动件", {"model": "模数1 10x10x100mm", "quantity": 5, "tags": ["齿轮齿条", "机械结构"]}),
    ("T8 丝杆(含铜螺母)",      "连接/结构", "传动件", {"model": "T8 导程2mm 300mm", "quantity": 2, "tags": ["丝杆传动", "机械结构"]}),
    ("深沟球轴承套装",         "连接/结构", "传动件", {"model": "608ZZ/624ZZ/625ZZ", "quantity": 10, "tags": ["轴承", "机械结构"], "is_consumable": True}),
    ("法兰轴承 KP08",          "连接/结构", "传动件", {"model": "KP08/KF08", "quantity": 4, "tags": ["轴承", "丝杆传动"]}),
    ("GT2 同步带轮+同步带",    "连接/结构", "传动件", {"model": "20T 5mm孔径 + 6mm带宽", "quantity": 4, "tags": ["机械结构"]}),
    ("梅花联轴器",             "连接/结构", "传动件", {"model": "5x8mm 梅花", "quantity": 5, "tags": ["联轴器", "机械结构"], "is_consumable": True}),
]

total = 0
for item in test_data:
    name, cat, sub = item[0], item[1], item[2]
    kw = item[3] if len(item) > 3 else {}
    add(name, cat, sub, **kw)
    total += 1

print(f"[3/3] 物料填充完成：共 {total} 条")
print(f"\n测试数据准备完毕！涵盖了全部 10 大类 50+ 子类。")
