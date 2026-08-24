# -*- coding: utf-8 -*-
"""数据库连接管理与初始化"""

import sqlite3
import os
from datetime import datetime

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_DIR = os.path.join(_BASE_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "warehouse.db")

# 分类常量 — 大类 + 子类（含助记码）
CATEGORIES = {
    "主控板":    {"code": "MC", "subs": [
        ("MCU/单片机", "MCU"), ("单板机SBC", "SBC"), ("FPGA/CPLD", "FPG"), ("DSP", "DSP"), ("其他", "OTH")
    ]},
    "传感模块":  {"code": "SN", "subs": [
        ("距离/位置", "DST"), ("温度/湿度", "THM"), ("运动/姿态(IMU)", "IMU"),
        ("光/颜色/图像", "OPT"), ("环境(气压/气体/声音)", "ENV"), ("电流/电压", "CVT"),
        ("生物/医学", "BIO"), ("其他", "OTH")
    ]},
    "执行/驱动": {"code": "AC", "subs": [
        ("直流电机", "DCM"), ("步进电机", "STP"), ("舵机/伺服", "SRV"),
        ("电机驱动板", "MDR"), ("继电器/接触器", "RLY"), ("气动/液压", "PNU"), ("其他", "OTH")
    ]},
    "通信模块":  {"code": "CM", "subs": [
        ("蓝牙", "BLE"), ("WiFi", "WIF"), ("LoRa/NB-IoT", "LOR"),
        ("射频/NFC", "RFD"), ("以太网/CAN/485", "ETH"), ("其他", "OTH")
    ]},
    "显示/交互": {"code": "DP", "subs": [
        ("OLED/LCD", "OLD"), ("LED/数码管", "LED"), ("按键/旋钮", "BTN"),
        ("蜂鸣器/扬声器", "BZR"), ("触摸屏", "TCH"), ("其他", "OTH")
    ]},
    "电源模块":  {"code": "PW", "subs": [
        ("电池", "BAT"), ("稳压/升降压", "REG"), ("充电管理", "CHG"),
        ("电源适配器", "ADP"), ("其他", "OTH")
    ]},
    "电子元件":  {"code": "EC", "subs": [
        ("电阻", "RES"), ("电容", "CAP"), ("电感/磁珠", "IND"),
        ("二极管", "DIO"), ("三极管/MOS", "BJT"), ("IC/运放", "ICS"),
        ("晶振", "XTL"), ("其他", "OTH")
    ]},
    "连接/结构": {"code": "CN", "subs": [
        ("导线/排线", "WIR"), ("接插件/排针", "CON"), ("面包板/洞洞板", "BRD"),
        ("紧固件", "FST"), ("结构件(支架/底盘/轮子)", "STR"), ("传动件", "TRN"), ("其他", "OTH")
    ]},
    "工具":      {"code": "TL", "subs": [
        ("测量仪器", "MSR"), ("焊接工具", "SLD"), ("拆装工具", "TOL"),
        ("电源/信号源", "PWS"), ("其他", "OTH")
    ]},
    "耗材":      {"code": "CS", "subs": [
        ("焊料/助焊剂", "SDR"), ("胶带/胶水", "TAP"), ("热缩管", "HSL"),
        ("清洁/防静电", "CLN"), ("其他", "OTH")
    ]},
}

