# -*- coding: utf-8 -*-
"""智能推荐工具 — LLM 根据项目需求推理物料清单，对照库存给出可出库清单 + 缺料预警

流程：
    1. LLM（或离线规则）把项目需求翻译成结构化物料清单
    2. 对照库存做三级匹配：
       ① 大类+子类精确匹配（quantity > 0）
       ② 命中不足/缺失 → 同大类按名称/标签相似度给出替代品建议
       ③ 完全无货 → 缺料预警
    3. 输出：可出库清单（✅/⚠️/❌）+ 替代建议（💡）
"""

from warehouse_mcp.db.database import get_db, CATEGORIES, get_category_subs
from warehouse_mcp.llm_client import _extract_json


def _build_project_prompt() -> str:
    """构建项目物料清单推理的 system prompt"""
    cat_lines = []
    for cat_name, cat_info in CATEGORIES.items():
        subs_str = "、".join(get_category_subs(cat_name))
        cat_lines.append(f"  {cat_name}（代码 {cat_info['code']}）：{subs_str}")

    return f"""你是一个大学生科创实验室的物料管理助手。用户会描述他想做的项目（如"WiFi遥控小车"、"温湿度监测"），你需要推理出完成这个项目所需的物料清单，后续系统会对照库存检查哪些有、哪些缺。

## 分类体系

大类及子类如下：
{chr(10).join(cat_lines)}

## 推理规则

1. 只输出完成该项目真正需要的物料，宁缺毋滥；不要为了凑数量添加无关物料（例如只要一块开发板，就不要加面包板、杜邦线、LED 等）；如果只是想要某一件具体物料而非项目，只输出这一项
2. category 必须是上述 10 个大类的完整中文名称，不能改字
3. sub_category 必须是该类下子类的完整名称，不能改字
4. name 写通用物料名称（如"直流减速电机"），不要写具体型号；型号/产品系列建议写在 note 里（如"ESP32 或 STM32 均可"）
5. quantity 是预计需要的件数（整数，≥1）
6. necessity：required=项目必需，optional=可选/锦上添花
7. note：一句话说明用途或选型建议
8. 明显互斥的备选方案（如"ESP32 或 STM32 二选一"）只列 1 项，把备选写进 note，避免重复计数

## 输出格式

严格输出 JSON，不要有任何其他文字：
```json
{{
    "project_name": "WiFi遥控小车",
    "items": [
        {{"name": "直流减速电机", "category": "执行/驱动", "sub_category": "直流电机", "quantity": 4, "necessity": "required", "note": "驱动车轮"}},
        {{"name": "电机驱动板", "category": "执行/驱动", "sub_category": "电机驱动板", "quantity": 1, "necessity": "required", "note": "L298N 或 TB6612"}},
        {{"name": "超声波传感器", "category": "传感模块", "sub_category": "距离/位置", "quantity": 1, "necessity": "optional", "note": "避障，可选"}}
    ]
}}
```"""


def infer_project(description: str) -> dict:
    """调用 LLM 推理项目所需物料清单（需要配置 API Key）。

    Returns:
        dict: {"project_name": str, "items": [{name, category, sub_category,
               quantity, necessity, note}]}

    Raises:
        RuntimeError: LLM 未配置 API Key
        ValueError: LLM 返回无法解析
    """
    from warehouse_mcp.llm_client import _api_key, _base_url, _model, _get_openai

    if not _api_key:
        raise RuntimeError("未配置 LLM API Key，无法使用智能推荐功能。")

    OpenAI = _get_openai()
    client = OpenAI(api_key=_api_key, base_url=_base_url)

    response = client.chat.completions.create(
        model=_model,
        messages=[
            {"role": "system", "content": _build_project_prompt()},
            {"role": "user", "content": description},
        ],
        temperature=0.2,
        max_tokens=1500,
    )

    content = response.choices[0].message.content.strip()
    result = _extract_json(content)

    if not isinstance(result, dict):
        raise ValueError(f"LLM 返回的不是 JSON 对象: {content[:200]}")

    items = result.get("items", [])
    if not isinstance(items, list) or not items:
        raise ValueError("LLM 返回的物料清单为空。")

    return {
        "project_name": result.get("project_name", ""),
        "items": items,
    }


# ---- 离线规则版本 ----

