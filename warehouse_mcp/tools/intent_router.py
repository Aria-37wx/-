# -*- coding: utf-8 -*-
"""意图路由 — LLM 分析用户自然语言输入，判断意图并提取参数"""

import re
from warehouse_mcp.db.database import CATEGORIES, get_category_subs
from warehouse_mcp.llm_client import _extract_json

# ---- LLM 版本 ----

def _build_context_block(context: dict) -> str:
    """多轮对话上下文说明（追加到 system prompt，让 LLM 判断细化/基于上下文出库/新话题）"""
    req = context.get("requirement", "")
    cnt = len(context.get("result_ids") or [])
    return f"""

## 当前对话上下文（非常重要）

用户正在进行多轮对话。此前的需求是：「{req}」，系统已经筛选出 {cnt} 条相关物料。

请判断用户这条新消息属于哪种情况：

1. **细化（refine）**：用户是在给刚才的查询补充约束/条件（例如"要强光的""用于照明的""蓝色的""大功率的""只要国产的"）。此时：intent 填 "search"，设置 "refine": true，description 填用户补充的约束原文，keyword 填 ""。

2. **基于上下文出库（from_context）**：用户想把刚才筛选出的结果直接出库（例如"出库""借这些""领用"）。此时：intent 填 "outbound"，设置 "from_context": true，keyword 填 ""。

3. **全新请求**：用户换了一个新话题（例如从"发光元件"跳到"电机"）。此时按正常规则分类，不要设置 refine/from_context。

无论哪种情况，输出 JSON 都要带 "refine" 和 "from_context" 两个布尔字段（默认为 false）。"""


def _build_intent_system_prompt(context=None) -> str:
    """构建意图分类的 system prompt"""
    cat_names = "、".join(CATEGORIES.keys())
    prompt = f"""你是一个大学生科创实验室的物料管理助手。用户会用自然语言描述他的需求，你需要分析他的意图。

## 可能的意图

1. **inbound（入库）**：用户想把新物料加入库存。关键词："到了"、"新买的"、"入库"、"有xx个"、"刚收到"
2. **outbound（出库）**：用户想借出或领用物料。关键词："借"、"拿"、"用一下"、"领"、"出库"
3. **search（查询）**：用户想查库存。关键词："有没有"、"在哪"、"查一下"、"库存"、"还有吗"、"找"
4. **return（归还）**：用户想归还借出的物料。关键词："还"、"归还"、"退回"、"还回来"
5. **recommend（项目推荐）**：用户描述一个想做/正在做的项目，需要系统给出**完整的多类物料清单**。关键词："做一个"、"想搞"、"项目"、"毕设"、"设计"、"搭建"、"需要哪些物料"、"怎么做"、"物料清单"
6. **unknown（未知）**：无法确定意图

**recommend 与其他意图的区分（非常重要）**：
- recommend = 描述一个"项目/作品"，需要**多类物料**的组合清单（如"做一辆小车"、"做个温湿度监测系统"）。
- outbound = 想要/借用**某一件具体的东西**（如"我想借一块 ESP32"、"领一个舵机"）。
- search = 想知道库存里**有没有/在哪**某件东西（如"有没有 uno 板子"、"查一下杜邦线"）。
- 即使用户提到了具体型号（uno、esp32、stm32、树莓派等），只要不是在描述一个需要多类物料的项目，就**不能判 recommend**，应判 search 或 outbound。

## 需要提取的信息

- **name**: 物料名称（根据描述猜测，如"USB扩展坞"、"TT直流电机"）。即使用户说"忘了叫啥"，也要根据描述推测一个名称。
- **description**: 补充描述（用户提到的所有细节，如品牌、功能、数量等）
- **quantity**: 数量（用户提到具体数字时提取，默认 1）
- **user_phone**: 手机号（11位数字）
- **keyword**: 搜索关键词。search 和 outbound 意图都必须填！把用户需求翻译成可搜索的关键词。例如用户说"低功耗无线通信"→ keyword="WiFi 蓝牙 LoRa 通信模块"，用户说"能跑Python的板子"→ keyword="MicroPython 开发板 ESP32 树莓派"

## 物料分类体系（供参考）

当前系统有这些大类：{cat_names}

## 输出格式

严格输出 JSON，不要有其他文字：
```json
{{
    "intent": "inbound",
    "name": "USB扩展坞",
    "description": "联想品牌，1个USB转3个USB+RJ45网口，约100个",
    "quantity": 100,
    "user_phone": "",
    "keyword": "",
    "confidence": "high",
    "reasoning": "用户说'刚到的'+数量→入库意图，描述USB转网口→推测为USB扩展坞"
}}
```

**重要规则**：
- name 一定要填，根据用户描述推测最可能的物料名称
- 即使用户说"忘了叫啥"，你也要尽力猜测一个合理的名字
- quantity 从用户话里提取数字，没有则填 1
- confidence: high=意图明确, medium=需确认, low=非常不确定
- reasoning 要简短解释你的判断逻辑

## 更多示例

入库: "刚买了5块ESP32开发板，WiFi蓝牙都有" → intent="inbound", name="ESP32开发板", description="支持WiFi和蓝牙", quantity=5, keyword=""

出库: "我想借一块能跑MicroPython的开发板" → intent="outbound", name="MicroPython开发板", keyword="MicroPython ESP32 树莓派Pico 开发板"

查询: "有没有低功耗的无线通信模块" → intent="search", keyword="低功耗 WiFi 蓝牙 LoRa 通信模块"

项目推荐: "我想做一辆WiFi遥控小车，需要哪些物料" → intent="recommend", name="WiFi遥控小车", description="WiFi遥控的四轮小车", quantity=1, keyword=""

项目推荐: "毕设想搞一个温湿度监测系统" → intent="recommend", name="温湿度监测系统", description="毕设项目：温湿度监测系统", quantity=1, keyword=""

查询（不是推荐）: "想要 uno 板子" → intent="search", name="Arduino Uno", keyword="uno arduino 开发板"

查询（不是推荐）: "有没有面包板" → intent="search", name="面包板", keyword="面包板" """
    if context:
        prompt += _build_context_block(context)
    return prompt


