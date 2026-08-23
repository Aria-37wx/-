# 数据库设计文档

> Phase 1 重构基线。本文档定义最终版数据库 schema，后续不再轻易改动。

---

## 一、大类与子类体系（MECE）

**设计原则**：互斥（每件物料只属一类）+ 穷尽（所有物料都有类可归）。

### 分类总表

| 大类 | 代码 | 子类 |
|------|------|------|
| **主控板** | `MC` | MCU/单片机 · 单板机SBC · FPGA/CPLD · DSP · 其他 |
| **传感模块** | `SN` | 距离/位置 · 温度/湿度 · 运动/姿态(IMU) · 光/颜色/图像 · 环境(气压/气体/声音) · 电流/电压 · 生物/医学 · 其他 |
| **执行/驱动** | `AC` | 直流电机 · 步进电机 · 舵机/伺服 · 电机驱动板 · 继电器/接触器 · 气动/液压 · 其他 |
| **通信模块** | `CM` | 蓝牙 · WiFi · LoRa/NB-IoT · 射频/NFC · 以太网/CAN/485 · 其他 |
| **显示/交互** | `DP` | OLED/LCD · LED/数码管 · 按键/旋钮 · 蜂鸣器/扬声器 · 触摸屏 · 其他 |
| **电源模块** | `PW` | 电池 · 稳压/升降压 · 充电管理 · 电源适配器 · 其他 |
| **电子元件** | `EC` | 电阻 · 电容 · 电感/磁珠 · 二极管 · 三极管/MOS · IC/运放 · 晶振 · 其他 |
| **连接/结构** | `CN` | 导线/排线 · 接插件/排针 · 面包板/洞洞板 · 紧固件 · 结构件(支架/底盘/轮子) · 其他 |
| **工具** | `TL` | 测量仪器 · 焊接工具 · 拆装工具 · 电源/信号源 · 其他 |
| **耗材** | `CS` | 焊料/助焊剂 · 胶带/胶水 · 热缩管 · 清洁/防静电 · 其他 |

### 互斥验证

| 物料 | 归入 | 为什么不归入其它类 |
|------|------|--------------------|
| HC-05 蓝牙 | CM | 通信功能，不是传感 |
| L298N 电机驱动 | AC | 驱动电机的，归入执行类 |
| GPS 模块 | SN | 定位 = 感知功能 |
| 面包板 | CN | 连接结构，不消耗所以不归耗材 |
| LED（单颗） | EC | 离散元件，不是显示模块 |
| OLED 屏（模块） | DP | 成品显示模块 |
| 18650 电池 | PW | 供电 = 电源类 |
| 热风枪 | TL | 可反复使用的工具 |

### 穷尽验证

任何大学生科创场景中可能出现的物料，总能找到归属：
- 没有对应子类 → 选"其他"
- 属于大类但需要语义标签 → 走标签系统（见第三节）

---

## 二、唯一标识（ID）设计

### 格式

```
{大类码}-{子类码}-{YYYYMMDD}-{NNNN}

AC-DCM-20260809-0001   执行/驱动 → 直流电机，2026-08-09入库，当日第1件
MC-MCU-20260809-0003   主控板 → MCU/单片机，同日第3件
EC-RES-20260809-0002   电子元件 → 电阻，同日第2件
```

### 三段语义（实为四段）

| 段 | 含义 | 检索用途 |
|----|------|----------|
| `AC` | 大类代码 | Phase 3 LLM 可按大类缩小范围：`AC-*` = 所有执行/驱动类 |
| `DCM` | 子类代码（3 字母助记） | 精确定位到子类：`AC-DCM-*` = 直流电机，无需再筛子类字段 |
| `20260809` | 入库日期 | 可按月统计入库量 |
| `0001` | 当日该子类序号 | 保证唯一性 |

### 子类助记码对照表

| 大类 | 子类 | 代码 |
|------|------|------|
| 主控板 MC | MCU/单片机 | MCU |
| | 单板机SBC | SBC |
| | FPGA/CPLD | FPG |
| 执行/驱动 AC | 直流电机 | DCM |
| | 步进电机 | STP |
| | 舵机/伺服 | SRV |
| | 电机驱动板 | MDR |
| 电子元件 EC | 电阻 | RES |
| | 电容 | CAP |
| | IC/运放 | ICS |
| ... | ... | ... |

> 完整对照见 `warehouse_mcp/db/database.py` 的 `CATEGORIES` 常量。每个子类有唯一 3 字母码，大类+子类共构成 5 字母 ID 前缀。

