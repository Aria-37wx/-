# 物料管理智能体

大学生科创实验室物料管理系统。基于 **FastMCP + SQLite + Streamlit**，支持 Web 界面操作和 MCP 协议调用。AI 自然语言对话可实现入库、出库、查询。

> 选题 4 参赛作品 | 团队协作开发

---

## 快速开始

### 环境

- Python 3.12+（推荐 Anaconda）
- 依赖：`mcp`（1.x，含 FastMCP）、`streamlit`、`openai`

```powershell
pip install -r requirements.txt
# 或手动安装：
# pip install "mcp>=1.0,<2" streamlit openai
```

> 注意：必须装 `mcp` 1.x（`pip install fastmcp` 装的是 2.x，`mcp.server.fastmcp` 已拆出，不兼容本项目）。

### 启动 Web 服务

```powershell
# 仓库已内置测试数据（data/warehouse.db），无需初始化，直接启动

# 1. （可选）如需重置为演示测试数据，运行
python setup_test_data.py

# 2. 启动 Web 界面
streamlit run warehouse_mcp/web/app.py --server.port 8501
```

浏览器打开 http://localhost:8501

### 启动 MCP Server（供 AI 客户端调用）

```powershell
python -m warehouse_mcp.server
```

配置到 MCP 客户端（如 Cursor、Trae）：

```json
{
  "mcpServers": {
    "warehouse": {
      "command": "python",
      "args": ["-m", "warehouse_mcp.server"]
    }
  }
}
```

---

## 页面功能

| 页面 | 功能 |
|------|------|
| 库存总览 | 关键词/类别/标签搜索浏览 |
| **AI 对话** | 自然语言操作，AI 自动判断意图：入库、出库、查询、归还、**项目推荐**（物料清单 + 缺料预警 + 批量出库） |
| 入库 | 手动填写表单入库 / 智能入库（AI 推断分类） |
| 出库 | 选择物料 → 借出或领用（耗材可一次出多件） |
| 归还 | 归还借出中的物料（显示借出数量） |
| 记录查询 | 借还记录 / 领用记录查询 |
| 标签管理 | 浏览和编辑标签库 |

---

## AI 对话示例

```
用户: "入库 5 块 ESP32 开发板"
  → AI 自动推断分类、子类、位置 → 确认 → 入库

用户: "我想借两块能跑 MicroPython 的开发板"
  → 关键词召回 + AI 语义筛选 → 列出匹配物料（同名非耗材合并显示） → 批量勾选 + 设置数量 → 确认出库

用户: "有没有低功耗无线通信模块"
  → 关键词召回 + AI 语义筛选 → 直接展示匹配的 WiFi/蓝牙/LoRa 模块
```

> AI 对话在判定意图后直接进入执行步骤展示结果（不再需要点击确认意图），仅在真正写库前做最终确认；
> 查询/出库采用「召回 → 语义筛选」两段式，剔除名字含关键词但品类不符的干扰项（如搜"电阻"不误返回"光敏电阻传感器"）。

---

## 项目结构

```
warehouse agent/
├── warehouse_mcp/              # 主包
│   ├── server.py               # MCP 入口
│   ├── llm_client.py           # LLM 调用 + 离线规则（Skill 层）
│   ├── db/                     # 数据库层（基础设施）
│   ├── tools/                  # MCP Tool 实现
│   │   ├── intent_router.py    # 意图分类（Skill 层）
│   │   ├── smart_add_material.py
│   │   ├── add_material.py     # 基础入库
│   │   ├── checkout.py         # 出库
│   │   ├── return_item.py      # 归还
│   │   ├── search_materials.py # 库存搜索（含结构化 search_material_rows）
│   │   ├── search_filter.py    # 搜索语义过滤（召回后按意图筛选）
│   │   └── borrow_query.py     # 借还查询
│   └── web/
│       └── app.py              # Streamlit Web 界面
├── setup_test_data.py          # 测试数据填充脚本
├── DB_DESIGN.md                # 数据库设计文档
├── DEV_GUIDE.md                # 开发者指南
├── TEAM_GUIDE.md               # 团队合作指南
└── data/                       # SQLite 数据库（已提交测试数据，clone 后可直接使用）
```

---

## 团队协作

请先阅读 [TEAM_GUIDE.md](TEAM_GUIDE.md)，了解：

- 哪些代码可以改（Skill 层）
- 哪些不能动（基础设施层）
- 开发方向和任务优先级

---

## LLM API 配置

在 Web 界面「AI 对话」→「高级设置」中输入 DeepSeek 等 OpenAI 兼容 API Key。

Key 保存到 `data/llm_config.json`，**该文件已在 .gitignore 中，不会被提交**。

未配置 Key 时自动使用离线规则模式（内置关键词匹配）。

---

## 技术栈

- **后端**: FastMCP (Python)
- **数据库**: SQLite
- **前端**: Streamlit
- **AI**: OpenAI 兼容 API（DeepSeek / 通义千问等）
- **协议**: MCP (Model Context Protocol)
