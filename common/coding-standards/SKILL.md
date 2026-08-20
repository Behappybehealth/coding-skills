---
name: coding-standards
description: 通用研发规范与代码工程搭建标准——新项目启动、代码审查、重构时必须参考。涵盖目录结构、命名规范、Clean Code、SOLID、Git 规范、Python 项目规范、文档规范。可持续追加更新。
---

# 通用研发规范与工程搭建标准

> 本规范适用于所有新项目。在开始写第一行代码前，必须按本规范定好项目骨架。

---

## 第零条：铁律

0. **先对齐，再动手。** 做任何实质性动作（写文件、改代码、提交、删改数据）之前，先用 TodoWrite 列出完整计划，向用户确认需求理解无误、方案拍板后才动工；只读探查（读文件、搜索、测量、跑校验）不受此限，可随时进行。（2026-08-18 用户立规）
1. **先定骨架，再写功能。** 新项目开始前，先画模块结构图，确认目录划分和文件职责，用户确认后再动手写代码。
2. **单文件不超过 300 行。** 超过就必须拆分。
3. **一个文件只做一件事。** 如果你需要用"和"来描述一个文件的职责，它就该拆。
4. **改一个功能，只改一个文件。** 如果需要打开 3 个以上文件才能改一个功能，说明耦合太紧。
5. **数据流单向。** 同一个变量被 3 个以上的地方修改，就会出 bug。
6. **不为图快往现有文件末尾追加。** 每次加功能都先想"这段该放哪"。

---

## 一、项目目录结构

### 1.1 通用骨架（适用于 90% 的项目）

```
project-name/
├── src/                  # 源代码
│   ├── core/             # 核心业务逻辑
│   ├── modules/          # 功能模块（按业务域拆分）
│   ├── utils/            # 工具函数（只放真正复用的）
│   ├── config/           # 配置管理
│   └── main.py           # 入口
├── tests/                # 测试代码（和 src 平行）
├── scripts/              # 脚本工具（构建、部署、数据处理）
├── docs/                 # 文档
├── deploy/               # 部署配置（Docker、nginx 等）
├── data/                 # 数据文件（不进 git）
├── .env                  # 环境变量（不进 git）
├── .gitignore
├── README.md
├── CLAUDE.md             # AI 编程助手项目上下文
└── requirements.txt / pyproject.toml
```

### 1.2 五个结构原则

| 原则 | 说明 |
|---|---|
| **可预测性** | 不用想就知道文件该放哪。如果需要"想一下"，结构就失败了 |
| **关注点分离** | 不同类型的逻辑分开放（UI、业务、数据、配置） |
| **可扩展性** | 5 个文件和 500 个文件都适用同一套结构 |
| **一致 > 创意** | `utils/` `config/` `tests/` 比 `magic-bag/` `stuff/` 好 |
| **不预建空目录** | 项目真正需要时再加，不要一上来建 15 个空文件夹 |

### 1.3 大型项目的两种拆法

**按功能拆（推荐）** — 每个功能自包含，好维护：

```
src/
├── auth/
│   ├── view.py           # UI
│   ├── service.py        # 业务
│   ├── model.py          # 数据
│   └── test_auth.py      # 测试
├── dashboard/
│   ├── view.py
│   ├── service.py
│   └── ...
└── trading/
    └── ...
```

**按层拆** — 经典 MVC，小项目可以，大了会乱：

```
src/
├── views/
├── services/
├── models/
└── routes/
```

### 1.4 小项目的轻量结构

```
project-name/
├── src/
│   └── main.py
├── tests/
└── README.md
```

> 从轻量开始，项目长大了再加目录。"Start simple. Stay consistent. Scale when it hurts."

---

## 二、命名规范

### 2.1 变量

```python
# ❌ 看不懂
d = "2026-08-14"
t = 86400
get_info()

# ✅ 一眼懂
trade_date = "2026-08-14"
SECONDS_IN_A_DAY = 86400
get_user_portfolio()
```

**规则：**
- 变量名要能读出来、能搜到
- 同一个东西用同一个词（别一会 `user` 一会 `client` 一会 `customer`）
- 类里面不要重复类名（`Car.car_make` → `Car.make`）
- 魔法数字必须起名字（`86400` → `SECONDS_IN_A_DAY`）
- 不要用缩写（除非是公认缩写如 `url`, `id`, `http`）

### 2.2 函数

```python
# ❌ 含糊
def handle(data): ...
def process(item): ...
def do_stuff(): ...

# ✅ 明确
def calculate_portfolio_score(trades): ...
def fetch_market_data(symbol): ...
def format_wide_table(result): ...
```

**规则：**
- 函数名说明**做什么**（`send_message` 不是 `handle_message`）
- 用一致的动词前缀：`get_` / `set_` / `create_` / `delete_` / `calculate_` / `fetch_` / `format_`

