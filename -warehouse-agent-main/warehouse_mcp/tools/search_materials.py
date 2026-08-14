# -*- coding: utf-8 -*-
"""库存查询工具 — 支持按关键词、类别、标签搜索"""

from warehouse_mcp.db.database import get_db


def search_materials(
    keyword: str = "",
    category: str = "",
    tag: str = "",
    only_available: bool = False
) -> str:
    """查询库存物料。

    Args:
        keyword: 按名称/类别/型号/子类模糊搜索
        category: 按大类精确筛选（如 "主控板"）
        tag: 按标签搜索（匹配标签名或描述）
        only_available: 仅显示有库存的物料
    """
    conn = get_db()
    try:
        if tag:
            # 标签搜索：拆分关键词，每个独立 OR 匹配
            terms = [t for t in tag.split() if t.strip()]
            if not terms:
                terms = [tag]
            or_clauses = []
            params = []
            for term in terms:
                kw = f"%{term}%"
                or_clauses.append("(t.name LIKE ? OR t.description LIKE ?)")
                params.extend([kw, kw])
            query = f"""
                SELECT DISTINCT m.*, GROUP_CONCAT(t.name, ', ') as tag_list
                FROM materials m
                JOIN material_tags mt ON m.id = mt.material_id
                JOIN tags t ON mt.tag_name = t.name
                WHERE ({" OR ".join(or_clauses)})
            """
            group_suffix = " GROUP BY m.id"
        else:
            query = "SELECT id, name, category, category_code, sub_category, sub_category_code, model, is_consumable, quantity, location, created_at FROM materials WHERE 1=1"
            params = []

            if keyword:
                # 拆分多关键词，每个词独立 OR 匹配
                terms = [t for t in keyword.split() if t.strip()]
                if not terms:
                    terms = [keyword]
                or_clauses = []
                for term in terms:
                    kw = f"%{term}%"
                    or_clauses.append(
                        "(name LIKE ? OR category LIKE ? OR model LIKE ? OR sub_category LIKE ? OR id LIKE ?)"
                    )
                    params.extend([kw, kw, kw, kw, kw])
                query += " AND (" + " OR ".join(or_clauses) + ")"

            group_suffix = ""

        if category:
            query += " AND category = ?"
            params.append(category)

        if only_available:
            query += " AND quantity > 0"

        query += group_suffix + " ORDER BY category, name"

        rows = conn.execute(query, params).fetchall()

        if not rows:
            return "没有找到匹配的物料。"

        lines = []
        for r in rows:
            type_label = "耗材" if r["is_consumable"] else "非耗材"
            loc = f" | 位置：{r['location']}" if r["location"] else ""
            model_str = f" | 型号：{r['model']}" if r["model"] else ""
            tags_str = f" | 标签：{r['tag_list']}" if "tag_list" in r.keys() else ""
            lines.append(
                f"[{r['id']}] {r['name']} | {r['category']} > {r['sub_category']}"
                f"{model_str} | {type_label} | 库存：{r['quantity']}{loc}{tags_str}"
            )

        return f"共 {len(rows)} 条结果：\n" + "\n".join(lines)

    finally:
        conn.close()