# 预置项目模板：关键词 → 物料清单（保证无 API Key 也能演示）
_PROJECT_TEMPLATES = [
    (
        "智能小车",
        ["小车", "遥控车", "循迹", "避障", "竞速", "四轮"],
        [
            {"name": "主控开发板", "category": "主控板", "sub_category": "MCU/单片机", "quantity": 1, "necessity": "required", "note": "ESP32 或 STM32F4"},
            {"name": "直流减速电机", "category": "执行/驱动", "sub_category": "直流电机", "quantity": 4, "necessity": "required", "note": "驱动车轮"},
            {"name": "电机驱动板", "category": "执行/驱动", "sub_category": "电机驱动板", "quantity": 1, "necessity": "required", "note": "L298N 或 TB6612"},
            {"name": "电池", "category": "电源模块", "sub_category": "电池", "quantity": 2, "necessity": "required", "note": "18650"},
            {"name": "超声波传感器", "category": "传感模块", "sub_category": "距离/位置", "quantity": 1, "necessity": "optional", "note": "HC-SR04 避障"},
            {"name": "小车底盘", "category": "连接/结构", "sub_category": "结构件(支架/底盘/轮子)", "quantity": 1, "necessity": "required", "note": "含轮子"},
            {"name": "杜邦线", "category": "连接/结构", "sub_category": "导线/排线", "quantity": 1, "necessity": "optional", "note": "连接用"},
        ],
    ),
    (
        "温湿度监测",
        ["温湿度", "环境监测", "气象站", "温控", "温度监测", "湿度"],
        [
            {"name": "主控开发板", "category": "主控板", "sub_category": "MCU/单片机", "quantity": 1, "necessity": "required", "note": "ESP32 带 WiFi 上报"},
            {"name": "温湿度传感器", "category": "传感模块", "sub_category": "温度/湿度", "quantity": 1, "necessity": "required", "note": "DHT11 或 DHT22"},
            {"name": "OLED显示屏", "category": "显示/交互", "sub_category": "OLED/LCD", "quantity": 1, "necessity": "optional", "note": "本地显示"},
            {"name": "电池", "category": "电源模块", "sub_category": "电池", "quantity": 1, "necessity": "required", "note": "18650 供电"},
            {"name": "面包板", "category": "连接/结构", "sub_category": "面包板/洞洞板", "quantity": 1, "necessity": "optional", "note": "搭电路"},
        ],
    ),
    (
        "蓝牙遥控",
        ["蓝牙遥控", "蓝牙控制", "手机遥控", "app遥控", "蓝牙小车"],
        [
            {"name": "蓝牙模块", "category": "通信模块", "sub_category": "蓝牙", "quantity": 1, "necessity": "required", "note": "HC-05 串口透传"},
            {"name": "主控开发板", "category": "主控板", "sub_category": "MCU/单片机", "quantity": 1, "necessity": "required", "note": "Arduino 或 STM32"},
            {"name": "舵机", "category": "执行/驱动", "sub_category": "舵机/伺服", "quantity": 2, "necessity": "optional", "note": "SG90 转向/云台"},
            {"name": "电池", "category": "电源模块", "sub_category": "电池", "quantity": 1, "necessity": "required", "note": ""},
        ],
    ),
    (
        "机械臂",
        ["机械臂", "机械手", "抓取", "多轴"],
        [
            {"name": "舵机", "category": "执行/驱动", "sub_category": "舵机/伺服", "quantity": 4, "necessity": "required", "note": "4 自由度关节"},
            {"name": "主控开发板", "category": "主控板", "sub_category": "MCU/单片机", "quantity": 1, "necessity": "required", "note": "STM32 或 Arduino"},
            {"name": "电源适配器", "category": "电源模块", "sub_category": "电源适配器", "quantity": 1, "necessity": "required", "note": "5V 大电流"},
            {"name": "机械臂支架", "category": "连接/结构", "sub_category": "结构件(支架/底盘/轮子)", "quantity": 1, "necessity": "required", "note": "亚克力或金属"},
            {"name": "按键", "category": "显示/交互", "sub_category": "按键/旋钮", "quantity": 2, "necessity": "optional", "note": "手动控制"},
        ],
    ),
    (
        "平衡车",
        ["平衡车", "自平衡", "两轮", "直立"],
        [
            {"name": "主控开发板", "category": "主控板", "sub_category": "MCU/单片机", "quantity": 1, "necessity": "required", "note": "STM32F4 做 PID"},
            {"name": "姿态传感器", "category": "传感模块", "sub_category": "运动/姿态(IMU)", "quantity": 1, "necessity": "required", "note": "MPU6050"},
            {"name": "直流减速电机", "category": "执行/驱动", "sub_category": "直流电机", "quantity": 2, "necessity": "required", "note": "带编码器更佳"},
            {"name": "电机驱动板", "category": "执行/驱动", "sub_category": "电机驱动板", "quantity": 1, "necessity": "required", "note": "TB6612"},
            {"name": "电池", "category": "电源模块", "sub_category": "电池", "quantity": 2, "necessity": "required", "note": "18650"},
        ],
    ),
    (
        "无人机",
        ["无人机", "四轴", "四旋翼", "飞控", "飞行器"],
        [
            {"name": "飞控板", "category": "主控板", "sub_category": "MCU/单片机", "quantity": 1, "necessity": "required", "note": "STM32F4 飞控"},
            {"name": "姿态传感器", "category": "传感模块", "sub_category": "运动/姿态(IMU)", "quantity": 1, "necessity": "required", "note": "MPU6050"},
            {"name": "无刷电机", "category": "执行/驱动", "sub_category": "直流电机", "quantity": 4, "necessity": "required", "note": "配螺旋桨"},
            {"name": "电调", "category": "执行/驱动", "sub_category": "电机驱动板", "quantity": 4, "necessity": "required", "note": "无刷电调"},
            {"name": "遥控接收机", "category": "通信模块", "sub_category": "射频/NFC", "quantity": 1, "necessity": "required", "note": "配遥控器"},
            {"name": "电池", "category": "电源模块", "sub_category": "电池", "quantity": 1, "necessity": "required", "note": "3S 锂电"},
        ],
    ),
    (
        "智能家居",
        ["智能家居", "灯控", "远程开关", "继电器", "家居"],
        [
            {"name": "主控开发板", "category": "主控板", "sub_category": "MCU/单片机", "quantity": 1, "necessity": "required", "note": "ESP8266/ESP32 联网"},
            {"name": "继电器模块", "category": "执行/驱动", "sub_category": "继电器/接触器", "quantity": 2, "necessity": "required", "note": "控制灯具/电器"},
            {"name": "LED灯", "category": "显示/交互", "sub_category": "LED/数码管", "quantity": 2, "necessity": "optional", "note": "状态指示"},
            {"name": "电源适配器", "category": "电源模块", "sub_category": "电源适配器", "quantity": 1, "necessity": "required", "note": "5V 供电"},
        ],
    ),
    (
        "视觉识别",
        ["视觉", "摄像头", "人脸", "图像识别", "opencv", "机器视觉", "目标检测"],
        [
            {"name": "摄像头模块", "category": "传感模块", "sub_category": "光/颜色/图像", "quantity": 1, "necessity": "required", "note": "USB 摄像头或 OV2640"},
            {"name": "单板计算机", "category": "主控板", "sub_category": "单板机SBC", "quantity": 1, "necessity": "required", "note": "树莓派或 K210 跑 OpenCV"},
            {"name": "OLED显示屏", "category": "显示/交互", "sub_category": "OLED/LCD", "quantity": 1, "necessity": "optional", "note": "显示识别结果"},
            {"name": "蜂鸣器", "category": "显示/交互", "sub_category": "蜂鸣器/扬声器", "quantity": 1, "necessity": "optional", "note": "识别成功报警"},
            {"name": "电源适配器", "category": "电源模块", "sub_category": "电源适配器", "quantity": 1, "necessity": "required", "note": "树莓派 5V 供电"},
        ],
    ),
    (
        "电子秤",
        ["电子秤", "称重", "压力", "体重秤"],
        [
            {"name": "称重传感器", "category": "传感模块", "sub_category": "其他", "quantity": 1, "necessity": "required", "note": "HX711 + 称重模块"},
            {"name": "主控开发板", "category": "主控板", "sub_category": "MCU/单片机", "quantity": 1, "necessity": "required", "note": ""},
            {"name": "OLED显示屏", "category": "显示/交互", "sub_category": "OLED/LCD", "quantity": 1, "necessity": "required", "note": "显示重量"},
            {"name": "电池", "category": "电源模块", "sub_category": "电池", "quantity": 1, "necessity": "optional", "note": ""},
        ],
    ),
]


