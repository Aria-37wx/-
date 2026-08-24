# -*- coding: utf-8 -*-
"""搜索结果过滤 — 用 LLM（或离线规则）理解用户真实意图，剔除关键词误匹配的干扰项。

解决的问题：关键词搜索是子串匹配，比如搜"电阻"会同时命中"电阻"和"电阻传感器"。
这里在拿到候选物料后，再让 LLM 判断哪些候选才真正符合用户意图，而不是机械返回所有子串命中。
"""

from warehouse_mcp.llm_client import _extract_json


def _build_filter_prompt() -> str:
    return """你是一个大学生科创实验室的物料管理助手。系统已经按关键词搜索出一批候选物料，但关键词是子串匹配，可能混入了"名字里含有关键词、但其实是另一类东西"的干扰项。你的任务是根据用户真正想要的东西，筛选出真正相关的候选物料。

## 输入

1. 用户需求（原话）
2. 候选物料列表（每项：id、名称、大类、子类、型号、库存）

## 判断规则

1. 先理解用户到底想要什么。例如"出库电阻"= 普通电阻元件（色环电阻、贴片电阻、电位器等），而不是"电阻传感器""热敏电阻传感器"这类名字里带"电阻"但属于传感器/模块的东西。
2. 名称完全对应、或明显同属一类（同子类/同系列）→ 保留。
3. 名称只是"包含"关键词、但属于明显不同品类（如搜"电阻"命中"电阻传感器"，搜"电机"命中"电机驱动板"这种用户没提的衍生件）→ 排除。
4. 宁缺毋滥：拿不准时倾向排除，别给用户一堆不相关的。
5. 如果候选里没有真正符合的，keep_ids 返回空数组。

## 输出格式

严格输出 JSON，不要有任何其他文字。keep_ids 填写候选物料里你想保留项的 id（字符串，原样照抄候选列表里的 id）：
```json
{
    "summary": "一句话说明你的筛选判断",
    "keep_ids": ["EC-RES-20260824-0001", "EC-RES-20260824-0002"]
}
```"""


def filter_materials(query: str, materials: list) -> dict:
    """调用 LLM 筛选候选物料（需要配置 API Key）。

    Returns:
        {"keep_ids": [int], "summary": str}
    """
    from warehouse_mcp.llm_client import _api_key, _base_url, _model, _get_openai

    if not _api_key:
        raise RuntimeError("未配置 LLM API Key，无法使用智能筛选。")

    OpenAI = _get_openai()
    client = OpenAI(api_key=_api_key, base_url=_base_url)

    lines = []
    for m in materials:
        model = m.get("model") or "-"
        lines.append(
            f"- id={m['id']} {m['name']}（{m['category']}>{m['sub_category']}"
            f"，型号 {model}，库存 {m.get('quantity', 0)}）"
        )
    user_content = f"用户需求：{query}\n\n候选物料：\n" + "\n".join(lines)

    response = client.chat.completions.create(
        model=_model,
        messages=[
            {"role": "system", "content": _build_filter_prompt()},
            {"role": "user", "content": user_content},
        ],
        temperature=0.1,
        max_tokens=800,
    )
    content = response.choices[0].message.content.strip()
    result = _extract_json(content)
    keep_ids = result.get("keep_ids", [])
    if not isinstance(keep_ids, list):
        keep_ids = []
    return {
        "keep_ids": [str(i) for i in keep_ids],
        "summary": str(result.get("summary", "")),
    }


# 干扰词：名称里混入这些词、但用户关键词本身不含，说明是"名字含关键词的另一类东西"
_INTERFERE_WORDS = ["传感器", "模块", "驱动", "开发板", "转接", "检测", "变送器", "探头", "控制器"]


def filter_materials_fake(query: str, materials: list) -> dict:
    """离线规则版筛选：精确/前缀命中优先，剔除"名称仅包含关键词但不同品类"的干扰项。"""
    q = (query or "").strip().lower()
    if not q:
        return {"keep_ids": [m["id"] for m in materials], "summary": ""}

    def score(m):
        name = (m.get("name") or "").strip().lower()
        if name == q:
            return 100
        if name.startswith(q):
            return 90
        if q in name:
            if any(w in name for w in _INTERFERE_WORDS if w not in q):
                return 10
            return 60
        if q in (m.get("category") or "").lower() or q in (m.get("sub_category") or "").lower():
            return 70
        if q in (m.get("model") or "").lower():
            return 50
        return 0

    scored = [(score(m), m) for m in materials]
    best = max((s for s, _ in scored), default=0)
    if best <= 0:
        keep = list(materials)
    elif best >= 90:
        keep = [m for s, m in scored if s >= 60]
    else:
        keep = [m for s, m in scored if s >= max(best - 10, 50)]
    return {"keep_ids": [m["id"] for m in keep], "summary": ""}


def filter_search_results(query: str, materials: list, use_fake: bool = False, keyword: str = "") -> dict:
    """筛选候选物料（对外接口）。

    Args:
        query: 用户原始需求（LLM 用于理解意图）
        materials: search_material_rows 返回的候选行列表
        use_fake: 是否使用离线规则（默认 False，优先尝试真实 LLM）
        keyword: 搜索关键词（离线规则用于子串匹配，默认回退到 query）

    Returns:
        {"keep_ids": [int], "summary": str, "llm_error": str}
    """
    if not materials:
        return {"keep_ids": [], "summary": "", "llm_error": ""}

    fake_q = keyword or query
    llm_error = ""
    try:
        res = filter_materials_fake(fake_q, materials) if use_fake else filter_materials(query, materials)
    except Exception as e:
        llm_error = str(e)
        res = filter_materials_fake(fake_q, materials)

    valid_ids = {m["id"] for m in materials}
    keep_ids = [i for i in res.get("keep_ids", []) if i in valid_ids]

    # LLM 返回的 id 全部无效（幻觉）时回退到全部候选，避免误伤
    if not keep_ids and res.get("keep_ids"):
        keep_ids = [m["id"] for m in materials]

    return {
        "keep_ids": keep_ids,
        "summary": res.get("summary", ""),
        "llm_error": llm_error,
    }