def classify_intent(user_input: str, context: dict = None) -> dict:
    """调用 LLM 分析用户意图（需要配置 API Key）。

    Args:
        user_input: 用户最新输入
        context: 多轮对话上下文 dict（可选），含 requirement / result_ids 等

    Returns:
        dict: {"intent", "name", "description", "quantity", "user_phone",
               "keyword", "confidence", "reasoning", "refine", "from_context"}
    """
    from warehouse_mcp.llm_client import _api_key, _base_url, _model, _get_openai

    if not _api_key:
        raise RuntimeError("未配置 LLM API Key，无法使用 AI 对话功能。")

    OpenAI = _get_openai()
    client = OpenAI(api_key=_api_key, base_url=_base_url)

    response = client.chat.completions.create(
        model=_model,
        messages=[
            {"role": "system", "content": _build_intent_system_prompt(context)},
            {"role": "user", "content": user_input},
        ],
        temperature=0.1,
        max_tokens=500,
    )

    content = response.choices[0].message.content.strip()
    result = _extract_json(content)

    # 确保必要字段存在
    result.setdefault("intent", "unknown")
    result.setdefault("name", "")
    result.setdefault("description", user_input)
    result.setdefault("quantity", 1)
    result.setdefault("user_phone", "")
    result.setdefault("keyword", "")
    result.setdefault("confidence", "low")
    result.setdefault("reasoning", "")
    result.setdefault("refine", False)
    result.setdefault("from_context", False)
    return result


# ---- 离线规则版本 ----