def infer_project_fake(description: str) -> dict:
    """离线规则版项目推理（不调用 LLM，内置常见项目模板）。

    模板之间按关键词命中数计分，取最高分；未命中的抛 ValueError。
    """
    text = description.lower()
    best, best_score = None, 0
    for name, keywords, items in _PROJECT_TEMPLATES:
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score > best_score:
            best, best_score = (name, keywords, items), score

    if best is None:
        raise ValueError(
            "离线规则无法识别项目类型。请尝试更明确的描述"
            "（如'智能小车'、'温湿度监测'、'机械臂'、'平衡车'）。"
        )

    return {
        "project_name": best[0],
        "items": best[2],
        "offline": True,
    }


# ---- 库存匹配（确定性逻辑，不用 LLM）----

def _normalize_items(items: list) -> tuple:
    """校验物料清单，过滤不在分类体系中的条目。

    Returns:
        (valid_items, dropped): 有效条目 + 被丢弃条目的说明
    """
    valid, dropped = [], []
    for it in items:
        if not isinstance(it, dict):
            continue
        cat = str(it.get("category", "")).strip()
        sub = str(it.get("sub_category", "")).strip()
        name = str(it.get("name", "")).strip() or f"{cat}-{sub}"
        try:
            qty = int(it.get("quantity", 1))
        except (TypeError, ValueError):
            qty = 1

        if cat not in CATEGORIES or sub not in get_category_subs(cat):
            dropped.append(f"「{name}」（category={cat}, sub_category={sub}）不在分类体系中，已忽略")
            continue

        valid.append({
            "name": name,
            "category": cat,
            "sub_category": sub,
            "quantity": max(qty, 1),
            "necessity": it.get("necessity", "required"),
            "note": str(it.get("note", "")),
        })
    return valid, dropped


