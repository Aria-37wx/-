# -*- coding: utf-8 -*-
"""物料管理 MCP Server 入口"""

from mcp.server.fastmcp import FastMCP

from warehouse_mcp.db.database import init_db
from warehouse_mcp.tools.add_material import add_material
from warehouse_mcp.tools.checkout import checkout
from warehouse_mcp.tools.return_item import return_item
from warehouse_mcp.tools.search_materials import search_materials
from warehouse_mcp.tools.borrow_query import get_borrow_records
from warehouse_mcp.tools.smart_add_material import smart_add_material, infer_material_info

# 创建 MCP Server
mcp = FastMCP("warehouse")

# 注册所有工具
mcp.tool()(add_material)
mcp.tool()(checkout)
mcp.tool()(return_item)
mcp.tool()(search_materials)
mcp.tool()(get_borrow_records)
mcp.tool()(smart_add_material)
mcp.tool()(infer_material_info)


def main():
    """启动 MCP Server"""
    init_db()  # 启动时自动建表
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