def classify_intent_fake(user_input: str, context: dict = None) -> dict:
    """离线规则版意图分类（不调用 LLM，基于关键词匹配）。

    覆盖常见场景，未覆盖的返回 unknown。支持多轮上下文：细化（refine）、基于上下文出库（from_context）。
    """
    text = user_input.strip()

    # 提取手机号
    phone = ""
    phone_match = re.search(r'1[3-9]\d{9}', text)
    if phone_match:
        phone = phone_match.group(0)

    # 提取数量
    quantity = 1
    qty_patterns = [
        (r'(\d+)\s*多?\s*个', 1),
        (r'(\d+)\s*多?\s*件', 1),
        (r'(\d+)\s*多?\s*台', 1),
        (r'(\d+)\s*多?\s*条', 1),
        (r'(\d+)\s*多?\s*盒', 1),
        (r'(\d+)\s*多?\s*包', 1),
        (r'(\d+)\s*多?\s*根', 1),
        (r'(\d+)\s*多?\s*块', 1),
        (r'(\d+)\s*多?\s*卷', 1),
        (r'([一二三四五六七八九十百千万]+)\s*多?\s*[个件台条盒包根块卷]', 0),
    ]
    for pat, _ in qty_patterns:
        m = re.search(pat, text)
        if m:
            try:
                quantity = int(m.group(1))
            except ValueError:
                quantity = _chinese_num_to_int(m.group(1))
            break

    # 意图判断
    inbound_words = ["到货", "新到", "刚到的", "刚收到", "新买", "入库", "登记", "加进去", "放进去", "加一下", "刚到"]
    outbound_words = ["借", "拿", "用一下", "领", "出库", "拿走", "取", "借用", "领用"]
    search_words = ["有没有", "在哪", "查一下", "找", "库存", "还有吗", "看看", "在哪", "有什么", "哪些"]
    return_words = ["归还", "退回", "还回来", "还了", "还掉", "退了"]
    recommend_words = ["做一个", "做个", "想做", "想搞", "搞一个", "搞个", "毕设", "大创",
                       "项目", "设计一个", "搭一个", "搭建", "制作", "diy",
                       "需要哪些物料", "物料清单", "需要什么", "怎么做", "整一个"]

    # ---- 多轮上下文感知：存在活跃查询结果时，优先判断「基于上下文出库」和「细化」 ----
    if context and context.get("result_ids"):
        # 1. 基于上下文的出库指令（短指令，没引入新物料主语）
        if _is_bare_outbound(text, outbound_words):
            return {
                "intent": "outbound",
                "name": "",
                "description": text,
                "quantity": 1,
                "user_phone": phone,
                "keyword": "",
                "confidence": "high",
                "reasoning": "检测到基于上下文的出库指令",
                "refine": False,
                "from_context": True,
            }
        # 2. 细化（补充约束条件），且没有明显的新意图词
        if _looks_like_refinement(
            text, inbound_words, outbound_words, search_words, return_words, recommend_words
        ):
            return {
                "intent": "search",
                "name": "",
                "description": text,
                "quantity": 1,
                "user_phone": phone,
                "keyword": "",
                "confidence": "medium",
                "reasoning": "检测到对当前查询的细化描述",
                "refine": True,
                "from_context": False,
            }

    inbound_score = sum(1 for w in inbound_words if w in text)
    outbound_score = sum(1 for w in outbound_words if w in text)
    search_score = sum(1 for w in search_words if w in text)
    return_score = sum(1 for w in return_words if w in text)
    recommend_score = sum(1 for w in recommend_words if w in text)

    scores = {
        "inbound": inbound_score,
        "outbound": outbound_score,
        "search": search_score,
        "return": return_score,
        "recommend": recommend_score,
    }
    max_intent = max(scores, key=scores.get)
    max_score = scores[max_intent]

    # recommend 与其他意图同分时优先（描述项目的说法比泛搜索词更具体）
    if recommend_score > 0 and recommend_score == max_score:
        max_intent = "recommend"
        max_score = recommend_score

    if max_score == 0:
        # 检查有没有数量暗示 → 可能是入库
        if quantity > 1:
            max_intent = "inbound"
            max_score = 1
        else:
            guessed = _guess_name(text)
            if guessed:
                return {
                    "intent": "search",
                    "name": guessed,
                    "description": text,
                    "quantity": 1,
                    "user_phone": phone,
                    "keyword": guessed,
                    "confidence": "low",
                    "reasoning": f"离线规则检测到具体物料「{guessed}」，默认按查询处理",
                }
            return {
                "intent": "unknown",
                "name": "",
                "description": text,
                "quantity": 1,
                "user_phone": phone,
                "keyword": "",
                "confidence": "low",
                "reasoning": "离线规则无法识别意图，请尝试更明确的表述。"
            }

    # 尝试猜物料名（recommend 意图猜不出具体物料，留空，由推荐工具根据完整描述分析）
    name = "" if max_intent == "recommend" else _guess_name(text)

    # 提取搜索关键词
    keyword = ""
    if max_intent in ("search", "outbound"):
        # 去掉意图词，剩余的就是关键词
        kw_text = text
        all_intent_words = set(inbound_words + outbound_words + search_words + return_words)
        for w in sorted(all_intent_words, key=len, reverse=True):
            kw_text = kw_text.replace(w, "")
        keyword = kw_text.strip().rstrip("？?。，,")
        # 去掉口语主语/请求前缀（"我想/我要/帮我..."），避免关键词混入主语
        for p in ["我想", "我要", "帮我", "给我", "麻烦", "请问", "想", "要", "请", "帮"]:
            if keyword.startswith(p):
                keyword = keyword[len(p):].strip()
                break

    result = {
        "intent": max_intent,
        "name": name,
        "description": text,
        "quantity": max(quantity, 1),
        "user_phone": phone,
        "keyword": keyword or name,
        "confidence": "medium" if max_score >= 2 else "low",
        "reasoning": f"离线规则匹配到{max_intent}关键词（得分{max_score}）",
        "refine": False,
        "from_context": False,
    }
    return result