### 2.3 文件/目录

```
# ✅ 小写、短名、无特殊符号
market_data.py          # 好
MarketData.py           # 不好（类名风格）
market-data.py          # 不好（import 会出错）
market_data_service.py  # 可以但偏长，考虑放子目录
```

---

## 三、Clean Code 原则

### 3.1 函数设计

```python
# ❌ 一个函数干三件事
def process_data(data, send_email=False):
    cleaned = clean(data)
    result = calculate(cleaned)
    if send_email:
        email(result)
    save(result)

# ✅ 一个函数一件事
def clean_data(data) -> list: ...
def calculate_scores(data) -> dict: ...
def send_report(result) -> None: ...
def save_result(result) -> None: ...
```

**函数规则清单：**
- 一个函数只做一件事
- 参数不超过 2-3 个，多了封装成 dataclass / dict
- 不要用布尔参数（flag），它说明函数做了两件事
- 避免副作用（不要偷偷改全局变量）
- 一层抽象——一个函数里调用的子函数应该处于同一抽象层

### 3.2 参数过多时用 dataclass

```python
# ❌ 参数爆炸
def create_report(title, body, button_text, cancellable, timeout, retries): ...

# ✅ 封装配置
@dataclass
class ReportConfig:
    title: str
    body: str
    button_text: str
    cancellable: bool = False
    timeout: int = 30
    retries: int = 3

def create_report(config: ReportConfig): ...
```

### 3.3 避免深层嵌套

```python
# ❌ 嵌套 4 层
if user:
    if user.is_active:
        if user.has_permission:
            if data.is_valid:
                process(data)

# ✅ 提前返回（guard clause）
if not user:
    return None
if not user.is_active:
    return None
if not user.has_permission:
    return None
if not data.is_valid:
    return None
process(data)
```

### 3.4 DRY — 不重复自己

```python
# ❌ 到处重复
score_sp500 = calc_score(spy_price, spy_ma60, spy_rsi)
score_ndx   = calc_score(qqq_price, qqq_ma60, qqq_rsi)
score_gold  = calc_score(gld_price, gld_ma60, gld_rsi)

# ✅ 抽象
scores = {name: calc_score(cfg, data[name]) for name, cfg in assets.items()}
```

---

## 四、SOLID 原则（类/模块设计）

| 原则 | 一句话 | 实操检验 |
|---|---|---|
| **S - 单一职责** | 一个类/模块只有一个改动的理由 | storage 只管读写，不管 UI 渲染 |
| **O - 开闭原则** | 对扩展开放，对修改关闭 | 新增资产只改 config，不改核心代码 |
| **L - 里氏替换** | 子类不能改变父类预期行为 | 子类方法的签名和返回值要兼容父类 |
| **I - 接口隔离** | 接口要小，不逼人实现不需要的东西 | 拆大接口为多个小接口 |
| **D - 依赖倒置** | 依赖抽象，不依赖具体实现 | storage 定义接口，Sheets 和 CSV 都实现它 |

---

## 五、Git 规范

### 5.1 提交信息格式（Conventional Commits）

```
<类型>: <简短描述>

[可选正文]
```

**类型清单：**

| 类型 | 含义 |
|---|---|
| `feat` | 新功能 |
| `fix` | 修 bug |
| `docs` | 改文档 |
| `style` | 格式调整（不改逻辑） |
| `refactor` | 重构（不改功能） |
| `perf` | 性能优化 |
| `test` | 加测试 |
| `chore` | 构建/工具链/依赖 |
| `revert` | 回滚 |

```
# ❌
update code
fix bug
改了点东西

# ✅
feat: 添加黄金 XAUT 行情抓取功能
fix: 修正月末释放计算中交易日计数错误
refactor: 将 app.py 拆分为独立 Tab 模块
chore: 升级 streamlit 到 1.40
```

### 5.2 .gitignore 必选项

```gitignore
# 环境
.venv/
__pycache__/
*.pyc

# 用户数据（不进 git）
data/transactions.csv
data/observations.csv
data/*.localbak

# 密钥
.env
.streamlit/secrets.toml

# 运行时
*.log
*.pid

# IDE
.idea/
.vscode/

# 系统
.DS_Store
Thumbs.db
```

### 5.3 分支策略

- `main` / `master`：永远可部署的稳定版
- `dev` / `develop`：日常开发
- `feature/xxx`：新功能分支
- `fix/xxx`：修 bug 分支
- 合入 main 前必须能跑通、无 lint 报错

> **可执行细则见 `branch-workflow` skill**（六步命令、机密预检、`--ff-only` 与 commit hash
> 稳定性、完成标准）。本节只留口径，具体怎么做以那份为准。（2026-08-20）

---

## 六、Python 项目规范

### 6.1 工具链

