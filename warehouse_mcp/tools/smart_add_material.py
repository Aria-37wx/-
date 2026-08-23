# -*- coding: utf-8 -*-
"""智能入库工具 — LLM 自动推断分类+标签"""

from warehouse_mcp.db.database import get_db, CATEGORIES, get_category_subs, get_recommended_location
from warehouse_mcp.tools.add_material import add_material
from warehouse_mcp.llm_client import infer_material, infer_material_fake


def infer_material_info(
    name: str,
    description: str = "",
    use_fake: bool = False
) -> dict:
    """推断物料信息（不插入数据库，供前端确认用）。

    Returns:
        dict: {
            "success": True/False,
            "error": "错误信息"（仅失败时）,
            "name": "物料名",
            "category": "大类",
            "sub_category": "子类",
            "model": "型号",
            "is_consumable": False,
            "location": "推荐位置",
            "tags": [...],
            "valid_subs": [...]  # 该大类下所有有效子类（供前端下拉框用）
        }
    """
    if not name.strip():
        return {"success": False, "error": "物料名称不能为空。"}

    # 1. 调用 LLM（或离线规则）推断
    try:
        if use_fake:
            inferred = infer_material_fake(name, description)
        else:
            inferred = infer_material(name, description)
    except Exception:
        # 未配 Key（RuntimeError）或 API 报错（网络/401/超时等）都降级到离线规则
        inferred = infer_material_fake(name, description)

    category = inferred.get("category", "")
    sub_category = inferred.get("sub_category", "")
    model = inferred.get("model", "")
    is_consumable = inferred.get("is_consumable", False)
    tags = inferred.get("tags", [])

    # 2. 校验
    if not category:
        return {"success": False, "error": f"无法推断「{name}」的大类和子类，请尝试手动入库或添加更详细的描述。"}

    if category not in CATEGORIES:
        return {"success": False, "error": f"推断的大类「{category}」不在分类体系中。"}

    valid_subs = get_category_subs(category)
    if sub_category not in valid_subs:
        return {"success": False, "error": f"推断的子类「{sub_category}」不在「{category}」的子类列表中。"}

    # 3. 自动分配位置
    location = get_recommended_location(category)

    return {
        "success": True,
        "name": name.strip(),
        "category": category,
        "sub_category": sub_category,
        "model": model,
        "is_consumable": is_consumable,
        "location": location,
        "tags": tags,
        "valid_subs": valid_subs,
    }


def smart_add_material(
    name: str,
    description: str = "",
    quantity: int = 1,
    use_fake: bool = False
) -> str:
    """智能入库：仅输入物料名称，LLM 自动推断类别/子类/标签/位置。

    Args:
        name: 物料名称，如 "STM32F407 开发板"
        description: 补充描述（可选），如 "带编码器的减速电机，搞小车用的"
        quantity: 入库数量
        use_fake: 是否使用离线规则推断（默认 False，优先尝试真实 LLM）

    流程：LLM推断 → 校验必填字段 → 自动分配位置 → 关联标签 → 调用 add_material
    """
    if not name.strip():
        return "错误：物料名称不能为空。"
    if quantity <= 0:
        return "错误：入库数量必须大于 0。"

    # 1. 调用 LLM（或离线规则）推断
    try:
        if use_fake:
            inferred = infer_material_fake(name, description)
        else:
            inferred = infer_material(name, description)
    except RuntimeError:
        # LLM 未配置，降级到离线规则
        inferred = infer_material_fake(name, description)

    category = inferred.get("category", "")
    sub_category = inferred.get("sub_category", "")
    model = inferred.get("model", "")
    is_consumable = inferred.get("is_consumable", False)
    tags = inferred.get("tags", [])

    # 2. 校验必填字段：category 和 sub_category 不能为空
    issues = []
    if not category:
        issues.append("大类无法推断")
    else:
        if category not in CATEGORIES:
            issues.append(f"推断的大类「{category}」不在分类体系中")
        else:
            valid_subs = get_category_subs(category)
            if sub_category not in valid_subs:
                issues.append(f"推断的子类「{sub_category}」不在「{category}」的子类列表中")

    if issues:
        return (
            f"智能入库失败：{'; '.join(issues)}。\n"
            f"  名称：{name}\n"
            f"  推断结果：category={category}, sub_category={sub_category}\n"
            f"  请使用手动入库或提供更详细的描述。"
        )

    # 3. 自动分配位置
    location = get_recommended_location(category)

    # 4. 预处理标签：确保新标签在 tags 表中存在
    conn = get_db()
    try:
        for tag in tags:
            if tag.strip():
                conn.execute("INSERT OR IGNORE INTO tags (name, description) VALUES (?, '')",
                             (tag.strip(),))
        conn.commit()
    finally:
        conn.close()

    # 5. 调用基础入库
    return add_material(
        name=name.strip(),
        category=category,
        sub_category=sub_category,
        model=model,
        is_consumable=is_consumable,
        quantity=quantity,
        location=location,
        tags=tags
    )
