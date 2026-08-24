# 物料管理智能体 — 开发者指南

> 面向开发者（AI Agent / 后续接手者）。包含项目架构、搭建步骤、编码规范。
> 业务需求请参见 `选题4-物料管理智能体-方案文档.md`。

---

## 1. 环境配置

### Python 虚拟环境（Conda）

**已就绪**，位于 `C:\Anaconda\envs\py312`（Python 3.12.13）。

```powershell
# Python 解释器路径
C:\Anaconda\envs\py312\python.exe

# 安装依赖
& "C:\Anaconda\envs\py312\python.exe" -m pip install fastmcp

# Phase 2/3 再加：openai / httpx 等 LLM 调用库
```

### UTF-8 编码（重要！）

Windows 默认编码是 GBK，而 Python 源文件含中文注释/文档字符串时必须用 UTF-8。
本项目所有 `.py` 文件：
1. 首行必须 `# -*- coding: utf-8 -*-`
2. 文件本身必须是 UTF-8 编码（无 BOM）

**如果遇到 `SyntaxError: (unicode error) 'utf-8' codec can't decode byte...`**，
说明文件被错误存为了 GBK。修复方法：

```powershell
& "C:\Anaconda\envs\py312\python.exe" -c "
import os, glob
base = r'c:\Users\Yu\Documents\Trae Data\warehouse agent\warehouse_mcp'
for f in glob.glob(os.path.join(base, '**', '*.py'), recursive=True):
    try:
        with open(f, 'r', encoding='gbk') as fh:
            content = fh.read()
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(content)
    except:
        pass
"
```
```python
# -*- coding: utf-8 -*-
```

或者在 VS Code 中设置 `"files.encoding": "utf8"`。

### PowerShell 执行策略问题

如果遇到 `无法加载...因为在此系统上禁止运行脚本`，先执行：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 2. 为什么不能照抄 weather.py

> 注：`weather.py` 是 MCP 官方教学示例，现已从仓库移除（与项目无关）。本节保留作为架构对比的讲解。

`weather.py` 是教学演示，只有一个文件、两个 tool。我们的项目复杂得多：

| 维度 | weather.py | 本系统 |
|------|-----------|--------|
| Tool 数量 | 2 个 | Phase 1 就有 5 个，最终 7 个 |
| 数据存储 | 无（纯 API 中转） | SQLite，4 张表 |
| 业务逻辑 | 无 | 入库/出库/借还/查询，有状态流转 |
| 代码量 | 100 行 | 预计 500-1000+ 行 |

**直接在一个文件里堆所有 tool + 所有数据库操作 = 不可维护。**

### 我们需要分层架构

```
weather.py 的模式：          我们的模式：
┌──────────────┐           ┌─────────────────────┐
│  main.py     │           │  server.py           │  ← MCP 入口，注册 tool
│  所有东西     │           │  tools/              │  ← 每个 tool 一个文件
│  混在一起     │           │   ├── add_material.py│
└──────────────┘           │   ├── checkout.py    │
                           │   ├── return_item.py │
                           │   ├── search.py      │
                           │   └── borrow_query.py│
                           │  db/                 │  ← 数据库层
                           │   ├── database.py    │
                           │   └── models.py      │
                           │  web/                │  ← 前端界面（Phase 1 后期加）
                           │   └── app.py         │
                           └─────────────────────┘
```

---

## 3. 项目目录结构