def _similarity_score(item_name: str, cand_name: str, cand_model: str, tag_list: str) -> int:
    """名称相似度：item 名称的 2 字片段在候选物料名称/型号/标签中的命中数"""
    text = f"{cand_name} {cand_model} {tag_list}".lower()
    name = item_name.lower()
    score = 0
    if name and name in text:
        score += 3
    # 2 字滑动窗口（对中文名称有效）
    bigrams = {name[i:i + 2] for i in range(len(name) - 1)} if len(name) >= 2 else set()
    score += sum(1 for bg in bigrams if bg in text)
    return score


def _match_inventory(items: list) -> tuple:
    """对照库存做三级匹配。

    Returns:
        (matched_items, summary): 每条含 status/available_qty/shortage/matched/alternatives，
        汇总含 ok/partial/missing 计数
    """
    conn = get_db()
    try:
        results = []
        summary = {"ok": 0, "partial": 0, "missing": 0}
        for it in items:
            # ① 大类+子类精确匹配
            rows = conn.execute(
                """SELECT id, name, category, sub_category, model,
                          is_consumable, quantity, location
                   FROM materials
                   WHERE category = ? AND sub_category = ? AND quantity > 0
                   ORDER BY quantity DESC, name""",
                (it["category"], it["sub_category"])
            ).fetchall()
            available = sum(r["quantity"] for r in rows)
            shortage = max(0, it["quantity"] - available)

            if available >= it["quantity"]:
                status = "ok"
            elif available > 0:
                status = "partial"
            else:
                status = "missing"
            summary[status] += 1

            # ② 不足/缺失 → 同大类替代品（按名称/标签相似度排序，取前 3）
            alternatives = []
            if shortage > 0:
                alt_rows = conn.execute(
                    """SELECT m.id, m.name, m.category, m.sub_category, m.model,
                              m.quantity, m.location, GROUP_CONCAT(t.name, ', ') AS tag_list
                       FROM materials m
                       LEFT JOIN material_tags mt ON m.id = mt.material_id
                       LEFT JOIN tags t ON mt.tag_name = t.name
                       WHERE m.category = ? AND m.sub_category != ? AND m.quantity > 0
                       GROUP BY m.id""",
                    (it["category"], it["sub_category"])
                ).fetchall()
                scored = [
                    (_similarity_score(it["name"], r["name"], r["model"], r["tag_list"] or ""), r)
                    for r in alt_rows
                ]
                scored = [s for s in scored if s[0] > 0]
                scored.sort(key=lambda x: -x[0])

                # 同名物料聚合为一条（数量累加），避免重复展示
                alternatives = []
                seen_names = set()
                for _, r in scored:
                    if r["name"] in seen_names:
                        for a in alternatives:
                            if a["name"] == r["name"]:
                                a["quantity"] += r["quantity"]
                        continue
                    seen_names.add(r["name"])
                    alternatives.append(dict(r))
                    if len(alternatives) >= 3:
                        break

            results.append({
                **it,
                "status": status,
                "available_qty": available,
                "shortage": shortage,
                "matched": [dict(r) for r in rows],
                "alternatives": alternatives,
            })
        return results, summary
    finally:
        conn.close()


# ---- 对外接口 ----

