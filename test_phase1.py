# -*- coding: utf-8 -*-
"""Phase 1 冒烟测试：入库 / 查询 / 出库 / 借还，全部走真断言（失败即抛异常）。

运行方式（项目根目录）：
    python test_phase1.py

注意：测试使用独立的临时数据库，不会污染 data/warehouse.db。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 必须在 import 任何 warehouse_mcp 模块之前把数据库指向临时文件
from warehouse_mcp.db import database
_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   f"data", f"test_tmp_{int(time.time())}.db")
database.DB_PATH = _DB

from warehouse_mcp.db.database import init_db, get_db  # noqa: E402
from warehouse_mcp.tools.add_material import add_material  # noqa: E402
from warehouse_mcp.tools.search_materials import search_materials  # noqa: E402
from warehouse_mcp.tools.checkout import checkout  # noqa: E402
from warehouse_mcp.tools.borrow_query import get_borrow_records  # noqa: E402
from warehouse_mcp.tools.return_item import return_item  # noqa: E402


def q(sql, *params):
    """快捷查询：返回全部行"""
    conn = get_db()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def q1(sql, *params):
    """快捷查询：返回第一行"""
    rows = q(sql, *params)
    return rows[0] if rows else None


def qv(sql, *params):
    """快捷查询：返回第一个标量值"""
    row = q1(sql, *params)
    return list(row)[0] if row else None


def main():
    init_db()
    print("OK: database initialized (临时库)")

    # ---- 入库 ----
    r = add_material("ESP32开发板", "主控板", "MCU/单片机", model="ESP32-WROOM-32",
                     quantity=3, location="柜A-1", tags=["ESP32", "IoT开发"])
    assert "入库成功" in r, f"非耗材入库失败: {r}"
    print("OK: add_material（非耗材，每件独立编号）")

    r = add_material("无铅焊锡丝", "耗材", "焊料/助焊剂", is_consumable=True,
                     quantity=5, location="柜F", tags=["焊锡丝"])
    assert "入库成功" in r, f"耗材入库失败: {r}"
    print("OK: add_material（耗材，合并数量）")

    # 非耗材 3 件 → 3 行各 1 件；耗材 1 行 5 件
    assert qv("SELECT COUNT(*) FROM materials WHERE name='ESP32开发板'") == 3
    assert qv("SELECT quantity FROM materials WHERE name='无铅焊锡丝'") == 5
    esp_id = qv("SELECT id FROM materials WHERE name='ESP32开发板' LIMIT 1")
    solder_id = qv("SELECT id FROM materials WHERE name='无铅焊锡丝'")

    # ---- 查询 ----
    assert "ESP32开发板" in search_materials(keyword="ESP32"), "关键词查询失败"
    assert "没有找到" in search_materials(keyword="不存在的物料XYZ")
    assert "ESP32开发板" in search_materials(tag="ESP32"), "标签查询失败"
    assert "没有找到" in search_materials(keyword="焊锡", tag="ESP32"), \
        "keyword 与 tag 应同时生效（交集），互不匹配时不应有结果"
    assert "ESP32开发板" in search_materials(keyword="开发板", tag="ESP32"), \
        "keyword 与 tag 同时命中时应返回结果"
    print("OK: search_materials（keyword / tag / 组合）")

    # ---- 出库 ----
    phone = "13800000001"

    # 耗材一次出 2 件
    r = checkout(solder_id, phone, "consume", quantity=2)
    assert "出库成功" in r, f"耗材批量出库失败: {r}"
    assert qv("SELECT quantity FROM materials WHERE id=?", solder_id) == 3
    assert qv("SELECT quantity FROM outbound_records WHERE material_id=? ORDER BY id DESC LIMIT 1",
              solder_id) == 2, "outbound_records 应记录出库数量"
    print("OK: checkout（耗材批量出库 2 件）")

    # 非耗材一次只能出 1 件
    r = checkout(esp_id, phone, "borrow", quantity=2)
    assert "错误" in r, f"非耗材批量出库应被拒绝，实际: {r}"
    print("OK: checkout（非耗材拒绝批量出库）")

    # 借出 1 件
    r = checkout(esp_id, phone, "borrow")
    assert "出库成功" in r, f"借出失败: {r}"
    assert qv("SELECT SUM(quantity) FROM materials WHERE name='ESP32开发板'") == 2
    print("OK: checkout（借出 1 件）")

    # ---- 借还记录与归还 ----
    assert "借出中" in get_borrow_records(user_phone=phone, only_active=True)
    assert "数量：1 件" in get_borrow_records(user_phone=phone, only_active=True), \
        "借还记录输出应显示借出数量"
    br_id = qv("SELECT id FROM borrow_records WHERE user_phone=? AND status='active'", phone)
    assert br_id is not None, "应有 1 条借出中记录"

    r = return_item(str(br_id))
    assert "归还成功" in r, f"归还失败: {r}"
    assert qv("SELECT SUM(quantity) FROM materials WHERE name='ESP32开发板'") == 3, \
        "归还后库存应恢复"
    assert qv("SELECT status FROM borrow_records WHERE id=?", br_id) == "returned"
    print("OK: return_item（归还后库存恢复）")

    # ---- 库存不足拒绝 ----
    r = checkout(solder_id, phone, "consume", quantity=99)
    assert "错误" in r and "库存不足" in r, f"超量出库应被拒绝，实际: {r}"
    assert qv("SELECT quantity FROM materials WHERE id=?", solder_id) == 3, \
        "失败出库不应扣库存"
    print("OK: checkout（库存不足拒绝，不扣库存）")

    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    finally:
        # 清理临时数据库
        for suffix in ("", "-journal", "-wal", "-shm"):
            p = _DB + suffix
            if os.path.exists(p):
                os.remove(p)