```
warehouse agent/
├── warehouse_mcp/                  # 主包
│   ├── __init__.py
│   ├── server.py                   # FastMCP 入口，注册所有 tool
│   │
│   ├── db/                         # 数据库层
│   │   ├── __init__.py
│   │   ├── database.py             # SQLite 连接管理、建表、迁移
│   │   └── models.py               # 数据类 / 表结构定义
│   │
│   ├── tools/                      # MCP Tool 实现（每个 tool 一个文件）
│   │   ├── __init__.py
│   │   ├── add_material.py         # 入库
│   │   ├── checkout.py             # 出库（借出/领用统一入口）
│   │   ├── return_item.py          # 归还
│   │   ├── search_materials.py     # 库存查询
│   │   ├── borrow_query.py         # 借还记录查询
│   │   ├── smart_add_material.py   # 智能入库（LLM 推理+校验+位置分配）
│   │   ├── search_filter.py        # 搜索语义过滤（召回后按意图筛选）
│   │   └── intent_router.py        # 意图路由（LLM 自然语言分析，分类+提取参数）
│   │
│   ├── llm_client.py               # LLM 推理客户端（OpenAI 兼容 + API Key 持久化）
│   └── web/                        # Web 前端（Streamlit）
│       ├── __init__.py
│       └── app.py                  # Streamlit 界面（7 页面，AI 对话为核心）
│
├── data/                           # SQLite 数据库文件存放
│   └── warehouse.db                # 已提交测试数据（clone 后可直接使用）
│
├── 选题4-物料管理智能体-方案文档.md   # 用户面向的业务文档
├── DEV_GUIDE.md                    # 本文件
└── requirements.txt
```

---

## 4. 核心架构

```
┌──────────────────────────────────────────────────────────┐
│                    用户交互层                              │
│  ┌─────────────┐  ┌──────────────────┐                   │
│  │ Web UI      │  │ LLM 客户端        │                   │
│  │ (Gradio/HTML)│  │ (Claude/Cursor等) │                   │
│  └──────┬──────┘  └────────┬─────────┘                   │
│         │                  │                              │
│         │    MCP Protocol (stdio)                         │
│         └────────┬─────────┘                              │
│                  ▼                                         │
│  ┌──────────────────────────────────────┐                │
│  │         MCP Server (server.py)        │                │
│  │                                       │                │
│  │  FastMCP("warehouse")                 │                │
│  │                                       │                │
│  │  @mcp.tool() ──┐                     │                │
│  │  @mcp.tool() ──┼── tools/*.py        │                │
│  │  @mcp.tool() ──┘                     │                │
│  └──────────────┬───────────────────────┘                │
│                 │                                          │
│                 ▼                                          │
│  ┌──────────────────────────────────────┐                │
│  │         数据库层 (db/)                 │                │
│  │                                       │                │
│  │  database.py  →  SQLite 连接          │                │
│  │  models.py    →  数据类定义            │                │
│  └──────────────┬───────────────────────┘                │
│                 │                                          │
│                 ▼                                          │
│  ┌──────────────────────────────────────┐                │
│  │     SQLite (data/warehouse.db)        │                │
│  │                                       │                │
│  │  materials / users /                  │                │
│  │  outbound_records / borrow_records    │                │
│  └──────────────────────────────────────┘                │
└──────────────────────────────────────────────────────────┘
```

### 数据流举例：借出一块开发板

```
用户输入: "借出 STM32F407，手机号 138xxxx"
    │
    ▼
checkout.py: checkout(material_id, user_phone, mode="borrow")
    │
    ├── 1. 检查库存 (database.py → SQLite)
    ├── 2. quantity - 1
    ├── 3. INSERT outbound_records (mode="borrow")
    ├── 4. INSERT borrow_records (status="active")
    └── 5. 返回结果
```

---

## 5. 关键设计决策

### 5.1 非耗材个体追踪 vs 耗材合并数量

入库时根据 `is_consumable` 决定存储策略：

- **非耗材**（开发板、工具等）: quantity=10 → INSERT 10 条独立记录，各有唯一编号（DEV-0001 ~ DEV-0010）。每件可独立借还。
- **耗材**（焊锡丝、导线等）: quantity=5 → INSERT 1 条记录，quantity=5。借出时扣减数量。

**唯一标识格式**: `{类别前缀}-{序号}`，每次入库查询当前类别最大序号 +1。

| 类别 | 前缀 |
|------|------|
| 开发板/主控 | DEV |
| 传感器 | SEN |
| 执行器/电机 | ACT |
| 电子元件 | ELC |
| 模块 | MOD |
| 工具 | TOL |
| 耗材 | CON |

### 5.2 出库统一入口 `checkout`

**不是**两个 tool（`remove_material` + `borrow_item`），而是一个 `checkout`，通过 `mode` 参数区分：