# 预置标签（产品系列级别）
_PRESET_TAGS = [
    # ---- 主控/开发板 ----
    ("Arduino Uno", "ATmega328P，5V逻辑，入门级MCU开发板，丰富扩展生态，适合教学和原型验证"),
    ("Arduino Mega", "ATmega2560，多IO口，适合复杂项目和3D打印机控制"),
    ("Arduino Nano", "ATmega328P，微型封装，适合空间受限的嵌入式项目"),
    ("ESP32", "乐鑫双核MCU，内置WiFi 802.11b/g/n和BLE 4.2，160MHz，适合IoT和无线传感器应用"),
    ("ESP8266", "乐鑫单核WiFi MCU，80/160MHz，低成本IoT方案，支持Arduino/NodeMCU"),
    ("STM32F1", "ARM Cortex-M3 @72MHz，经典入门MCU，适合教学和通用控制"),
    ("STM32F4", "ARM Cortex-M4 @168MHz，带DSP和FPU，高性能MCU，适合实时控制和信号处理"),
    ("STM32F7/H7", "ARM Cortex-M7 @216-480MHz，高性能带Cache，适合复杂运算和GUI"),
    ("树莓派", "Linux单板计算机，丰富GPIO/HDMI/USB，适合视觉处理、边缘计算和教学"),
    ("K210", "RISC-V双核+KPU神经网络加速器，适合边缘AI和视觉应用"),
    ("FPGA", "可编程逻辑器件，适合高速并行处理和数字电路设计"),
    ("51单片机", "经典入门MCU，8051架构，简单易学，适合教学和基础控制"),

    # ---- 电机/驱动 ----
    ("L298N", "双H桥电机驱动模块，可驱动2个直流电机或1个步进电机，逻辑5V驱动5-35V"),
    ("TB6612", "双H桥电机驱动模块，比L298N效率更高，适合电池供电项目"),
    ("A4988", "步进电机驱动模块，支持微步进，适合3D打印机和CNC"),
    ("无刷电机", "三相无刷直流电机，高效率高转速，需要专用电调驱动"),
    ("减速电机", "直流电机+减速箱，大扭矩低转速，适合小车和机械臂关节"),
    ("编码电机", "带霍尔编码器的直流减速电机，可测速，适合闭环控制"),
    ("舵机SG90", "微型伺服电机，0-180°，PWM控制，适合小型机械臂和转向控制"),

    # ---- 传感器 ----
    ("HC-SR04", "超声波测距模块，2cm-400cm，5V，用于避障和距离检测"),
    ("MPU6050", "6轴IMU(3轴加速度+3轴陀螺仪)，I2C接口，用于姿态解算和运动检测"),
    ("DHT11", "低端数字温湿度传感器，精度±2℃/±5%RH，适合环境监测入门"),
    ("DHT22", "高精度数字温湿度传感器，精度±0.5℃，适合精确环境监测"),
    ("红外传感器", "红外发射/接收、对管、热释电(PIR)等，适合避障、人体检测、通信"),
    ("光敏传感器", "光敏电阻、BH1750光照度传感器等，适合环境光检测"),
    ("声音传感器", "麦克风模块、声音检测，适合声控和噪声监测"),
    ("气体传感器", "MQ系列(CO/烟雾/酒精等)，适合安防和环境检测"),
    ("压力/称重", "HX711+称重传感器，适合电子秤和压力检测"),
    ("编码器", "旋转编码器，适合电机测速和位置检测"),
    ("霍尔传感器", "磁场检测，适合转速测量和接近开关"),
    ("GPS/北斗", "卫星定位模块，适合户外导航和轨迹记录"),

    # ---- 通信 ----
    ("HC-05", "蓝牙2.0串口透传模块，主从一体，适合短距离无线通信"),
    ("NRF24L01", "2.4GHz无线收发模块，SPI接口，适合多节点组网"),
    ("LoRa", "低功耗远距离无线通信技术，适合户外IoT和农业监测"),
    ("Zigbee", "低功耗自组网无线通信，适合智能家居和传感器网络"),
    ("USB转串口", "CH340/CP2102/FT232等USB-TTL模块，必备调试工具"),
    ("CAN/485", "工业现场总线通信模块，适合多机通信和工业控制"),

    # ---- 电源 ----
    ("18650电池", "3.7V锂离子电池，适合便携供电"),
    ("锂电池充电", "TP4056等锂电池充电管理模块"),
    ("降压模块", "LM2596/MP1584等DC-DC降压模块，适合电压转换"),
    ("升压模块", "MT3608等DC-DC升压模块，适合电池升压供电"),

    # ---- 显示 ----
    ("0.96 OLED", "128x64 I2C/SPI OLED显示屏，适合小型信息显示"),
    ("LCD1602", "16x2字符液晶显示，经典入门显示模块"),
    ("TFT触摸屏", "彩色触摸显示屏，适合GUI互动项目"),

    # ---- 结构 ----
    ("小车底盘", "智能小车底盘套件，含底盘+轮子+电机，适合竞速和循迹"),
    ("亚克力板", "透明亚克力板材，适合DIY外壳和结构"),
    ("联轴器", "电机轴与负载连接件，适合机械传动"),

    # ---- 工具 ----
    ("示波器", "电子信号波形测量仪器，调试必备"),
    ("逻辑分析仪", "数字信号时序分析工具，适合通信协议调试"),
    ("可调电源", "可调电压电流直流电源，适合开发测试"),

    # ---- 场景标签 ----
    ("PID控制", "使用PID算法的控制系统，适合温度/速度/位置闭环控制"),
    ("四轴无人机", "四旋翼飞行器相关，适合无人机竞赛和飞控开发"),
    ("平衡车", "两轮自平衡小车，适合姿态控制和PID算法实践"),
    ("机械臂", "多轴机械臂，适合运动学和伺服控制"),
    ("循迹小车", "红外/摄像头循迹智能小车，适合传感器和控制入门"),
    ("IoT开发", "物联网项目常用元件，含WiFi/蓝牙/传感器"),
    ("教学用", "常用于课程教学和实验的物料"),
    ("竞赛用", "常用于电赛/机器人竞赛的物料"),
]

