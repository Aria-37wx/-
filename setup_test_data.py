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
]

total = 0
for item in test_data:
    name, cat, sub = item[0], item[1], item[2]
    kw = item[3] if len(item) > 3 else {}
    add(name, cat, sub, **kw)
    total += 1

print(f"[3/3] 物料填充完成：共 {total} 条")
print(f"\n测试数据准备完毕！涵盖了全部 10 大类 50+ 子类。")