```python
@mcp.tool()
async def checkout(
    material_id: str,
    user_phone: str,
    mode: str  # "borrow" 或 "consume"
) -> str:
```

**理由**：借出和领用本质都是"库存 -1 + 记录操作"，只是后处理不同（借出额外创建 borrow_records）。一个入口避免逻辑重复。

### 5.3 操作时决定借/领，不由物料属性死板决定

`materials.is_consumable` 存在，但仅作 UI 默认值提示：
- 耗材：UI 默认选中「领用」
- 非耗材：UI 两者都可选

后端不根据 `is_consumable` 强制限制出库方式（同一块开发板，既可以借也可以领）。

### 5.4 手机号即用户标识

- 无需注册流程
- 首次出现自动创建用户记录
- `users` 表中的 `name` 字段可选

---

## 6. 数据库建表 SQL（实际 schema）

```sql
-- 物料表：非耗材每件独立记录，耗材合并
CREATE TABLE materials (
    id TEXT PRIMARY KEY,             -- DEV-0001, CON-0001 等
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    sub_category TEXT DEFAULT '',
    model TEXT DEFAULT '',
    is_consumable INTEGER NOT NULL DEFAULT 0,  -- 决定入库策略
    quantity INTEGER NOT NULL DEFAULT 0,        -- 非耗材=1，耗材≥1
    location TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE users (
    phone TEXT PRIMARY KEY,
    name TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 出库记录（借出+领用）
CREATE TABLE outbound_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id TEXT NOT NULL,
    user_phone TEXT NOT NULL,
    mode TEXT NOT NULL CHECK(mode IN ('borrow','consume')),
    quantity INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (material_id) REFERENCES materials(id)
);

-- 借还记录（仅 borrow 模式出库时创建）
CREATE TABLE borrow_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id TEXT NOT NULL,
    user_phone TEXT NOT NULL,
    borrowed_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    returned_at TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','returned')),
    FOREIGN KEY (material_id) REFERENCES materials(id)
);
```

---

## 7. Phase 1 搭建顺序 ? 已完成

```
Step 1: 创建 .venv，安装 fastmcp              ?
Step 2: 创建目录结构                            ?
Step 3: db/database.py — SQLite 连接、建表     ?
Step 4: db/models.py   — dataclass 定义        ?（已删除，表结构见 db/database.py 和 DB_DESIGN.md）
Step 5: tools/add_material.py      — 入库      ?
Step 6: tools/checkout.py          — 出库      ?
Step 7: tools/return_item.py       — 归还      ?
Step 8: tools/search_materials.py  — 库存查询  ?
Step 9: tools/borrow_query.py      — 借还记录  ?
Step 10: server.py                 — MCP 组装  ?
Step 11: 功能测试                    ?（18/18）
Step 12: web/app.py                — Streamlit
```

---
## 8. Phase 2 — 智能入库（17/17 测试通过）

### 新增文件
- `llm_client.py` — LLM 推理客户端（OpenAI 兼容，支持 DeepSeek/通义千问 + API Key 本地持久化）
- `tools/smart_add_material.py` — 智能入库工具（`infer_material_info` 推断 + `smart_add_material` 直接入库）
- `tools/intent_router.py` — 意图路由器（`classify_intent` LLM 版 + `classify_intent_fake` 离线规则版）

### 新增数据库结构
- `locations` 表 — 大类→推荐位置映射
- 标签从 17 → 60+ 个

### 配置方式

```powershell
$env:LLM_API_KEY = "sk-xxx"
$env:LLM_BASE_URL = "https://api.deepseek.com"  # 默认
$env:LLM_MODEL = "deepseek-chat"                 # 默认
```

也可以在 Web 界面「高级设置」中输入 Key（支持本地持久化保存到 `data/llm_config.json`，该文件已被 .gitignore 忽略）。

未配置 API Key 时自动降级为离线规则。

### 智能入库流程（两步确认）

```
用户输入名称 → infer_material_info() → 展示推断结果（可编辑） → 用户确认 → add_material()
```

---

## 9. Phase 3 — AI 自然语言对话

### 新增功能
- Web UI 新增「AI 对话」页面，支持自然语言输入
- LLM 自动判断用户意图（入库/查库/出库/归还）并提取参数
- 离线规则降级方案（`classify_intent_fake`）

