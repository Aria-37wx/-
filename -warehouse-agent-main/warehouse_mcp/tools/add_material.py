# -*- coding: utf-8 -*-
"""入库工具"""

from datetime import datetime
from warehouse_mcp.db.database import (get_db, generate_id, CATEGORIES,
                                        get_sub_code, get_category_subs)


def add_material(
    name: str,
    category: str,
    sub_category: str = "",
    model: str = "",
    is_consumable: bool = False,
    quantity: int = 1,
    location: str = "",
    tags: list = None
) -> str:
    """入库物料。

    Args:
        name: 物料名称
        category: 大类（如 "执行/驱动"）
        sub_category: 子类（如 "直流电机"）
        model: 型号
        is_consumable: 是否耗材
        quantity: 数量（非耗材每件独立编号，耗材合并）
        location: 存放位置
        tags: 标签列表

    ID 格式：{大类码}-{子类码}-{YYYYMMDD}-{NNNN}，如 AC-DCM-20260809-0001
    """
    if quantity <= 0:
        return "错误：入库数量必须大于 0。"

    if category not in CATEGORIES:
        valid = "、".join(CATEGORIES.keys())
        return f"错误：无效的大类「{category}」。有效大类：{valid}"

    cat_info = CATEGORIES[category]
    category_code = cat_info["code"]

    # 验证子类
    valid_subs = get_category_subs(category)
    if sub_category and sub_category not in valid_subs:
        return f"错误：无效的子类「{sub_category}」。有效子类：{'、'.join(valid_subs)}"

    sub_category_code = get_sub_code(category, sub_category) if sub_category else "OTH"

    if tags is None:
        tags = []

    conn = get_db()
    try:
        if is_consumable:
            material_id = generate_id(conn, category_code, sub_category_code)
            conn.execute(
                """INSERT INTO materials (id, name, category, category_code,
                   sub_category, sub_category_code, model, is_consumable, quantity, location)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
                (material_id, name, category, category_code, sub_category,
                 sub_category_code, model, quantity, location)
            )
            ids = [material_id]
        else:
            ids = []
            date_str = datetime.now().strftime("%Y%m%d")
            prefix = f"{category_code}-{sub_category_code}-{date_str}-"
            row = conn.execute(
                "SELECT MAX(CAST(SUBSTR(id, LENGTH(?) + 1) AS INTEGER)) FROM materials WHERE id LIKE ?",
                (prefix, f"{prefix}%")
            ).fetchone()
            base_seq = (row[0] or 0) + 1

            for i in range(quantity):
                material_id = f"{prefix}{base_seq + i:04d}"
                conn.execute(
                    """INSERT INTO materials (id, name, category, category_code,
                       sub_category, sub_category_code, model, is_consumable, quantity, location)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 0, 1, ?)""",
                    (material_id, name, category, category_code, sub_category,
                     sub_category_code, model, location)
                )
                ids.append(material_id)

        # 关联标签
        for tag in tags:
            if tag.strip():
                for mid in ids:
                    conn.execute(
                        "INSERT OR IGNORE INTO material_tags (material_id, tag_name) VALUES (?, ?)",
                        (mid, tag.strip())
                    )

        conn.commit()

        id_summary = ", ".join(ids) if len(ids) <= 5 else f"{ids[0]} ~ {ids[-1]}（共{len(ids)}件）"
        tag_str = f"\n  标签：{', '.join(tags)}" if tags else ""
        return (
            f"入库成功！\n"
            f"  编号：{id_summary}\n"
            f"  名称：{name}\n"
            f"  分类：{category} > {sub_category}\n"
            f"  数量：{quantity}\n"
            f"  类型：{'耗材' if is_consumable else '非耗材（每件独立编号）'}\n"
            f"  位置：{location or '未指定'}{tag_str}"
        )
    except Exception as e:
        conn.rollback()
        return f"入库失败：{e}"
    finally:
        conn.close()