def analyze_project(description: str, use_fake: bool = False) -> dict:
    """分析项目需求并对照库存（不直接出库，供前端确认用）。

    Returns:
        dict: {
            "success": True/False,
            "error": "错误信息"（仅失败时）,
            "project_name": "项目名",
            "description": "原始描述",
            "items": [每条含 name/category/sub_category/quantity/necessity/note
                      + status(ok/partial/missing)/available_qty/shortage
                      + matched[库存命中] + alternatives[同类替代]],
            "dropped": [被忽略条目的说明],
            "summary": {"ok": n, "partial": n, "missing": n},
        }
    """
    if not description.strip():
        return {"success": False, "error": "项目描述不能为空。"}

    # 1. LLM（或离线规则）推理物料清单
    llm_error = ""
    try:
        if use_fake:
            inferred = infer_project_fake(description)
        else:
            inferred = infer_project(description)
    except Exception as e:
        # LLM 未配置或调用失败，降级到离线规则
        llm_error = str(e)
        try:
            inferred = infer_project_fake(description)
        except Exception:
            return {
                "success": False,
                "error": "无法推理出物料清单：LLM 调用失败且离线规则未命中项目模板。"
                         "请尝试更明确的描述（如'智能小车'、'温湿度监测'、'机械臂'）。",
            }

    # 2. 校验清单
    valid_items, dropped = _normalize_items(inferred.get("items", []))
    if not valid_items:
        return {
            "success": False,
            "error": "无法推理出有效的物料清单，请补充项目描述"
                     f"{'（离线规则未命中项目模板）' if dropped else ''}。",
        }

    # 3. 对照库存匹配
    matched_items, summary = _match_inventory(valid_items)

    return {
        "success": True,
        "project_name": inferred.get("project_name", ""),
        "description": description.strip(),
        "items": matched_items,
        "dropped": dropped,
        "summary": summary,
        "llm_error": llm_error,
    }


def _append_alternatives(lines: list, it: dict):
    """追加替代品建议到输出行"""
    if it["alternatives"]:
        lines.append("    💡 同类替代：")
        for a in it["alternatives"]:
            lines.append(
                f"       [{a['id']}] {a['name']}（{a['sub_category']}）"
                f"库存{a['quantity']} 位置:{a['location'] or '未指定'}"
            )
    else:
        lines.append("    💡 无同类替代品，建议采购")


def recommend_for_project(description: str, use_fake: bool = False) -> str:
    """智能推荐：根据项目需求推荐物料清单并对照库存。

    Args:
        description: 项目需求描述，如"我想做一辆 WiFi 遥控的四轮小车，能避障"
        use_fake: 是否使用离线规则（默认 False，优先尝试真实 LLM）

    Returns:
        格式化文本：可出库清单（✅/⚠️/❌）+ 替代建议（💡）+ 缺料预警
    """
    result = analyze_project(description, use_fake=use_fake)
    if not result.get("success"):
        return f"智能推荐失败：{result.get('error', '未知错误')}"

    lines = [
        f"项目：{result.get('project_name') or '（未命名项目）'}",
        f"需求描述：{result['description']}",
        "─" * 40,
    ]

    for it in result["items"]:
        need = f"需{it['quantity']}"
        if it["necessity"] == "optional":
            need += "（可选）"
        note = f" — {it['note']}" if it["note"] else ""
        header = f"「{it['name']}」{it['category']}>{it['sub_category']} {need}{note}"

        if it["status"] == "ok":
            lines.append(f"✅ 有货 {header}")
            for m in it["matched"][:3]:
                lines.append(
                    f"    [{m['id']}] {m['name']} 库存{m['quantity']} "
                    f"位置:{m['location'] or '未指定'}"
                )
        elif it["status"] == "partial":
            lines.append(f"⚠️ 不足 {header} 库存仅{it['available_qty']}，缺{it['shortage']}")
            for m in it["matched"][:3]:
                lines.append(
                    f"    [{m['id']}] {m['name']} 库存{m['quantity']} "
                    f"位置:{m['location'] or '未指定'}"
                )
            _append_alternatives(lines, it)
        else:
            lines.append(f"❌ 缺货 {header}")
            _append_alternatives(lines, it)

    s = result["summary"]
    lines.append("─" * 40)
    lines.append(f"汇总：可满足 {s['ok']} 项 | 部分满足 {s['partial']} 项 | 缺货 {s['missing']} 项")
    if result.get("dropped"):
        lines.append(f"注：{len(result['dropped'])} 条被忽略（不在分类体系中）")
    if result.get("llm_error"):
        lines.append(f"注：LLM 调用失败，已降级为离线规则（{result['llm_error'][:100]}）")

    return "\n".join(lines)
