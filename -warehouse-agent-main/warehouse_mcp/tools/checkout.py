# -*- coding: utf-8 -*-
"""出库工具 — 统一入口，mode 区分「借出」和「领用」"""

from warehouse_mcp.db.database import get_db


def checkout(
    material_id: str,
    user_phone: str,
    mode: str
) -> str:
    """出库一个物料。

    Args:
        material_id: 物料编号（如 MC-20260809-0001）
        user_phone: 操作人手机号
        mode: 出库方式，"borrow"（借出，需归还）或 "consume"（领用，不归还）
    """
    if mode not in ("borrow", "consume"):
        return "错误：mode 必须是 'borrow'（借出）或 'consume'（领用）。"

    conn = get_db()
    try:
        # 1. 检查物料是否存在、库存是否充足
        row = conn.execute(
            "SELECT id, name, quantity FROM materials WHERE id = ?",
            (material_id,)
        ).fetchone()

        if row is None:
            return f"错误：物料编号 {material_id} 不存在。"

        if row["quantity"] <= 0:
            return f"错误：物料「{row['name']}」库存不足（当前库存：0）。"

        # 2. 确保用户存在
        conn.execute(
            "INSERT OR IGNORE INTO users (phone) VALUES (?)",
            (user_phone,)
        )

        # 3. 扣减库存
        conn.execute(
            "UPDATE materials SET quantity = quantity - 1 WHERE id = ?",
            (material_id,)
        )

        # 4. 写入出库记录
        cursor = conn.execute(
            "INSERT INTO outbound_records (material_id, user_phone, mode) VALUES (?, ?, ?)",
            (material_id, user_phone, mode)
        )

        # 5. 借出模式：额外创建借还记录
        if mode == "borrow":
            conn.execute(
                "INSERT INTO borrow_records (material_id, user_phone) VALUES (?, ?)",
                (material_id, user_phone)
            )

        conn.commit()

        mode_label = "借出（需归还）" if mode == "borrow" else "领用（永久出库）"
        return (
            f"出库成功！\n"
            f"  物料：{row['name']}（{material_id}）\n"
            f"  方式：{mode_label}\n"
            f"  操作人：{user_phone}\n"
            f"  剩余库存：{row['quantity'] - 1}"
        )

    except Exception as e:
        conn.rollback()
        return f"出库失败：{e}"
    finally:
        conn.close()
