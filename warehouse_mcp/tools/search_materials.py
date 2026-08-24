# -*- coding: utf-8 -*-
"""库存查询工具 — 支持按关键词、类别、标签搜索（条件可自由组合）"""

from warehouse_mcp.db.database import get_db


def search_material_rows(
    keyword: str = "",
    category: str = "",
    tag: str = "",
    only_available: bool = False
) -> list:
    """查询库存物料，返回结构化行列表（不合并、不格式化文本）。

    Args:
        keyword: 按名称/类别/型号/子类/编号模糊搜索（多词空格分隔，OR 匹配）
        category: 按大类精确筛选（如 "主控板"）
        tag: 按标签搜索（匹配标签名或描述，可与 keyword 同时使用）
        only_available: 仅返回有库存的物料

    Returns:
        每行 dict 含 id, name, category, category_code, sub_category,
        sub_category_code, model, is_consumable, quantity, location,
        created_at, tag_list（逗号分隔的标签名）。
    """
    conn = get_db()
    try:
        # 标签检索统一走 JOIN，没传 tag 时 LEFT JOIN 只用来聚合标签展示
        query = """
            SELECT m.id, m.name, m.category, m.category_code,
                   m.sub_category, m.sub_category_code, m.model,
                   m.is_consumable, m.quantity, m.location, m.created_at,
                   GROUP_CONCAT(t.name, ', ') AS tag_list
            FROM materials m
            LEFT JOIN material_tags mt ON m.id = mt.material_id
            LEFT JOIN tags t ON mt.tag_name = t.name
            WHERE 1=1
        """
        params = []

        if keyword:
            # 拆分多关键词，每个词独立 OR 匹配
            terms = [t for t in keyword.split() if t.strip()] or [keyword]
            or_clauses = []
            for term in terms:
                kw = f"%{term}%"
                or_clauses.append(
                    "(m.name LIKE ? OR m.category LIKE ? OR m.model LIKE ?"
                    " OR m.sub_category LIKE ? OR m.id LIKE ?)"
                )
                params.extend([kw, kw, kw, kw, kw])
            query += " AND (" + " OR ".join(or_clauses) + ")"

        if tag:
            # 标签搜索：拆分关键词，每个独立 OR 匹配标签名或描述
            terms = [t for t in tag.split() if t.strip()] or [tag]
            or_clauses = []
            for term in terms:
                kw = f"%{term}%"
                or_clauses.append("(t.name LIKE ? OR t.description LIKE ?)")
                params.extend([kw, kw])
            query += " AND (" + " OR ".join(or_clauses) + ")"

        if category:
            query += " AND m.category = ?"
            params.append(category)

        if only_available:
            query += " AND m.quantity > 0"

        query += " GROUP BY m.id ORDER BY m.category, m.name"

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def search_materials(
    keyword: str = "",
    category: str = "",
    tag: str = "",
    only_available: bool = False
) -> str:
    """查询库存物料（文本输出）。

    Args:
        keyword: 按名称/类别/型号/子类/编号模糊搜索（多词空格分隔，OR 匹配）
        category: 按大类精确筛选（如 "主控板"）
        tag: 按标签搜索（匹配标签名或描述，可与 keyword 同时使用）
        only_available: 仅显示有库存的物料
    """
    rows = search_material_rows(
        keyword=keyword, category=category, tag=tag, only_available=only_available
    )

    if not rows:
        return "没有找到匹配的物料。"

    # 非耗材同名（+同型号+同分类）合并为一条、库存求和、不显示个体编号；
    # 耗材本身即合并存储，保持独立条目。
    non_cons = {}   # (name, category, sub_category, model) -> 合并信息
    cons = []       # 耗材行

    for r in rows:
        if r["is_consumable"]:
            cons.append(r)
        else:
            key = (r["name"], r["category"], r["sub_category"], r["model"])
            if key not in non_cons:
                non_cons[key] = {
                    "name": r["name"], "category": r["category"],
                    "sub_category": r["sub_category"], "model": r["model"],
                    "quantity": 0, "location": r["location"] or "",
                    "tags": set(),
                }
            non_cons[key]["quantity"] += r["quantity"]
            if r["location"]:
                non_cons[key]["location"] = r["location"]
            if r["tag_list"]:
                non_cons[key]["tags"].update(r["tag_list"].split(", "))

    # 统一按大类、名称排序输出
    entries = []
    for key, d in non_cons.items():
        entries.append((d["category"], d["name"], 0, key))
    for r in cons:
        entries.append((r["category"], r["name"], 1, r))
    entries.sort(key=lambda e: (e[0], e[1], e[2]))

    lines = []
    for _, _, kind, obj in entries:
        if kind == 0:
            d = non_cons[obj]
            model_str = f" | 型号：{d['model']}" if d["model"] else ""
            loc = f" | 位置：{d['location']}" if d["location"] else ""
            tags_str = f" | 标签：{', '.join(sorted(d['tags']))}" if d["tags"] else ""
            lines.append(
                f"{d['name']} | {d['category']} > {d['sub_category']}"
                f"{model_str} | 非耗材 | 库存：{d['quantity']}{loc}{tags_str}"
            )
        else:
            r = obj
            model_str = f" | 型号：{r['model']}" if r["model"] else ""
            loc = f" | 位置：{r['location']}" if r["location"] else ""
            tags_str = f" | 标签：{r['tag_list']}" if r["tag_list"] else ""
            lines.append(
                f"[{r['id']}] {r['name']} | {r['category']} > {r['sub_category']}"
                f"{model_str} | 耗材 | 库存：{r['quantity']}{loc}{tags_str}"
            )

    return f"共 {len(lines)} 条结果：\n" + "\n".join(lines)
