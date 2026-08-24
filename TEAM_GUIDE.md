# 团队合作指南

> 面向团队同伴（AI 辅助开发）。说明哪些可以改、哪些不能动、应该往什么方向开发。

---

## 一、项目概览

这是一个"物料管理智能体"，面向大学生科创实验室场景。已有功能：

| 功能 | 说明 |
|------|------|
| 手动入库 | 填表单录入物料 |
| 出库 | 借出/领用，需手机号 |
| 归还 | 归还借出的物料 |
| 库存总览 | 关键词/类别/标签搜索 |
| AI 对话 | **核心页面**，自然语言驱动入库/出库/查询 |

当前 AI 对话能力：用户说"帮我入库 10 个 100 欧电阻"或"有没有无线通信模块"，AI 自动判断意图并执行。

项目文件在 `warehouse_mcp/` 下，Streamlit Web 界面在 `warehouse_mcp/web/app.py`。

---

## 二、你的工作范围 == "Skill 层"

### 可以改的文件

```
warehouse_mcp/
├── llm_client.py              ← 核心！LLM 调用、System Prompt、推断逻辑
├── tools/
│   ├── intent_router.py       ← 意图分类（classify_intent / classify_intent_fake）
│   ├── smart_add_material.py  ← 入库推断（infer_material_info）
│   └── recommend.py           ← 项目需求→物料推荐（已实现）
```

### 绝对不能改的文件（基础设施）

```
warehouse_mcp/
├── db/
│   ├── database.py            ← 数据库连接、建表、ID生成
│   └── models.py              ← 数据结构定义
├── tools/
│   ├── add_material.py        ← 基础入库（ID 生成、数据写入）
│   ├── checkout.py            ← 出库逻辑
│   ├── return_item.py         ← 归还逻辑
│   ├── search_materials.py    ← 数据库搜索
│   └── borrow_query.py        ← 借还记录查询
├── server.py                  ← MCP 入口
├── web/app.py                 ← 【只改 AI 对话部分】其他页面不要动
```

**简单理解**：你的代码负责让 AI "想得对"；基础设施负责让数据"存得对"。前者是你的领域，后者是已完工的基础。

如果确实需要改基础设施（比如数据库加字段），请先和项目负责人讨论。

---

## 三、开发方向：让智能体更"聪明"

### 当前不足（就是你要改进的）

1. **入库分类错误**
   - 比如 "USB 扩展坞" 被分到"电子元件"而非"连接/结构"
   - 原因：`infer_material_fake`（离线规则）和 LLM prompt 对边缘物料的判断不准

2. **查询不充分**
   - "开发板"搜不到"电路板"，"无线模块"搜不到"NRF24L01"
   - 已做基础的分词搜索，但同义词/语义匹配还不够

3. **出库搜索不够准**
   - 用户说"我想做 WiFi 遥控小车需要什么"，AI 应该有"项目→物料清单"的推理能力

### 你的任务方向

| 优先级 | 任务 | 涉及文件 |
|--------|------|----------|
| P0 | 优化 LLM System Prompt，减少分类错误 | `llm_client.py`（`_build_system_prompt`） |
| P0 | 完善离线规则 `infer_material_fake`，覆盖更多边缘物料 | `llm_client.py` |
| P1 | 扩展搜索的同义词/语义匹配能力 | `intent_router.py`（`classify_intent`）|
| P1 | 增强标签搜索的语义匹配 | `llm_client.py`（prompt 中提示 LLM 扩展关键词） |
| P2 | 项目推荐：用户描述项目 → LLM 拆解物料清单 → 对照库存 | `tools/recommend.py`（已完成） |

### 怎么做

**修改 LLM System Prompt**：在 `llm_client.py` 的 `_build_system_prompt()` 中补充更多物料分类知识和边界案例。

**修改离线规则**：在 `llm_client.py` 的 `infer_material_fake()` 中添加更多关键词匹配规则。

**增强意图路由**：在 `intent_router.py` 的 `classify_intent` 和 `classify_intent_fake` 中让 LLM 生成更丰富的搜索关键词。

**项目推荐**（已在 `tools/recommend.py` 实现，LLM 版 + 离线版）：
- LLM 版：调用 LLM，从项目描述生成物料清单
- 离线版：内置几个常见项目模板（循迹小车、无人机、智能家居等）

---

## 四、环境配置

### Python 环境

```
路径: C:\Anaconda\envs\py312
Python: 3.12.13
已安装: fastmcp, streamlit, openai
```

```powershell
# 启动 Web 服务
& "C:\Anaconda\envs\py312\Scripts\streamlit.exe" run "warehouse_mcp\web\app.py" --server.headless true --server.port 8501 --browser.gatherUsageStats false
```

### LLM API Key

- 在 Web 界面「AI 对话」→「高级设置」中输入 DeepSeek 等 OpenAI 兼容的 API Key
- 保存到 `data/llm_config.json`（该文件已在 `.gitignore` 中，不会提交）

### 测试数据

仓库已提交测试数据库 `data/warehouse.db`（clone 后可直接使用，含 322 条物料、94 个标签，覆盖全部 10 大类 50+ 子类）。如需重置为初始测试数据，运行 `setup_test_data.py`：

```powershell
& "C:\Anaconda\envs\py312\python.exe" setup_test_data.py
```

### 编码警告

Windows 下 `.py` 文件可能被存为 GBK 编码导致运行报错。如果你用 VS Code，请设置 `"files.encoding": "utf8"`。如果遇到 `UnicodeDecodeError`，运行：

```powershell
& "C:\Anaconda\envs\py312\python.exe" -c "
import os, glob, base
base = r'warehouse_mcp'
for f in glob.glob(os.path.join(base, '**', '*.py'), recursive=True):
    try:
        with open(f, 'r', encoding='gbk') as fh: c = fh.read()
        with open(f, 'w', encoding='utf-8') as fh: fh.write(c)
    except: pass
"
```

---

## 五、Git/GitHub 协作

### 分支策略

```
main ──── 稳定版本（项目负责人维护）
  └── dev ──── 开发分支（日常开发）
       ├── feature/smarter-classify   你正在做的
       └── feature/xxx
```

提交前先 `git pull` 拉取最新代码，避免冲突。

### 提交规范

```
feat: 优化 LLM 分类 prompt，USB扩展坞不再判错
fix: 修复离线规则中红外传感器子类映射
```

### 不要提交

- `data/llm_config.json`（LLM API Key，已在 .gitignore）
- `.env` 等密钥文件
- `__pycache__/`

---

## 六、代码规范

1. 所有 `.py` 文件首行：`# -*- coding: utf-8 -*-`
2. 文件名：小写+下划线（`recommend.py`）
3. 函数注释用中文，说明输入输出
4. 每个功能都写 **LLM 版本 + 离线规则版本**（模式参考 `intent_router.py`），确保不配 API Key 也能用
5. 修改过的函数，保持原有参数签名不变（Web 页面依赖它们）

---

> 文档版本：v1.0 | 日期：2026-08-11