### 生成逻辑

```python
def generate_id(category_code: str, date_str: str) -> str:
    # 查询当日该类别已有的最大值
    # SELECT MAX(CAST(SUBSTR(id, 13) AS INTEGER))
    # FROM materials
    # WHERE id LIKE '{code}-{date}-%'
    # 返回 {code}-{date}-{seq+1:04d}
```

### 为什么不用 UUID

- UUID 无含义，人类不可读，LLM 无法从中提取任何信息
- `MC-20260809-0001` 看一眼就知道：主控板、今天入库的、第1件
- Phase 3 时 LLM 可以用前缀缩小搜索范围，省 token

---

## 三、标签系统

### 设计定位

```
子类 = "这是什么类型的物料"（固定字段，互斥）
标签 = "这个物料有什么故事"（灵活字段，非互斥，带描述）
```

标签系统是 Phase 3 智能检索的核心——LLM 匹配用户需求与标签描述来找到物料。

### 表结构

```sql
-- 标签定义表
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,       -- 标签名，如 "ESP32"、"L298N"、"Arduino"
    description TEXT DEFAULT ''       -- 描述说明，LLM 搜索的目标文本
);

-- 物料-标签关联表（多对多）
CREATE TABLE material_tags (
    material_id TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    PRIMARY KEY (material_id, tag_name),
    FOREIGN KEY (material_id) REFERENCES materials(id),
    FOREIGN KEY (tag_name) REFERENCES tags(name)
);
```

### 标签 vs 子类的边界

| 维度 | 子类 | 标签 |
|------|------|------|
| 属性 | 互斥（一个物料只有一个子类） | 非互斥（一个物料可以有多个标签） |
| 内容 | 分类标识（"电阻"、"MCU/单片机"） | 概念/产品系列 + 描述 |
| 用途 | 人类浏览、固定查询 | LLM 语义匹配 |
| 例子 | `子类 = "MCU/单片机"` | `标签: "ESP32" → 描述: "双核MCU，WiFi+BLE..."` |

**子类已经覆盖的基础概念不要重复打标签**：
- 100Ω 电阻：子类="电阻"，不需要标签（子类已经说明了它是电阻）
- HC-SR04：子类="距离/位置"，标签="HC-SR04"（补充产品系列信息）

**标签主要打在产品系列/功能家族级别**：
- ESP32 开发板：标签="ESP32"、"IoT开发板"
- L298N 驱动板：标签="L298N"、"电机驱动"
- 树莓派 4B：标签="树莓派"、"单板机"、"Linux"

### Phase 3 检索流程

```
用户: "我想做WiFi遥控小车"

LLM 推理 → 需要的物料概念：
  "WiFi通信" → 搜标签描述含 WiFi 的 → 找到 "ESP32"、"ESP8266"
  "电机驱动" → 搜标签描述含 电机驱动 的 → 找到 "L298N"、"TB6612"
  "电源"     → 大类 PW + 子类 电池

  → 联合查询：有这些标签的物料 + 电源类物料
  → 返回清单 + 库存状态
```

---

## 四、完整数据库 Schema

### 4.1 物料表 `materials`

```sql
CREATE TABLE materials (
    id TEXT PRIMARY KEY,                          -- AC-DCM-20260809-0001
    name TEXT NOT NULL,                            -- "TT 直流电机"
    category TEXT NOT NULL,                        -- "执行/驱动"
    category_code TEXT NOT NULL,                   -- "AC"
    sub_category TEXT NOT NULL,                    -- "直流电机"
    sub_category_code TEXT NOT NULL,               -- "DCM"
    model TEXT DEFAULT '',                         -- "TT Motor"
    is_consumable INTEGER NOT NULL DEFAULT 0,      -- 0=非耗材 1=耗材
    quantity INTEGER NOT NULL DEFAULT 1,           -- 非耗材每件=1，耗材可>1
    location TEXT DEFAULT '',                      -- "柜A-1"
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX idx_materials_category ON materials(category_code);
CREATE INDEX idx_materials_name ON materials(name);
CREATE INDEX idx_materials_created ON materials(created_at);
```

> 入库策略：非耗材 quantity=N → INSERT N 条独立记录（DEV-0001 ~ DEV-N）；耗材 → 1 条记录 quantity=N。

### 4.2 标签表 `tags`

```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT ''
);

CREATE INDEX idx_tags_name ON tags(name);
```

### 4.3 物料-标签关联表 `material_tags`

