# -*- coding: utf-8 -*-
"""借还记录查询工具"""

from warehouse_mcp.db.database import get_db


def get_borrow_records(
    user_phone: str = "",
    material_id: str = "",
    only_active: bool = False
) -> str:
    """查询借还记录。

    Args:
        user_phone: 按用户手机号筛选（可选）
        material_id: 按物料编号筛选（可选）
        only_active: 仅显示未归还的记录（默认 False）
    """
    conn = get_db()
    try:
        query = """
            SELECT br.id, br.material_id, m.name AS material_name,
                   br.user_phone, br.borrowed_at, br.returned_at, br.status
            FROM borrow_records br
            LEFT JOIN materials m ON br.material_id = m.id
            WHERE 1=1
        """
        params = []

        if user_phone:
            query += " AND br.user_phone = ?"
            params.append(user_phone)

        if material_id:
            query += " AND br.material_id = ?"
            params.append(material_id)

        if only_active:
            query += " AND br.status = 'active'"

        query += " ORDER BY br.borrowed_at DESC"

        rows = conn.execute(query, params).fetchall()

        if not rows:
            return "没有找到匹配的借还记录。"

        lines = []
        for r in rows:
            status_label = "借出中" if r["status"] == "active" else "已归还"
            returned = f" | 归还时间：{r['returned_at']}" if r["returned_at"] else ""
            lines.append(
                f"[{r['id']}] {r['material_name'] or r['material_id']} "
                f"| 借出人：{r['user_phone']} "
                f"| 借出：{r['borrowed_at']} "
                f"| 状态：{status_label}{returned}"
            )

        return f"共 {len(rows)} 条记录：\n" + "\n".join(lines)

    finally:
        conn.close()
