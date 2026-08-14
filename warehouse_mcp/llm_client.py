# -*- coding: utf-8 -*-
"""LLM 推理客户端 — OpenAI 兼容接口（DeepSeek / 通义千问 / OpenAI 通用）

使用方式：
    1. 设置环境变量 LLM_API_KEY 和 LLM_BASE_URL（可选）
    2. 或通过代码 configure(api_key, base_url) 配置
    3. 调用 infer_material(name, description) 获取推理结果

需要安装：pip install openai
"""

import os
import json
import re
from warehouse_mcp.db.database import CATEGORIES, get_category_subs

# 配置文件路径（data/ 已被 .gitignore 忽略，不会提交到 git）
_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "llm_config.json"
)

_api_key = os.environ.get("LLM_API_KEY", "")
_base_url = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
_model = os.environ.get("LLM_MODEL", "deepseek-chat")

# 用 __import__ 延迟导入，避免未安装时启动报错
_openai = None


def _load_config():
    """从本地文件加载 LLM 配置（优先环境变量，其次文件）"""
    global _api_key, _base_url, _model
    if os.path.exists(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # 环境变量优先，文件作为默认值
            if not _api_key:
                _api_key = saved.get("api_key", "")
            if not os.environ.get("LLM_BASE_URL"):
                _base_url = saved.get("base_url", _base_url)
            if not os.environ.get("LLM_MODEL"):
                _model = saved.get("model", _model)
        except Exception:
            pass


_load_config()  # 模块加载时自动读取


def _get_openai():
    global _openai
    if _openai is None:
        _openai = __import__("openai").OpenAI
    return _openai


def configure(api_key: str = "", base_url: str = "", model: str = ""):
    """手动配置 LLM 连接参数（同时保存到本地文件）"""
    global _api_key, _base_url, _model
    if api_key:
        _api_key = api_key
    if base_url:
        _base_url = base_url
    if model:
        _model = model
    # 保存到本地文件
    _save_config()


def _save_config():
    """保存 LLM 配置到本地文件"""
    try:
        os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "api_key": _api_key,
                "base_url": _base_url,
                "model": _model,
            }, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_config_status() -> dict:
    """获取当前 LLM 配置状态"""
    return {
        "has_key": bool(_api_key),
        "base_url": _base_url,
        "model": _model,
        "key_prefix": (_api_key[:8] + "...") if len(_api_key) > 8 else ("***" if _api_key else ""),
    }


def _build_system_prompt() -> str:
    """构建 system prompt：告诉 LLM 分类体系和可用标签"""
    cat_lines = []
    for cat_name, cat_info in CATEGORIES.items():
        subs = get_category_subs(cat_name)
        subs_str = "、".join(subs)
        cat_lines.append(f"  {cat_name}（代码 {cat_info['code']}）：{subs_str}")

    return f"""你是一个大学生科创实验室的物料管理助手。你的任务是：根据用户提供的物料名称和可选描述，推断该物料应属于哪个类别。

## 分类体系

大类及子类如下：
{chr(10).join(cat_lines)}

## 标签

标签是可选的特性标记，用于帮助后续智能检索。如果物料是某个知名产品系列，请给出标签。例如：
- 名称 "STM32F407" → 标签 ["STM32F4"]
- 名称 "Arduino Uno" → 标签 ["Arduino Uno"]
- 名称 "HC-SR04 超声波模块" → 标签 ["HC-SR04"]
- 名称 "红外对管" → 标签 ["红外传感器"]

如果用户提到特殊用途（如"这是搞红外的"），请同时添加功能标签。

## 推断规则

1. category 必须是上述 10 个大类的完整中文名称，不能改字
2. sub_category 必须是该类下子类的完整名称，不能改字
3. model 提取型号信息（如产品编号），没有则填空字符串
4. is_consumable：焊锡丝、热缩管、胶带等用完就没了 = true，开发板、工具等可反复使用 = false
5. tags：物料所属的产品系列标签（可选）

## 输出格式

请严格输出 JSON，不要有任何其他文字：
```json
{{
    "category": "主控板",
    "sub_category": "MCU/单片机",
    "model": "STM32F407",
    "is_consumable": false,
    "tags": ["STM32F4"]
}}
```

如果没有把握确定某个字段，用空字符串。但 category 和 sub_category 必须尽可能推断。"""


