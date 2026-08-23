# -*- coding: utf-8 -*-
"""归还工具"""

from warehouse_mcp.db.database import get_db


def return_item(borrow_id: str) -> str:
    """归还一个借出的物料。

    Args:
        borrow_id: 借出记录编号
    """
    conn = get_db()
    try:
        # 1. 查找借出记录
        row = conn.execute(
            "SELECT id, material_id, user_phone, status, quantity FROM borrow_records WHERE id = ?",
            (borrow_id,)
        ).fetchone()

        if row is None:
            return f"错误：借出记录 {borrow_id} 不存在。"

        if row["status"] == "returned":
            return f"错误：该物料已经归还过了。"

        # 2. 更新借还记录为已归还
        conn.execute(
            "UPDATE borrow_records SET status = 'returned', returned_at = datetime('now','localtime') WHERE id = ?",
            (borrow_id,)
        )

        # 3. 恢复库存（按借出时的数量）
        conn.execute(
            "UPDATE materials SET quantity = quantity + ? WHERE id = ?",
            (row["quantity"], row["material_id"])
        )

        conn.commit()

        # 获取物料名称
        mat = conn.execute(
            "SELECT name FROM materials WHERE id = ?",
            (row["material_id"],)
        ).fetchone()

        return (
            f"归还成功！\n"
            f"  物料：{mat['name'] if mat else row['material_id']}\n"
            f"  借出人：{row['user_phone']}\n"
            f"  记录编号：{borrow_id}"
        )

    except Exception as e:
        conn.rollback()
        return f"归还失败：{e}"
    finally:
        conn.close()
