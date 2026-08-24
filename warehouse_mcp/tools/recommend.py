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
from warehouse_mcp.bom_library import search_bom_library, format_bom_refs


def _build_project_prompt(bom_refs: list = None) -> str:
    """构建项目物料清单推理的 system prompt。

    Args:
        bom_refs: 检索到的参考 BOM 列表（可为空），作为参考知识注入。
    """
    cat_lines = []
    for cat_name, cat_info in CATEGORIES.items():
        subs_str = "、".join(get_category_subs(cat_name))
        cat_lines.append(f"  {cat_name}（代码 {cat_info['code']}）：{subs_str}")

    bom_section = ""
    if bom_refs:
        bom_section = (
            "\n## 参考 BOM（实验室收集的真实项目物料清单，仅供参考）\n\n"
            + format_bom_refs(bom_refs)
            + "\n\n"
        )

    return f"""你是一个大学生科创实验室的物料管理助手。用户会描述他想做的项目（如"WiFi遥控小车"、"循迹小车"、"机械臂"），你需要推理出完成这个项目所需的物料清单，并给出可理解的说明。后续系统会对照库存检查哪些有、哪些缺。

## 分类体系

大类及子类如下：
{chr(10).join(cat_lines)}

## 项目类型自判断

科创项目大致分两类，请你自己判断用户的描述更接近哪一种，并据此调整推荐的发散程度：
- 偏「创新 DIY / 大创 / 自由选题」：顺着「控制核心 → 动力驱动 → 传动结构 → 感知输入 → 交互输出 → 供电 → 连接装配」的设计维度去发散，每个维度尽量给出主推方案 + 备选方案，给用户更多创新选择空间。
- 偏「竞赛固定题 / 电赛 / 嵌赛 / B类赛标准题」：参考标准 BOM 收敛到成熟可靠的配置，突出必需件，避免添加花哨无关物料。

在 output 的 project_type 字段标注：创新类写 "open"，竞赛固定类写 "competition"。

{bom_section}## 推理规则

1. 只输出完成该项目真正需要的物料，宁缺毋滥；不要为了凑数量添加无关物料（例如只要一块开发板，就不要加面包板、杜邦线、LED 等）；如果只是想要某一件具体物料而非项目，只输出这一项
2. category 必须是上述 10 个大类的完整中文名称，不能改字
3. sub_category 必须是该类下子类的完整名称，不能改字
4. name 写通用物料名称（如"直流减速电机"），不要写具体型号；型号/产品系列建议写在 options 里
5. quantity 是预计需要的件数（整数，≥1）
6. necessity：required=项目必需，optional=可选/锦上添花
7. role：一句话说明该物料在项目里干什么（如"驱动车轮行驶"）
8. why：一句话说明为什么需要它（如"提供动力，减速箱增大扭矩"）；optional 物料可简短
9. options：备选型号或方案（如"STM32F1/F4、ESP32 均可"），没有可留空
10. 明显互斥的备选方案（如"ESP32 或 STM32 二选一"）只列 1 项，把备选写进 options，避免重复计数
11. 若提供了「参考 BOM」，仅作参考：结合用户的具体需求做调整，允许创新补充，不要逐字照抄

## 可解释说明要求

- overview：用 1~2 段中文，说清楚这个项目的整体构成和大致工作原理（不要列清单，要讲清楚"是什么、怎么工作、由哪几部分协作"）
- 对 required（必需）物料，role 和 why 要写得清楚具体；对 optional 物料可一句话带过

## 输出格式

严格输出 JSON，不要有任何其他文字：
```json
{{
    "project_name": "WiFi遥控小车",
    "project_type": "open",
    "overview": "该小车以主控为核心，通过电机驱动板驱动直流减速电机带动车轮行驶，……",
    "items": [
        {{"name": "直流减速电机", "category": "执行/驱动", "sub_category": "直流电机", "quantity": 4, "necessity": "required", "role": "驱动车轮行驶", "why": "提供动力，减速箱增大扭矩", "options": "TT马达、N20 均可"}},
        {{"name": "超声波传感器", "category": "传感模块", "sub_category": "距离/位置", "quantity": 1, "necessity": "optional", "role": "避障", "why": "", "options": "HC-SR04"}}
    ]
}}
```"""


def infer_project(description: str, bom_refs: list = None) -> dict:
    """调用 LLM 推理项目所需物料清单（需要配置 API Key）。

    Args:
        description: 项目需求描述
        bom_refs: 检索到的参考 BOM 列表（可为空），注入 prompt 作为参考

    Returns:
        dict: {"project_name": str, "project_type": str, "overview": str,
               "items": [{name, category, sub_category, quantity, necessity,
                          role, why, options}]}

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
            {"role": "system", "content": _build_project_prompt(bom_refs)},
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
        "project_type": result.get("project_type", ""),
        "overview": result.get("overview", ""),
        "items": items,
    }


# ---- 离线规则版本 ----

def infer_project_fake(description: str) -> dict:
    """离线规则版项目推理（不调用 LLM，直接检索内置 BOM 参考库）。

    按关键词命中数取最相关的 BOM；未命中的抛 ValueError。
    """
    boms = search_bom_library(description, limit=1)
    if not boms:
        raise ValueError(
            "离线规则无法识别项目类型。请尝试更明确的描述"
            "（如'循迹小车'、'平衡车'、'机械臂'、'无人机'、'温湿度监测'）。"
        )

    bom = boms[0]
    items = [
        {
            "name": it["name"],
            "category": it["category"],
            "sub_category": it["sub_category"],
            "quantity": it["quantity"],
            "necessity": it["necessity"],
            "role": it.get("role", ""),
            "why": it.get("why", ""),
            "options": it.get("options", ""),
        }
        for it in bom["items"]
    ]
    scenario = bom.get("scenario", "")
    project_type = "competition" if ("竞赛" in scenario or "电赛" in scenario) else "open"

    return {
        "project_name": bom["name"],
        "project_type": project_type,
        "overview": bom.get("overview", ""),
        "items": items,
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
            "role": str(it.get("role", "")),
            "why": str(it.get("why", "")),
            "options": str(it.get("options", "")),
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

    # 1. LLM（或离线规则）推理物料清单（先检索 BOM 参考库作为参考）
    bom_refs = search_bom_library(description, limit=2)
    llm_error = ""
    try:
        if use_fake:
            inferred = infer_project_fake(description)
        else:
            inferred = infer_project(description, bom_refs)
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
        "project_type": inferred.get("project_type", ""),
        "overview": inferred.get("overview", ""),
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
    ]
    if result.get("overview"):
        lines.append(f"📋 项目说明：{result['overview']}")
    lines.append("─" * 40)

    for it in result["items"]:
        need = f"需{it['quantity']}"
        if it["necessity"] == "optional":
            need += "（可选）"
        explain_parts = []
        if it.get("role"):
            explain_parts.append(f"作用：{it['role']}")
        if it.get("why"):
            explain_parts.append(f"原因：{it['why']}")
        if it.get("options"):
            explain_parts.append(f"备选：{it['options']}")
        explain = f"（{' | '.join(explain_parts)}）" if explain_parts else ""
        header = f"「{it['name']}」{it['category']}>{it['sub_category']} {need}{explain}"

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