def _guess_name(text: str) -> str:
    """从文本中尝试猜测物料名称（离线规则）"""
    # 常见科创物料关键词 → 名称映射
    name_map = [
        (["扩展坞", "usb.*转", "usb.*网"], "USB扩展坞"),
        (["电机", "马达"], "电机"),
        (["舵机", "伺服"], "舵机"),
        (["开发板"], "开发板"),
        (["传感器"], "传感器"),
        (["电池"], "电池"),
        (["导线", "杜邦线", "排线"], "导线"),
        (["面包板"], "面包板"),
        (["电阻"], "电阻"),
        (["电容"], "电容"),
        (["焊锡", "锡丝"], "焊锡丝"),
        (["热缩管"], "热缩管"),
        (["螺丝", "螺母", "螺钉"], "螺丝"),
        (["万用表"], "万用表"),
        (["电烙铁", "烙铁"], "电烙铁"),
        (["示波器"], "示波器"),
        (["蓝牙"], "蓝牙模块"),
        (["wifi", "WiFi"], "WiFi模块"),
        (["lora", "LoRa"], "LoRa模块"),
        (["arduino", "Arduino"], "Arduino"),
        (["uno"], "Arduino Uno"),
        (["esp32", "ESP32"], "ESP32"),
        (["esp8266", "ESP8266"], "ESP8266"),
        (["stm32", "STM32"], "STM32"),
        (["树莓派"], "树莓派"),
        (["lcd", "LCD", "液晶"], "LCD屏幕"),
        (["oled", "OLED"], "OLED屏幕"),
        (["蜂鸣器"], "蜂鸣器"),
    ]
    text_lower = text.lower()
    for keywords, name in name_map:
        for kw in keywords:
            if kw.lower() in text_lower:
                return name
    return ""


def _chinese_num_to_int(s: str) -> int:
    """中文数字转整数（简化版）"""
    mapping = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
               "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "百": 100}
    if s in mapping:
        return mapping[s]
    # "几十" 模式
    if "十" in s:
        parts = s.split("十")
        tens = mapping.get(parts[0], 1) * 10
        ones = mapping.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
        return tens + ones
    return 1


def _is_bare_outbound(text: str, outbound_words: list) -> bool:
    """判断是否是「基于上下文的裸出库指令」（如"出库""借这些""领用"，没引入新物料主语）。"""
    t = text
    for w in sorted(outbound_words, key=len, reverse=True):
        t = t.replace(w, "")
    # 去掉语气词 / 指示词 / 数量单位
    for w in ["这些", "那些", "它们", "就", "吧", "的", "了", "一下", "物料", "东西",
              "这个", "那个", "全部", "都", "全", "先", "直接", "麻烦", "帮我", "给我",
              "请", "要", "想", "都给我"]:
        t = t.replace(w, "")
    t = re.sub(r'[\d一二三四五六七八九十百千万两]+', '', t)
    t = re.sub(r'[个件台块根卷盒包张支条]', '', t)
    t = t.strip().strip("，。？！?., ")
    return t == ""


def _looks_like_refinement(text: str, inbound_words, outbound_words, search_words,
                           return_words, recommend_words) -> bool:
    """判断是否是对当前查询的「细化」（补充约束，且没有明显新意图词）。"""
    all_intent = inbound_words + outbound_words + search_words + return_words + recommend_words
    if any(w in text for w in all_intent):
        return False
    refine_starts = ["要", "想要", "需要", "用于", "用作", "只要", "最好是", "得是",
                     "是", "改成", "换成", "带", "要带", "能", "有", "带", "最好", "强"]
    if any(text.startswith(w) for w in refine_starts):
        return True
    refine_contains = ["用于", "用作", "强光", "高亮", "大功率", "更亮", "功率",
                       "亮度", "颜色", "蓝色", "红色", "白色", "绿色", "黄色",
                       "只要", "或者", "还是", "防水", "耐高温", "低压", "高压"]
    if any(w in text for w in refine_contains):
        return True
    return False
