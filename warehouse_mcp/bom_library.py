# -*- coding: utf-8 -*-
"""BOM 参考库 — 大学生科创常见项目的物料清单参考

用途：
    作为「智能推荐」的参考知识库，而不是直接照抄给用户。
    推荐时先按项目描述检索最相关的 BOM，注入 LLM prompt 作为参考，
    由 LLM 结合用户实际需求做调整与创新补充。

每条 BOM 结构：
    name         项目名
    keywords     用于检索匹配的关键词（命中计分）
    scenario     适用场景说明（竞赛/课程设计/DIY）
    overview     项目整体构成与原理的一段文字（用于可解释输出）
    items        物料清单，每条含：
        name / category / sub_category  名称 + 分类（对齐 CATEGORIES）
        quantity / necessity            数量 + 必需/可选
        role        该物料在项目里干什么
        why         为什么需要它
        options 备选型号/方案
"""

BOM_LIBRARY = [
    {
        "name": "循迹小车",
        "keywords": ["循迹", "寻迹", "智能车", "小车", "巡线", "竞速", "避障", "电赛", "寻线", "轨迹"],
        "scenario": "电子设计竞赛 / 智能车竞赛 控制类",
        "overview": "基于微控制器+红外循迹传感器的自动寻线小车。多路红外对管识别地面黑线位置，"
                   "主控运行 PID 算法调节左右电机转速使小车沿路径行驶，可扩展避障、无线遥控与视觉识别。",
        "items": [
            {"name": "主控开发板", "category": "主控板", "sub_category": "MCU/单片机", "quantity": 1,
             "necessity": "required", "role": "小车大脑，运行循迹与 PID 控制算法",
             "why": "需处理多路循迹信号并输出电机 PWM 调速", "options": "STM32F1/F4、ESP32、Arduino Mega"},
            {"name": "直流减速电机", "category": "执行/驱动", "sub_category": "直流电机", "quantity": 2,
             "necessity": "required", "role": "驱动车轮行驶", "why": "提供动力，减速箱增大扭矩",
             "options": "TT马达、N20、GA12-N20"},
            {"name": "电机驱动板", "category": "执行/驱动", "sub_category": "电机驱动板", "quantity": 1,
             "necessity": "required", "role": "放大 MCU 信号驱动电机",
             "why": "MCU 的 IO 电流不足以直接驱动电机", "options": "L298N、TB6612FNG、DRV8833"},
            {"name": "循迹传感器", "category": "传感模块", "sub_category": "光/颜色/图像", "quantity": 1,
             "necessity": "required", "role": "识别地面黑线位置",
             "why": "红外对管检测黑白反射差异实现循迹", "options": "TCRT5000 多路灰度/数字循迹模块"},
            {"name": "电池", "category": "电源模块", "sub_category": "电池", "quantity": 1,
             "necessity": "required", "role": "整车供电", "why": "需持续大电流驱动电机",
             "options": "18650 锂电池组 7.4V"},
            {"name": "降压模块", "category": "电源模块", "sub_category": "稳压/升降压", "quantity": 1,
             "necessity": "required", "role": "把电池电压降到 5V/3.3V",
             "why": "MCU 和传感器需要稳定低压供电", "options": "LM2596、AMS1117"},
            {"name": "小车底盘", "category": "连接/结构", "sub_category": "结构件(支架/底盘/轮子)", "quantity": 1,
             "necessity": "required", "role": "承载所有元件并安装车轮",
             "why": "固定电机、电池与电路板", "options": "亚克力/铝合金底盘含车轮"},
            {"name": "杜邦线", "category": "连接/结构", "sub_category": "导线/排线", "quantity": 1,
             "necessity": "required", "role": "连接各模块", "why": "电路接线", "options": "公对公/公对母"},
            {"name": "编码器", "category": "传感模块", "sub_category": "其他", "quantity": 2,
             "necessity": "optional", "role": "测量电机转速实现闭环调速",
             "why": "PID 调速需要速度反馈", "options": "霍尔/光电编码器（与电机配套）"},
            {"name": "蓝牙模块", "category": "通信模块", "sub_category": "蓝牙", "quantity": 1,
             "necessity": "optional", "role": "手机遥控或无线调试", "why": "无线控制/打印调试信息",
             "options": "HC-05/06"},
            {"name": "OLED显示屏", "category": "显示/交互", "sub_category": "OLED/LCD", "quantity": 1,
             "necessity": "optional", "role": "显示状态与调试信息",
             "why": "方便观察传感器数据和速度", "options": "0.96 寸 OLED"},
            {"name": "超声波传感器", "category": "传感模块", "sub_category": "距离/位置", "quantity": 1,
             "necessity": "optional", "role": "避障测距", "why": "检测前方障碍物距离",
             "options": "HC-SR04"},
        ],
    },
    {
        "name": "两轮平衡车",
        "keywords": ["平衡车", "自平衡", "两轮", "直立", "倒立摆", "两轮小车"],
        "scenario": "电子设计竞赛 / 课程设计 控制类",
        "overview": "利用 MPU6050 检测车体倾角，主控运行串级 PID 控制两个直流电机正反转，"
                   "使车身保持直立，并可受控前进、后退与转向。",
        "items": [
            {"name": "主控开发板", "category": "主控板", "sub_category": "MCU/单片机", "quantity": 1,
             "necessity": "required", "role": "运行 PID 平衡算法",
             "why": "需要实时姿态解算与电机控制", "options": "STM32F103C8T6"},
            {"name": "姿态传感器", "category": "传感模块", "sub_category": "运动/姿态(IMU)", "quantity": 1,
             "necessity": "required", "role": "检测车体倾角",
             "why": "平衡车靠倾角反馈实现闭环", "options": "MPU6050"},
            {"name": "直流减速电机", "category": "执行/驱动", "sub_category": "直流电机", "quantity": 2,
             "necessity": "required", "role": "驱动两轮", "why": "带编码器更佳，可闭环控制",
             "options": "N20 编码电机"},
            {"name": "电机驱动板", "category": "执行/驱动", "sub_category": "电机驱动板", "quantity": 1,
             "necessity": "required", "role": "驱动电机正反转与调速", "why": "",
             "options": "TB6612FNG、MX1508"},
            {"name": "电池", "category": "电源模块", "sub_category": "电池", "quantity": 1,
             "necessity": "required", "role": "供电", "why": "需要同时给电机和主控供电",
             "options": "18650 锂电池组 7.4V"},
            {"name": "车体支架", "category": "连接/结构", "sub_category": "结构件(支架/底盘/轮子)", "quantity": 1,
             "necessity": "required", "role": "支撑车身并安装电机车轮", "why": "",
             "options": "底盘+车轮+支架套件"},
            {"name": "OLED显示屏", "category": "显示/交互", "sub_category": "OLED/LCD", "quantity": 1,
             "necessity": "optional", "role": "显示倾角/转速", "why": "调试观察", "options": "0.96 寸 OLED"},
            {"name": "蓝牙模块", "category": "通信模块", "sub_category": "蓝牙", "quantity": 1,
             "necessity": "optional", "role": "无线调试或遥控", "why": "", "options": "HC-05"},
        ],
    },
    {
        "name": "机械臂",
        "keywords": ["机械臂", "机械手", "抓取", "多轴", "机械手臂", "多自由度"],
        "scenario": "机器人 / 课程设计 / DIY",
        "overview": "由多个舵机驱动的多自由度机械臂，主控输出 PWM 控制各关节舵机角度实现抓取、"
                   "搬运等动作，可扩展蓝牙、摇杆、示教等多种控制方式。",
        "items": [
            {"name": "舵机", "category": "执行/驱动", "sub_category": "舵机/伺服", "quantity": 4,
             "necessity": "required", "role": "驱动各关节角度",
             "why": "舵机自带位置反馈，适合精确角度控制", "options": "SG90/MG90S"},
            {"name": "主控开发板", "category": "主控板", "sub_category": "MCU/单片机", "quantity": 1,
             "necessity": "required", "role": "输出 PWM 控制舵机",
             "why": "需要多路 PWM 通道", "options": "STM32F103、Arduino Uno/Nano"},
            {"name": "电源", "category": "电源模块", "sub_category": "电源适配器", "quantity": 1,
             "necessity": "required", "role": "独立给舵机供电",
             "why": "多舵机电流大，USB 供电不足", "options": "5V/2A 以上电源"},
            {"name": "结构件", "category": "连接/结构", "sub_category": "结构件(支架/底盘/轮子)", "quantity": 1,
             "necessity": "required", "role": "机械臂连杆与支架", "why": "构成臂体",
             "options": "亚克力板切割件 / 3D 打印件"},
            {"name": "杜邦线", "category": "连接/结构", "sub_category": "导线/排线", "quantity": 1,
             "necessity": "required", "role": "连接各模块", "why": "电路接线", "options": ""},
            {"name": "按键/旋钮", "category": "显示/交互", "sub_category": "按键/旋钮", "quantity": 2,
             "necessity": "optional", "role": "示教/手动控制", "why": "手动控制关节",
             "options": "电位器、摇杆"},
            {"name": "蓝牙模块", "category": "通信模块", "sub_category": "蓝牙", "quantity": 1,
             "necessity": "optional", "role": "无线控制/调试", "why": "", "options": "HC-05"},
            {"name": "OLED显示屏", "category": "显示/交互", "sub_category": "OLED/LCD", "quantity": 1,
             "necessity": "optional", "role": "显示状态", "why": "调试观察", "options": "0.96 寸 OLED"},
            {"name": "紧固件", "category": "连接/结构", "sub_category": "紧固件", "quantity": 1,
             "necessity": "optional", "role": "固定结构", "why": "螺丝螺母", "options": "M2/M3 螺丝螺母包"},
        ],
    },
    {
        "name": "四轴无人机",
        "keywords": ["无人机", "四轴", "四旋翼", "飞控", "飞行器", "穿越机", "四轴飞行"],
        "scenario": "航模 / 竞赛 / DIY",
        "overview": "四轴飞行器，飞控读取姿态传感器数据，通过 PID 调节四个无刷电机转速（经电调驱动）"
                   "产生升力与姿态变化，遥控器+接收机实现人工操控。",
        "items": [
            {"name": "飞控/主控板", "category": "主控板", "sub_category": "MCU/单片机", "quantity": 1,
             "necessity": "required", "role": "姿态解算与电机控制", "why": "飞行器大脑",
             "options": "STM32F405、Arduino Nano"},
            {"name": "姿态传感器", "category": "传感模块", "sub_category": "运动/姿态(IMU)", "quantity": 1,
             "necessity": "required", "role": "检测飞行姿态", "why": "提供角速度与加速度",
             "options": "MPU6050"},
            {"name": "无刷电机", "category": "执行/驱动", "sub_category": "直流电机", "quantity": 4,
             "necessity": "required", "role": "提供升力", "why": "四轴需要四个电机驱动螺旋桨",
             "options": "2212 920KV"},
            {"name": "电调", "category": "执行/驱动", "sub_category": "电机驱动板", "quantity": 4,
             "necessity": "required", "role": "驱动无刷电机调速", "why": "无刷电机需要电子调速器",
             "options": "30A ESC"},
            {"name": "螺旋桨", "category": "连接/结构", "sub_category": "其他", "quantity": 2,
             "necessity": "required", "role": "产生升力", "why": "需正反桨成对抵消反扭矩",
             "options": "1045 正反桨"},
            {"name": "机架", "category": "连接/结构", "sub_category": "结构件(支架/底盘/轮子)", "quantity": 1,
             "necessity": "required", "role": "飞行器骨架", "why": "固定电机与飞控",
             "options": "F450 机架 / 碳纤维机架"},
            {"name": "遥控器/接收机", "category": "通信模块", "sub_category": "射频/NFC", "quantity": 1,
             "necessity": "required", "role": "人工遥控", "why": "发送控制指令",
             "options": "FS-i6 + FS-iA6B"},
            {"name": "电池", "category": "电源模块", "sub_category": "电池", "quantity": 1,
             "necessity": "required", "role": "动力供电", "why": "需大倍率放电",
             "options": "3S/4S 锂电池 2200-3000mAh"},
        ],
    },
    {
        "name": "温湿度监测",
        "keywords": ["温湿度", "环境监测", "气象站", "温控", "温度监测", "湿度", "环境监控"],
        "scenario": "课程设计 / 大创 / DIY",
        "overview": "主控采集温湿度传感器数据，本地显示或经 WiFi 上报，用于环境监测、气象站、"
                   "温控等场景。",
        "items": [
            {"name": "主控开发板", "category": "主控板", "sub_category": "MCU/单片机", "quantity": 1,
             "necessity": "required", "role": "采集并上报数据", "why": "需联网上报",
             "options": "ESP32（带 WiFi）"},
            {"name": "温湿度传感器", "category": "传感模块", "sub_category": "温度/湿度", "quantity": 1,
             "necessity": "required", "role": "采集温湿度", "why": "核心传感",
             "options": "DHT11/DHT22"},
            {"name": "OLED显示屏", "category": "显示/交互", "sub_category": "OLED/LCD", "quantity": 1,
             "necessity": "optional", "role": "本地显示数据", "why": "脱机可读", "options": "0.96 寸 OLED"},
            {"name": "电池", "category": "电源模块", "sub_category": "电池", "quantity": 1,
             "necessity": "required", "role": "供电", "why": "便携/离线场景", "options": "18650"},
            {"name": "面包板", "category": "连接/结构", "sub_category": "面包板/洞洞板", "quantity": 1,
             "necessity": "optional", "role": "搭电路", "why": "原型验证", "options": ""},
        ],
    },
    {
        "name": "蓝牙遥控小车",
        "keywords": ["蓝牙遥控", "蓝牙控制", "手机遥控", "app遥控", "蓝牙小车", "遥控小车"],
        "scenario": "课程设计 / DIY",
        "overview": "手机通过蓝牙发送指令，主控接收后驱动电机实现小车的遥控移动。",
        "items": [
            {"name": "蓝牙模块", "category": "通信模块", "sub_category": "蓝牙", "quantity": 1,
             "necessity": "required", "role": "接收手机遥控指令", "why": "无线通信",
             "options": "HC-05 串口透传"},
            {"name": "主控开发板", "category": "主控板", "sub_category": "MCU/单片机", "quantity": 1,
             "necessity": "required", "role": "解析指令并控制电机", "why": "",
             "options": "Arduino 或 STM32"},
            {"name": "直流减速电机", "category": "执行/驱动", "sub_category": "直流电机", "quantity": 2,
             "necessity": "required", "role": "驱动车轮", "why": "", "options": "TT马达"},
            {"name": "电机驱动板", "category": "执行/驱动", "sub_category": "电机驱动板", "quantity": 1,
             "necessity": "required", "role": "驱动电机", "why": "", "options": "L298N"},
            {"name": "电池", "category": "电源模块", "sub_category": "电池", "quantity": 1,
             "necessity": "required", "role": "供电", "why": "", "options": "18650 锂电池组"},
            {"name": "小车底盘", "category": "连接/结构", "sub_category": "结构件(支架/底盘/轮子)", "quantity": 1,
             "necessity": "required", "role": "承载结构", "why": "", "options": "含车轮"},
        ],
    },
    {
        "name": "视觉识别",
        "keywords": ["视觉", "摄像头", "人脸", "图像识别", "opencv", "机器视觉", "目标检测", "图像"],
        "scenario": "大创 / 课程设计 / 竞赛",
        "overview": "单板机运行 OpenCV 等图像处理算法，配合摄像头实现人脸识别、目标检测、"
                   "循迹等视觉任务。",
        "items": [
            {"name": "单板计算机", "category": "主控板", "sub_category": "单板机SBC", "quantity": 1,
             "necessity": "required", "role": "运行图像识别算法", "why": "需要较强算力",
             "options": "树莓派 / K210 / OpenMV"},
            {"name": "摄像头", "category": "传感模块", "sub_category": "光/颜色/图像", "quantity": 1,
             "necessity": "required", "role": "采集图像", "why": "视觉输入",
             "options": "USB 摄像头或 OV2640"},
            {"name": "OLED显示屏", "category": "显示/交互", "sub_category": "OLED/LCD", "quantity": 1,
             "necessity": "optional", "role": "显示识别结果", "why": "", "options": ""},
            {"name": "电源适配器", "category": "电源模块", "sub_category": "电源适配器", "quantity": 1,
             "necessity": "required", "role": "供电", "why": "单板机功耗较高",
             "options": "5V 供电"},
            {"name": "蜂鸣器", "category": "显示/交互", "sub_category": "蜂鸣器/扬声器", "quantity": 1,
             "necessity": "optional", "role": "识别成功报警", "why": "", "options": ""},
        ],
    },
    {
        "name": "智能家居",
        "keywords": ["智能家居", "灯控", "远程开关", "继电器", "家居", "远程控制", "物联网"],
        "scenario": "大创 / 物联网 / DIY",
        "overview": "主控联网后控制继电器通断，实现灯具、电器的远程开关与定时控制。",
        "items": [
            {"name": "主控开发板", "category": "主控板", "sub_category": "MCU/单片机", "quantity": 1,
             "necessity": "required", "role": "联网与控制中枢", "why": "需 WiFi 联网",
             "options": "ESP8266/ESP32"},
            {"name": "继电器模块", "category": "执行/驱动", "sub_category": "继电器/接触器", "quantity": 2,
             "necessity": "required", "role": "控制灯具/电器通断", "why": "低电平控制高功率负载",
             "options": ""},
            {"name": "LED灯", "category": "显示/交互", "sub_category": "LED/数码管", "quantity": 2,
             "necessity": "optional", "role": "状态指示", "why": "", "options": ""},
            {"name": "电源适配器", "category": "电源模块", "sub_category": "电源适配器", "quantity": 1,
             "necessity": "required", "role": "供电", "why": "", "options": "5V 供电"},
        ],
    },
    {
        "name": "电子秤",
        "keywords": ["电子秤", "称重", "压力", "体重秤", "称重传感器", "重量"],
        "scenario": "课程设计 / DIY",
        "overview": "称重传感器（HX711）检测压力，主控采集并换算成重量后在显示屏上显示。",
        "items": [
            {"name": "称重传感器", "category": "传感模块", "sub_category": "其他", "quantity": 1,
             "necessity": "required", "role": "检测重量", "why": "压力传感",
             "options": "HX711 + 称重模块"},
            {"name": "主控开发板", "category": "主控板", "sub_category": "MCU/单片机", "quantity": 1,
             "necessity": "required", "role": "采集并换算重量", "why": "", "options": ""},
            {"name": "OLED显示屏", "category": "显示/交互", "sub_category": "OLED/LCD", "quantity": 1,
             "necessity": "required", "role": "显示重量", "why": "", "options": ""},
            {"name": "电池", "category": "电源模块", "sub_category": "电池", "quantity": 1,
             "necessity": "optional", "role": "便携供电", "why": "", "options": ""},
        ],
    },
]