```sql
CREATE TABLE material_tags (
    material_id TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    PRIMARY KEY (material_id, tag_name),
    FOREIGN KEY (material_id) REFERENCES materials(id),
    FOREIGN KEY (tag_name) REFERENCES tags(name)
);
```

### 4.4 用户表 `users`

```sql
CREATE TABLE users (
    phone TEXT PRIMARY KEY,
    name TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
```

### 4.5 出库记录表 `outbound_records`

```sql
CREATE TABLE outbound_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id TEXT NOT NULL,
    user_phone TEXT NOT NULL,
    mode TEXT NOT NULL CHECK(mode IN ('borrow','consume')),
    quantity INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (material_id) REFERENCES materials(id)
);

CREATE INDEX idx_outbound_material ON outbound_records(material_id);
CREATE INDEX idx_outbound_user ON outbound_records(user_phone);
CREATE INDEX idx_outbound_created ON outbound_records(created_at);
```

### 4.6 借还记录表 `borrow_records`

```sql
CREATE TABLE borrow_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id TEXT NOT NULL,
    user_phone TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,  -- 借出数量，归还时按量恢复库存
    borrowed_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    returned_at TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','returned')),
    FOREIGN KEY (material_id) REFERENCES materials(id)
);

CREATE INDEX idx_borrow_material ON borrow_records(material_id);
CREATE INDEX idx_borrow_user ON borrow_records(user_phone);
CREATE INDEX idx_borrow_status ON borrow_records(status);
```

---

## 五、表关系图

```
┌──────────────┐     ┌─────────────────┐     ┌──────────┐
│  materials   │────→│  material_tags   │←────│   tags   │
│              │     │  material_id     │     │  name    │
│  id (PK)     │     │  tag_name        │     │  desc    │
│  name        │     └─────────────────┘     └──────────┘
│  category    │
│  sub_category│     ┌──────────────────┐     ┌──────────┐
│  model       │────→│ outbound_records  │←────│  users   │
│  quantity    │     │  material_id      │     │  phone   │
│  location    │     │  user_phone       │     │  name    │
└──────────────┘     │  mode             │     └──────────┘
       │             └──────────────────┘
       │             ┌──────────────────┐
       └────────────→│ borrow_records    │
                     │  material_id      │
                     │  user_phone       │
                     │  status           │
                     └──────────────────┘
```

---

## 六、常见查询

### 库存总览
```sql
SELECT category, sub_category, COUNT(*) as cnt, SUM(quantity) as total
FROM materials
WHERE quantity > 0
GROUP BY category, sub_category
ORDER BY category;
```

### 搜索物料（多字段模糊匹配）
```sql
SELECT * FROM materials
WHERE (name LIKE '%关键词%'
   OR category LIKE '%关键词%'
   OR model LIKE '%关键词%'
   OR sub_category LIKE '%关键词%')
AND quantity > 0;
```

### 带标签的物料详情
```sql
SELECT m.*, GROUP_CONCAT(t.name) as tags, GROUP_CONCAT(t.description, '; ') as tag_descs
FROM materials m
LEFT JOIN material_tags mt ON m.id = mt.material_id
LEFT JOIN tags t ON mt.tag_name = t.name
WHERE m.id = 'MC-20260809-0001'
GROUP BY m.id;
```

### 按标签搜索物料（Phase 3 核心查询）
```sql
-- 搜索标签描述中包含某关键词的物料
SELECT DISTINCT m.*
FROM materials m
JOIN material_tags mt ON m.id = mt.material_id
JOIN tags t ON mt.tag_name = t.name
WHERE t.description LIKE '%WiFi%'
   OR t.name LIKE '%ESP32%';
```

### 查询某人借出中的物料
```sql
SELECT br.id, m.name, br.borrowed_at
FROM borrow_records br
JOIN materials m ON br.material_id = m.id
WHERE br.user_phone = '13800000001'
  AND br.status = 'active';
```

---

## 七、分类/子类/标签 预置数据

### 标签预置（产品系列级别，Phase 1 即可插入）

