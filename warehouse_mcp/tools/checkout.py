# -*- coding: utf-8 -*-
"""出库工具 — 统一入口，mode 区分「借出」和「领用」"""

from warehouse_mcp.db.database import get_db


def checkout(
    material_id: str,
    user_phone: str,
    mode: str,
    quantity: int = 1
) -> str:
    """出库物料。

    Args:
        material_id: 物料编号（如 MC-20260809-0001）
        user_phone: 操作人手机号
        mode: 出库方式，"borrow"（借出，需归还）或 "consume"（领用，不归还）
        quantity: 出库数量（默认 1；非耗材每件独立编号，只能 1 件/条）

    非耗材入库时每件占一行（quantity=1），一次只能出 1 件；
    耗材合并在一行，quantity 为总库存，可一次出多件。
    """
    if mode not in ("borrow", "consume"):
        return "错误：mode 必须是 'borrow'（借出）或 'consume'（领用）。"

    if quantity <= 0:
        return "错误：出库数量必须大于 0。"

    conn = get_db()
    try:
        # 1. 检查物料是否存在、库存是否充足
        row = conn.execute(
            "SELECT id, name, quantity, is_consumable FROM materials WHERE id = ?",
            (material_id,)
        ).fetchone()

        if row is None:
            return f"错误：物料编号 {material_id} 不存在。"

        if row["quantity"] <= 0:
            return f"错误：物料「{row['name']}」库存不足（当前库存：0）。"

        if not row["is_consumable"] and quantity > 1:
            return (
                f"错误：物料「{row['name']}」是非耗材（每件独立编号），"
                f"一次只能出 1 件。如需多件，请逐条出库。"
            )

        if row["quantity"] < quantity:
            return (
                f"错误：物料「{row['name']}」库存不足"
                f"（需 {quantity}，当前库存：{row['quantity']}）。"
            )

        # 2. 确保用户存在
        conn.execute(
            "INSERT OR IGNORE INTO users (phone) VALUES (?)",
            (user_phone,)
        )

        # 3. 条件式扣减库存：WHERE 里再校验一次库存，防止并发下扣成负数
        cursor = conn.execute(
            "UPDATE materials SET quantity = quantity - ? "
            "WHERE id = ? AND quantity >= ?",
            (quantity, material_id, quantity)
        )
        if cursor.rowcount != 1:
            return (
                f"错误：物料「{row['name']}」库存不足"
                f"（需 {quantity}，当前库存：{row['quantity']}）。"
            )

        # 4. 写入出库记录
        conn.execute(
            "INSERT INTO outbound_records (material_id, user_phone, mode, quantity) VALUES (?, ?, ?, ?)",
            (material_id, user_phone, mode, quantity)
        )

        # 5. 借出模式：额外创建借还记录（记录数量，归还时按量恢复）
        if mode == "borrow":
            conn.execute(
                "INSERT INTO borrow_records (material_id, user_phone, quantity) VALUES (?, ?, ?)",
                (material_id, user_phone, quantity)
            )

        conn.commit()

        mode_label = "借出（需归还）" if mode == "borrow" else "领用（永久出库）"
        qty_line = f"\n  数量：{quantity}" if quantity > 1 else ""
        return (
            f"出库成功！\n"
            f"  物料：{row['name']}（{material_id}）\n"
            f"  方式：{mode_label}{qty_line}\n"
            f"  操作人：{user_phone}\n"
            f"  剩余库存：{row['quantity'] - quantity}"
        )

    except Exception as e:
        conn.rollback()
        return f"出库失败：{e}"
    finally:
        conn.close()