def search_bom_library(description: str, limit: int = 2) -> list:
    """按项目描述检索最相关的 BOM（关键词命中计分，取 top-N）。

    Returns:
        命中的 BOM dict 列表（按相关度降序）；无命中返回空列表。
    """
    text = description.lower()
    scored = []
    for bom in BOM_LIBRARY:
        score = sum(1 for kw in bom["keywords"] if kw.lower() in text)
        if score > 0:
            scored.append((score, bom))
    scored.sort(key=lambda x: -x[0])
    return [bom for _, bom in scored[:limit]]


def format_bom_refs(boms: list) -> str:
    """把命中的 BOM 格式化成注入 prompt 的参考文本。"""
    if not boms:
        return ""
    parts = []
    for bom in boms:
        lines = [f"### 参考 BOM：{bom['name']}（{bom.get('scenario', '')}）"]
        lines.append(f"参考说明：{bom['overview']}")
        for it in bom["items"]:
            role = f" | 作用：{it['role']}" if it.get("role") else ""
            why = f" | 原因：{it['why']}" if it.get("why") else ""
            alt = f" | 备选：{it['options']}" if it.get("options") else ""
            lines.append(
                f"- {it['name']}（{it['category']}>{it['sub_category']}）x{it['quantity']} "
                f"[{it['necessity']}]{role}{why}{alt}"
            )
        parts.append("\n".join(lines))
    return "\n\n".join(parts)