# 默认位置推荐（大类 → 推荐位置）
DEFAULT_LOCATIONS = {
    "主控板":    "柜A-1 主控板区",
    "传感模块":  "柜A-2 传感器区",
    "执行/驱动": "柜B-1 电机驱动区",
    "通信模块":  "柜A-3 通信模块区",
    "显示/交互": "柜A-4 显示交互区",
    "电源模块":  "柜B-2 电源区",
    "电子元件":  "柜C 元件抽屉",
    "连接/结构": "柜D 连接结构区",
    "工具":      "柜E 工具区",
    "耗材":      "柜F 耗材区",
}


def get_category_subs(category_name: str) -> list:
    """返回某大类的子类名称列表（不含代码）"""
    return [s[0] for s in CATEGORIES[category_name]["subs"]]


def get_sub_code(category_name: str, sub_category: str) -> str:
    """返回子类的 3 字母助记码"""
    for name, code in CATEGORIES[category_name]["subs"]:
        if name == sub_category:
            return code
    return "OTH"


def get_recommended_location(category: str) -> str:
    """返回某大类的推荐位置（不查数据库，直接用常量）"""
    return DEFAULT_LOCATIONS.get(category, "")


def get_db() -> sqlite3.Connection:
    """获取数据库连接（row_factory = Row，开启外键约束）"""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """初始化数据库，创建所有表 + 预置标签（幂等）"""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS materials (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            category_code TEXT NOT NULL DEFAULT '',
            sub_category TEXT NOT NULL DEFAULT '',
            sub_category_code TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            is_consumable INTEGER NOT NULL DEFAULT 0,
            quantity INTEGER NOT NULL DEFAULT 0,
            location TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE INDEX IF NOT EXISTS idx_materials_category ON materials(category_code);
        CREATE INDEX IF NOT EXISTS idx_materials_subcat ON materials(sub_category_code);
        CREATE INDEX IF NOT EXISTS idx_materials_name ON materials(name);
        CREATE INDEX IF NOT EXISTS idx_materials_created ON materials(created_at);

        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);

        CREATE TABLE IF NOT EXISTS material_tags (
            material_id TEXT NOT NULL,
            tag_name TEXT NOT NULL,
            PRIMARY KEY (material_id, tag_name),
            FOREIGN KEY (material_id) REFERENCES materials(id),
            FOREIGN KEY (tag_name) REFERENCES tags(name)
        );

        CREATE TABLE IF NOT EXISTS users (
            phone TEXT PRIMARY KEY,
            name TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS outbound_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id TEXT NOT NULL,
            user_phone TEXT NOT NULL,
            mode TEXT NOT NULL CHECK(mode IN ('borrow','consume')),
            quantity INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (material_id) REFERENCES materials(id)
        );

        CREATE INDEX IF NOT EXISTS idx_outbound_material ON outbound_records(material_id);
        CREATE INDEX IF NOT EXISTS idx_outbound_user ON outbound_records(user_phone);
        CREATE INDEX IF NOT EXISTS idx_outbound_created ON outbound_records(created_at);

        CREATE TABLE IF NOT EXISTS borrow_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id TEXT NOT NULL,
            user_phone TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            borrowed_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            returned_at TEXT,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','returned')),
            FOREIGN KEY (material_id) REFERENCES materials(id)
        );

        CREATE INDEX IF NOT EXISTS idx_borrow_material ON borrow_records(material_id);
        CREATE INDEX IF NOT EXISTS idx_borrow_user ON borrow_records(user_phone);
        CREATE INDEX IF NOT EXISTS idx_borrow_status ON borrow_records(status);

        CREATE TABLE IF NOT EXISTS locations (
            category TEXT PRIMARY KEY,
            recommended TEXT NOT NULL
        );
    """)

    # 预置标签（幂等：IGNORE 避免重复插入）
    # 迁移：老库的 borrow_records 没有 quantity 列，幂等补上
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(borrow_records)").fetchall()]
    if "quantity" not in cols:
        conn.execute(
            "ALTER TABLE borrow_records ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1"
        )

    conn.executemany(
        "INSERT OR IGNORE INTO tags (name, description) VALUES (?, ?)",
        _PRESET_TAGS
    )

    # 预置位置推荐（幂等）
    conn.executemany(
        "INSERT OR IGNORE INTO locations (category, recommended) VALUES (?, ?)",
        list(DEFAULT_LOCATIONS.items())
    )
    conn.commit()
    conn.close()


def generate_id(conn: sqlite3.Connection, category_code: str, sub_category_code: str,
                date_str: str = None) -> str:
    """生成物料唯一标识。

    格式 {大类码}-{子类码}-{YYYYMMDD}-{NNNN}
    例：AC-DCM-20260809-0001（执行/驱动 → 直流电机）
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")
    prefix = f"{category_code}-{sub_category_code}-{date_str}-"
    row = conn.execute(
        "SELECT MAX(CAST(SUBSTR(id, LENGTH(?) + 1) AS INTEGER)) FROM materials WHERE id LIKE ?",
        (prefix, f"{prefix}%")
    ).fetchone()
    seq = (row[0] or 0) + 1
    return f"{prefix}{seq:04d}"