| 用途 | 推荐工具 | 配置位置 |
|---|---|---|
| 代码格式化 | `ruff format` | `pyproject.toml` |
| 静态检查 | `ruff check` | `pyproject.toml` |
| 类型提示 | `mypy`（可选但推荐） | `pyproject.toml` |
| 测试 | `pytest` | `tests/` 目录 |
| 依赖管理 | `uv` 或 `poetry` | 替代裸 `pip` |

### 6.2 模块规范

```python
# ✅ 导入顺序：标准库 → 第三方 → 本项目
import json
import pathlib

import pandas as pd
import streamlit as st

from . import storage
from .core import scoring
```

- `__init__.py` 保持空或最小化，不塞大量初始化代码
- 避免 `from xxx import *`（让依赖来源模糊）
- 模块名短、小写、无特殊符号

### 6.3 类型提示

```python
# ❌ 不提示
def calculate(data, amount):
    ...

# ✅ 有提示
def calculate(data: dict, amount: float) -> dict:
    ...

# 复杂类型用 dataclass
@dataclass
class AssetScore:
    name: str
    score: float
    weight: float
    suggested_amount: float
```

### 6.4 错误处理

```python
# ❌ 吞掉错误
try:
    result = fetch_data()
except:
    result = None

# ✅ 明确捕获、有日志
try:
    result = fetch_data()
except ConnectionError as e:
    logger.warning("行情抓取失败: %s", e)
    result = load_cached_data()
```

- 不要用裸 `except:`，永远指定异常类型
- 错误信息要有上下文（什么操作、什么输入、什么失败了）
- 可恢复的错误用 fallback，不可恢复的让程序崩掉并报警

---

## 七、文档规范

### 7.1 项目必备文件

| 文件 | 内容 | 是否必须 |
|---|---|---|
| `README.md` | 项目简介、快速开始、部署说明 | ✅ 必须 |
| `CLAUDE.md` | AI 编程助手的项目上下文 | ✅ 必须（用 Claude Code 时） |
| `.gitignore` | 排除规则 | ✅ 必须 |
| `CHANGELOG.md` | 版本变更记录 | 推荐 |
| `docs/` | 详细文档（架构、API、策略说明） | 中大型项目必须 |

### 7.2 代码注释

```python
# ❌ 废话注释（代码本身已经说清楚了）
x = x + 1  # x 加 1

# ✅ 解释 WHY（代码说清 WHAT，注释说清 WHY）
# 月末最后 7 天释放剩余预算，防止月底资金闲置
if remaining_days <= 7 and available_pool > 0:
    min_amount = daily_baseline
```

**注释规则：**
- 注释解释 WHY（为什么这么做），代码本身解释 WHAT（做了什么）
- 公共函数/类必须有 docstring（参数、返回值、异常）
- TODO 注释带作者和日期：`# TODO(作者名 2026-08): 支持多币种`
- 删除无用注释，不要留着"以后可能用到"

### 7.3 README 模板

```markdown
# 项目名称

一句话描述。

## 快速开始

1. 克隆项目
2. 安装依赖
3. 配置环境变量
4. 启动

## 项目结构

（目录树 + 各目录职责）

## 开发指南

（如何加新功能、如何跑测试、如何部署）

## 技术栈

（主要依赖和版本）
```

---

## 八、项目启动清单（Checklist）

每次开始一个新项目，按这个清单走：

- [ ] 确定项目类型和技术栈
- [ ] 画模块结构图（哪些目录、哪些文件、各自职责）
- [ ] 用户确认结构后再开始写代码
- [ ] 创建 `.gitignore`
- [ ] 创建 `README.md`
- [ ] 创建 `CLAUDE.md`（如用 Claude Code）
- [ ] 初始化 git 仓库，首次提交
- [ ] 配置代码格式化工具（ruff / prettier）
- [ ] 配置 lint 工具
- [ ] 建立 `tests/` 目录，写第一个测试
- [ ] 确认目录结构合理（根目录不堆放杂文件）

---

## 附录：参考来源

- [The Ultimate Folder Structure Guide — Medium](https://medium.com/@boubkerelmaayouf/the-ultimate-folder-structure-guide-for-any-project-any-language-6bb5b8fbd5b3)
- [Clean Code Python — GitHub](https://github.com/zedr/clean-code-python)
- [Structuring Your Project — The Hitchhiker's Guide to Python](https://docs.python-guide.org/writing/structure/)
- [Best Practices for Coding, Organization, and Documentation — MIT CommLab](https://mitcommlab.mit.edu/broad/commkit/best-practices-for-coding-organization-and-documentation/)
- [项目搭建规范 — CSDN](https://blog.csdn.net/ASHIYI66/article/details/134640800)
- [dev-guide — GitHub](https://github.com/roomAchar/dev-guide)