def _extract_json(text: str) -> dict:
    """从 LLM 回复中提取 JSON（处理 markdown 代码块包裹的情况）"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试提取 ```json ... ``` 代码块
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试提取第一个 { ... } 对象
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"无法从 LLM 回复中解析 JSON: {text[:200]}")


def infer_material(name: str, description: str = "") -> dict:
    """调用 LLM 推断物料的分类和属性。

    Args:
        name: 物料名称，如 "TT直流减速电机"
        description: 额外描述（可选），如 "带编码器"

    Returns:
        dict: {"category": "执行/驱动", "sub_category": "直流电机",
               "model": "TT Motor", "is_consumable": False, "tags": ["减速电机"]}

    Raises:
        RuntimeError: LLM 未配置 API Key
        ValueError: LLM 返回无法解析
    """
    if not _api_key:
        raise RuntimeError(
            "未配置 LLM API Key。请设置环境变量 LLM_API_KEY，"
            "或调用 warehouse_mcp.llm_client.configure(api_key='...')"
        )

    OpenAI = _get_openai()
    client = OpenAI(api_key=_api_key, base_url=_base_url)

    user_content = f"物料名称：{name}"
    if description:
        user_content += f"\n补充描述：{description}"

    response = client.chat.completions.create(
        model=_model,
        messages=[
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user", "content": user_content},
        ],
        temperature=0.1,   # 低温度，保证输出稳定
        max_tokens=500,
    )

    content = response.choices[0].message.content.strip()
    result = _extract_json(content)

    return result


def infer_material_fake(name: str, description: str = "") -> dict:
    """离线 Mock 版本，不调用 LLM，基于规则推断（用于测试和无 API 环境）。

    覆盖常见科创物料名称，未覆盖的返回空类别由调用方处理。
    """
    name_lower = name.lower()
    desc_lower = description.lower() if description else ""

    # 主控板
    if any(kw in name_lower for kw in ["arduino", "stm32", "esp32", "esp8266", "树莓派", "k210", "51单片机", "msp430"]):
        if "esp32" in name_lower:
            return {"category": "主控板", "sub_category": "MCU/单片机", "model": "ESP32", "is_consumable": False, "tags": ["ESP32", "IoT开发"]}
        if "esp8266" in name_lower:
            return {"category": "主控板", "sub_category": "MCU/单片机", "model": "ESP8266", "is_consumable": False, "tags": ["ESP8266", "IoT开发"]}
        if "树莓派" in name_lower:
            return {"category": "主控板", "sub_category": "单板机SBC", "model": "", "is_consumable": False, "tags": ["树莓派"]}
        if "stm32f4" in name_lower or ("stm32" in name_lower and ("407" in name_lower or "429" in name_lower)):
            return {"category": "主控板", "sub_category": "MCU/单片机", "model": "", "is_consumable": False, "tags": ["STM32F4"]}
        if "stm32f1" in name_lower or ("stm32" in name_lower and "103" in name_lower):
            return {"category": "主控板", "sub_category": "MCU/单片机", "model": "", "is_consumable": False, "tags": ["STM32F1"]}
        if "arduino" in name_lower:
            return {"category": "主控板", "sub_category": "MCU/单片机", "model": "", "is_consumable": False, "tags": ["Arduino Uno"]}
        if "k210" in name_lower:
            return {"category": "主控板", "sub_category": "MCU/单片机", "model": "", "is_consumable": False, "tags": ["K210"]}
        return {"category": "主控板", "sub_category": "MCU/单片机", "model": "", "is_consumable": False, "tags": []}

    # 执行/驱动
    if any(kw in name_lower for kw in ["电机", "马达", "舵机", "伺服", "步进", "驱动"]):
        if "步进" in name_lower:
            return {"category": "执行/驱动", "sub_category": "步进电机", "model": "", "is_consumable": False, "tags": []}
        if "舵机" in name_lower or "伺服" in name_lower:
            return {"category": "执行/驱动", "sub_category": "舵机/伺服", "model": "", "is_consumable": False, "tags": ["舵机SG90"]}
        if "无刷" in name_lower:
            return {"category": "执行/驱动", "sub_category": "直流电机", "model": "", "is_consumable": False, "tags": ["无刷电机"]}
        if "减速" in name_lower or "编码" in name_lower:
            tags = ["减速电机"]
            if "编码" in name_lower:
                tags.append("编码电机")
            return {"category": "执行/驱动", "sub_category": "直流电机", "model": "", "is_consumable": False, "tags": tags}
        if "l298n" in name_lower or "tb6612" in name_lower or "a4988" in name_lower:
            return {"category": "执行/驱动", "sub_category": "电机驱动板", "model": "", "is_consumable": False, "tags": [name.strip()]}
        return {"category": "执行/驱动", "sub_category": "直流电机", "model": "", "is_consumable": False, "tags": ["减速电机"]}

    # 传感模块
    if any(kw in name_lower for kw in ["传感器", "hc-sr04", "超声波", "dht11", "dht22", "温湿度", "mpu6050", "陀螺仪", "加速度", "红外", "光敏", "压力", "气体"]):
        if "超声波" in name_lower or "hc-sr04" in name_lower:
            return {"category": "传感模块", "sub_category": "距离/位置", "model": "HC-SR04", "is_consumable": False, "tags": ["HC-SR04"]}
        if "dht11" in name_lower or "dht22" in name_lower or "温湿度" in name_lower:
            return {"category": "传感模块", "sub_category": "温度/湿度", "model": "", "is_consumable": False, "tags": ["DHT11"]}
        if "mpu6050" in name_lower or "陀螺仪" in name_lower:
            return {"category": "传感模块", "sub_category": "运动/姿态(IMU)", "model": "", "is_consumable": False, "tags": ["MPU6050"]}
        if "红外" in name_lower:
            return {"category": "传感模块", "sub_category": "光/颜色/图像", "model": "", "is_consumable": False, "tags": ["红外传感器"]}
        if "光敏" in name_lower:
            return {"category": "传感模块", "sub_category": "光/颜色/图像", "model": "", "is_consumable": False, "tags": ["光敏传感器"]}
        if "压力" in name_lower or "称重" in name_lower:
            return {"category": "传感模块", "sub_category": "其他", "model": "", "is_consumable": False, "tags": ["压力/称重"]}
        if "气体" in name_lower or "mq" in name_lower:
            return {"category": "传感模块", "sub_category": "环境(气压/气体/声音)", "model": "", "is_consumable": False, "tags": ["气体传感器"]}
        return {"category": "传感模块", "sub_category": "其他", "model": "", "is_consumable": False, "tags": []}

    # 通信模块
    if any(kw in name_lower for kw in ["蓝牙", "wifi", "lora", "nrf24", "zigbee", "nfc", "rfid", "can", "485", "串口", "ch340", "cp2102"]):
        if "蓝牙" in name_lower or "hc-05" in name_lower:
            return {"category": "通信模块", "sub_category": "蓝牙", "model": "", "is_consumable": False, "tags": ["HC-05"]}
        if "wifi" in name_lower:
            return {"category": "通信模块", "sub_category": "WiFi", "model": "", "is_consumable": False, "tags": []}
        if "lora" in name_lower:
            return {"category": "通信模块", "sub_category": "LoRa/NB-IoT", "model": "", "is_consumable": False, "tags": ["LoRa"]}
        if "串口" in name_lower or "ch340" in name_lower or "cp2102" in name_lower:
            return {"category": "通信模块", "sub_category": "其他", "model": "", "is_consumable": False, "tags": ["USB转串口"]}
        return {"category": "通信模块", "sub_category": "其他", "model": "", "is_consumable": False, "tags": []}

    # 显示/交互
    if any(kw in name_lower for kw in ["oled", "lcd", "屏幕", "显示", "蜂鸣器", "按键", "按钮"]):
        if "oled" in name_lower:
            return {"category": "显示/交互", "sub_category": "OLED/LCD", "model": "", "is_consumable": False, "tags": ["0.96 OLED"]}
        if "lcd" in name_lower:
            return {"category": "显示/交互", "sub_category": "OLED/LCD", "model": "", "is_consumable": False, "tags": ["LCD1602"]}
        if "蜂鸣器" in name_lower:
            return {"category": "显示/交互", "sub_category": "蜂鸣器/扬声器", "model": "", "is_consumable": False, "tags": []}
        return {"category": "显示/交互", "sub_category": "其他", "model": "", "is_consumable": False, "tags": []}

    # 电源模块
    if any(kw in name_lower for kw in ["电池", "18650", "电源", "降压", "升压", "稳压", "充电", "lm2596", "mt3608", "ams1117", "tp4056"]):
        if "18650" in name_lower or "电池" in name_lower:
            return {"category": "电源模块", "sub_category": "电池", "model": "", "is_consumable": False, "tags": ["18650电池"]}
        if "充电" in name_lower or "tp4056" in name_lower:
            return {"category": "电源模块", "sub_category": "充电管理", "model": "", "is_consumable": False, "tags": ["锂电池充电"]}
        if "降压" in name_lower or "稳压" in name_lower:
            return {"category": "电源模块", "sub_category": "稳压/升降压", "model": "", "is_consumable": False, "tags": ["降压模块"]}
        if "升压" in name_lower:
            return {"category": "电源模块", "sub_category": "稳压/升降压", "model": "", "is_consumable": False, "tags": ["升压模块"]}
        return {"category": "电源模块", "sub_category": "其他", "model": "", "is_consumable": False, "tags": []}

    # 电子元件
    if any(kw in name_lower for kw in ["电阻", "电容", "电感", "二极管", "三极管", "mos", "运放", "晶振", "led灯", "ne555"]):
        if "电阻" in name_lower:
            return {"category": "电子元件", "sub_category": "电阻", "model": "", "is_consumable": False, "tags": []}
        if "电容" in name_lower:
            return {"category": "电子元件", "sub_category": "电容", "model": "", "is_consumable": False, "tags": []}
        if "电感" in name_lower or "磁珠" in name_lower:
            return {"category": "电子元件", "sub_category": "电感/磁珠", "model": "", "is_consumable": False, "tags": []}
        if "二极管" in name_lower:
            return {"category": "电子元件", "sub_category": "二极管", "model": "", "is_consumable": False, "tags": []}
        if "三极管" in name_lower or "mos" in name_lower:
            return {"category": "电子元件", "sub_category": "三极管/MOS", "model": "", "is_consumable": False, "tags": []}
        if "运放" in name_lower or "ne555" in name_lower:
            return {"category": "电子元件", "sub_category": "IC/运放", "model": "", "is_consumable": False, "tags": []}
        if "晶振" in name_lower:
            return {"category": "电子元件", "sub_category": "晶振", "model": "", "is_consumable": False, "tags": []}
        return {"category": "电子元件", "sub_category": "其他", "model": "", "is_consumable": False, "tags": []}

    # 连接/结构
    if any(kw in name_lower for kw in ["导线", "排线", "杜邦线", "排针", "面包板", "螺丝", "螺母", "铜柱", "支架", "底盘", "轮子", "联轴器", "亚克力"]):
        if "导线" in name_lower or "排线" in name_lower or "杜邦线" in name_lower:
            return {"category": "连接/结构", "sub_category": "导线/排线", "model": "", "is_consumable": False, "tags": []}
        if "面包板" in name_lower:
            return {"category": "连接/结构", "sub_category": "面包板/洞洞板", "model": "", "is_consumable": False, "tags": []}
        if "轮子" in name_lower or "底盘" in name_lower:
            return {"category": "连接/结构", "sub_category": "结构件(支架/底盘/轮子)", "model": "", "is_consumable": False, "tags": ["小车底盘"]}
        if "联轴器" in name_lower:
            return {"category": "连接/结构", "sub_category": "结构件(支架/底盘/轮子)", "model": "", "is_consumable": False, "tags": ["联轴器"]}
        return {"category": "连接/结构", "sub_category": "其他", "model": "", "is_consumable": False, "tags": []}

    # 工具
    if any(kw in name_lower for kw in ["万用表", "示波器", "电烙铁", "螺丝刀", "镊子", "剥线钳", "热风枪", "可调电源", "逻辑分析"]):
        if "示波器" in name_lower:
            return {"category": "工具", "sub_category": "测量仪器", "model": "", "is_consumable": False, "tags": ["示波器"]}
        if "电烙铁" in name_lower or "烙铁" in name_lower:
            return {"category": "工具", "sub_category": "焊接工具", "model": "", "is_consumable": False, "tags": []}
        if "可调电源" in name_lower:
            return {"category": "工具", "sub_category": "电源/信号源", "model": "", "is_consumable": False, "tags": ["可调电源"]}
        return {"category": "工具", "sub_category": "其他", "model": "", "is_consumable": False, "tags": []}

    # 耗材
    if any(kw in name_lower for kw in ["焊锡", "锡丝", "松香", "助焊剂", "热缩管", "扎带", "胶带", "胶水", "酒精", "洗板水"]):
        if "焊锡" in name_lower or "锡丝" in name_lower or "松香" in name_lower:
            return {"category": "耗材", "sub_category": "焊料/助焊剂", "model": "", "is_consumable": True, "tags": []}
        if "热缩管" in name_lower:
            return {"category": "耗材", "sub_category": "热缩管", "model": "", "is_consumable": True, "tags": []}
        if "扎带" in name_lower or "胶带" in name_lower:
            return {"category": "耗材", "sub_category": "胶带/胶水", "model": "", "is_consumable": True, "tags": []}
        return {"category": "耗材", "sub_category": "其他", "model": "", "is_consumable": True, "tags": []}

    # 完全无法识别，返回空
    return {"category": "", "sub_category": "", "model": "", "is_consumable": False, "tags": []}