```sql
-- 开发板/主控类标签
INSERT INTO tags (name, description) VALUES
('Arduino Uno', 'ATmega328P，5V逻辑，入门级MCU开发板，丰富扩展生态，适合教学和原型验证'),
('ESP32', '乐鑫双核MCU，内置WiFi 802.11b/g/n和BLE 4.2，160MHz，支持Arduino/MicroPython/ESP-IDF开发，适合IoT和无线应用'),
('ESP8266', '乐鑫单核WiFi MCU，80/160MHz，低成本IoT方案，支持Arduino/NodeMCU'),
('STM32F4', 'ARM Cortex-M4 @168MHz，带DSP和FPU，高性能MCU，适合实时控制和信号处理'),
('STM32F1', 'ARM Cortex-M3 @72MHz，经典入门MCU，适合教学和通用控制'),
('树莓派', 'Linux单板计算机，丰富GPIO/HDMI/USB，适合视觉处理、边缘计算和教学'),
('K210', 'RISC-V双核+KPU神经网络加速器，适合边缘AI和视觉应用'),

-- 电机驱动类标签
('L298N', '双H桥电机驱动模块，可驱动2个直流电机或1个步进电机，逻辑5V驱动5-35V'),
('TB6612', '双H桥电机驱动模块，比L298N效率更高，适合电池供电项目'),
('A4988', '步进电机驱动模块，支持微步进，适合3D打印机和CNC'),

-- 传感类标签
('HC-SR04', '超声波测距模块，2cm-400cm，5V，用于避障和距离检测'),
('MPU6050', '6轴IMU（3轴加速度+3轴陀螺仪），I2C接口，用于姿态解算和运动检测'),
('DHT11', '数字温湿度传感器，精度±2℃/±5%RH，适合环境监测入门'),

-- 通信类标签
('HC-05', '蓝牙2.0串口透传模块，主从一体，适合短距离无线通信'),
('NRF24L01', '2.4GHz无线收发模块，SPI接口，适合多节点组网'),
('LoRa', '低功耗远距离无线通信技术，适合户外IoT和农业监测');
```

### 分类/子类常量（写入工具代码）

```python
CATEGORIES = {
    "主控板":    {"code": "MC", "subs": [
        "MCU/单片机", "单板机SBC", "FPGA/CPLD", "DSP", "其他"
    ]},
    "传感模块":  {"code": "SN", "subs": [
        "距离/位置", "温度/湿度", "运动/姿态(IMU)", "光/颜色/图像",
        "环境(气压/气体/声音)", "电流/电压", "生物/医学", "其他"
    ]},
    "执行/驱动": {"code": "AC", "subs": [
        "直流电机", "步进电机", "舵机/伺服", "电机驱动板",
        "继电器/接触器", "气动/液压", "其他"
    ]},
    "通信模块":  {"code": "CM", "subs": [
        "蓝牙", "WiFi", "LoRa/NB-IoT", "射频/NFC",
        "以太网/CAN/485", "其他"
    ]},
    "显示/交互": {"code": "DP", "subs": [
        "OLED/LCD", "LED/数码管", "按键/旋钮",
        "蜂鸣器/扬声器", "触摸屏", "其他"
    ]},
    "电源模块":  {"code": "PW", "subs": [
        "电池", "稳压/升降压", "充电管理", "电源适配器", "其他"
    ]},
    "电子元件":  {"code": "EC", "subs": [
        "电阻", "电容", "电感/磁珠", "二极管", "三极管/MOS",
        "IC/运放", "晶振", "其他"
    ]},
    "连接/结构": {"code": "CN", "subs": [
        "导线/排线", "接插件/排针", "面包板/洞洞板",
        "紧固件", "结构件(支架/底盘/轮子)", "其他"
    ]},
    "工具":      {"code": "TL", "subs": [
        "测量仪器", "焊接工具", "拆装工具", "电源/信号源", "其他"
    ]},
    "耗材":      {"code": "CS", "subs": [
        "焊料/助焊剂", "胶带/胶水", "热缩管", "清洁/防静电", "其他"
    ]},
}
```

---

## 八、locations 表（Phase 2 新增）

```sql
CREATE TABLE locations (
    category TEXT PRIMARY KEY,
    recommended TEXT NOT NULL
);
```

预置数据：

| 大类 | 推荐位置 |
|------|----------|
| 主控板 | 柜A-1 主控板区 |
| 传感模块 | 柜A-2 传感器区 |
| 执行/驱动 | 柜B-1 电机驱动区 |
| 通信模块 | 柜A-3 通信模块区 |
| 显示/交互 | 柜A-4 显示交互区 |
| 电源模块 | 柜B-2 电源区 |
| 电子元件 | 柜C 元件抽屉 |
| 连接/结构 | 柜D 连接结构区 |
| 工具 | 柜E 工具区 |
| 耗材 | 柜F 耗材区 |

智能入库时根据推断的大类自动分配位置，手动入库时位置字段仍可自由选择。

---

> 文档版本：v1.1 | 日期：2026-08-09
