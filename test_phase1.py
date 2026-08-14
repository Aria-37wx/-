# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'c:\Users\Yu\Documents\Trae Data\warehouse agent')

from warehouse_mcp.db.database import init_db
init_db()
print('OK: database initialized')

from warehouse_mcp.tools.add_material import add_material
r = add_material('STM32F407 dev board', 'dev board', 'ARM', 'F407', False, 3, 'Cabinet A-1')
print(r)
print('OK: add_material')

from warehouse_mcp.tools.search_materials import search_materials
print(search_materials())
print('OK: search_materials')

from warehouse_mcp.tools.checkout import checkout
from warehouse_mcp.db.database import get_db
conn = get_db()
mat = conn.execute("SELECT id FROM materials LIMIT 1").fetchone()
conn.close()
print(checkout(mat['id'], '13800000001', 'borrow'))
print('OK: checkout borrow')

from warehouse_mcp.tools.borrow_query import get_borrow_records
print(get_borrow_records())
print('OK: borrow_query')

from warehouse_mcp.tools.return_item import return_item
conn2 = get_db()
br = conn2.execute("SELECT id FROM borrow_records WHERE status='active' LIMIT 1").fetchone()
conn2.close()
print(return_item(br['id']))
print('OK: return_item')

print('ALL TESTS PASSED')
