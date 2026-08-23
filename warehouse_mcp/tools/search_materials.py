# -*- coding: utf-8 -*-
"""库存查询工具 — 支持按关键词、类别、标签搜索（条件可自由组合）"""

from warehouse_mcp.db.database import get_db


def search_materials(
    keyword: str = "",
    category: str = "",
    tag: str = "",
    only_available: bool = False
) -> str:
    """查询库存物料。

    Args:
        keyword: 按名称/类别/型号/子类/编号模糊搜索（多词空格分隔，OR 匹配）
        category: 按大类精确筛选（如 "主控板"）
        tag: 按标签搜索（匹配标签名或描述，可与 keyword 同时使用）
        only_available: 仅显示有库存的物料
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

        if not rows:
            return "没有找到匹配的物料。"

        lines = []
        for r in rows:
            type_label = "耗材" if r["is_consumable"] else "非耗材"
            loc = f" | 位置：{r['location']}" if r["location"] else ""
            model_str = f" | 型号：{r['model']}" if r["model"] else ""
            tags_str = f" | 标签：{r['tag_list']}" if r["tag_list"] else ""
            lines.append(
                f"[{r['id']}] {r['name']} | {r['category']} > {r['sub_category']}"
                f"{model_str} | {type_label} | 库存：{r['quantity']}{loc}{tags_str}"
            )

        return f"共 {len(rows)} 条结果：\n" + "\n".join(lines)

    finally:
        conn.close()