### 搜索优化（召回 + 语义筛选）

- 关键词自动拆分：LLM 生成的 "MicroPython ESP32 树莓派Pico 开发板" 会被拆为 4 个独立词，每个词 OR 匹配
- 同时搜索物料名 + 标签描述，解决"电路板"vs"开发板"等表述差异
- **两段式过滤**（`tools/search_filter.py`）：先按关键词广度召回候选，再用 LLM（离线规则降级）理解用户真实意图，仅保留符合意图的 `keep_ids`，剔除"名字含关键词但品类不同"的干扰项（如搜"电阻"不再误返回"光敏电阻传感器模块"）
- 真实 LLM 失败时自动降级为离线规则 `filter_materials_fake`（按名称精确度 + 干扰词打分）

### 对话流程

```
用户自然语言 → classify_intent() → 意图+参数 → 直接进入执行步骤 → 展示结果 → 写库前最终确认
         │
         └── intent: inbound  → 推断分类 → 确认入库表单（可编辑）→ 确认入库
         └── intent: search   → 关键词召回 → AI 语义筛选 → 展示结果（只读，无确认）
         └── intent: outbound → 关键词召回 → AI 语义筛选 → 批量勾选+数量 → 确认借出/领用
         └── intent: return   → 查询待归还列表
         └── intent: unknown  → 提示重新描述
```

> 与早期版本相比，移除了意图判定后的「确认意图」步骤：AI 判定意图后直接路由到对应执行步骤展示结果，
> 仅在真正写库前（入库确认 / 出库勾选并确认）保留最终确认，与智能推荐一致的体验。

### 示例

**入库：**
```
用户: "我手头有个刚到的，100多个，是联想的电脑配件，
      可以把一个usb口变成3个usb还有一个网线口的，忘了叫啥了"

AI: 我理解你想入库「USB扩展坞」，数量约 100 个。
    → infer_material_info() → 大类=连接/结构, 子类=接插件/排针, 位置=柜D
    → 确认表单（可编辑）→ 确认入库
```

**出库：**
```
用户: "我想借一块能跑MicroPython的开发板"

AI: 我理解你想出库「MicroPython开发板」
    搜索关键词: MicroPython ESP32 树莓派Pico 开发板
    → 关键词召回 + AI 语义筛选（剔除不符意图的词条）
    → 批量勾选物料 + 数量 + 手机号 + 借出/领用 → 确认出库
```

**查询：**
```
用户: "有没有低功耗的无线通信模块"

AI: 我理解你想查询「低功耗 WiFi 蓝牙 LoRa 通信模块」
    → 关键词召回（物料名 + 标签描述）
    → AI 语义筛选 → 展示匹配结果
```

---

## 10. 编码规范

1. **所有 `.py` 文件首行**：`# -*- coding: utf-8 -*-`
2. **文件命名**：小写 + 下划线（`add_material.py`，不是 `AddMaterial.py`）
3. **函数命名**：小写 + 下划线
4. **类命名**：大驼峰
5. **数据库操作**：全部在 `db/database.py` 中封装，tools 不直接写 SQL
6. **返回给 MCP 的字符串**：用中文，因为用户是中国人

---

## 11. 测试方式

Phase 1 的 MCP Server 已经通过自动化测试验证（18/18 全部通过）。

### 启动 Web 服务
```powershell
& "C:\Anaconda\envs\py312\Scripts\streamlit.exe" run "warehouse_mcp\web\app.py" --server.headless true --server.port 8501 --browser.gatherUsageStats false
```

### 方式 A：直接命令行（开发时用）
```powershell
& "C:\Anaconda\envs\py312\python.exe" -m warehouse_mcp.server
```

### 方式 B：配置到 MCP 客户端
在 `mcp.json` 中添加：
```json
{
  "mcpServers": {
    "warehouse": {
      "command": "C:\\Anaconda\\envs\\py312\\python.exe",
      "args": ["-m", "warehouse_mcp.server"]
    }
  }
}
```

---

> 版本：v0.6 | 日期：2026-08-10
