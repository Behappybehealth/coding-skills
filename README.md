# coding-skills — Claude Code 技能库

本仓是 `X:\coding\skills` 的全量版本管理。所有给 Claude Code 用的 skill 只此一份，
通过目录联接挂进 `~/.claude/skills`，不存副本。

> **本文是给人读的目录与选用指南；每个 skill 的实际执行指令在它自己的 `SKILL.md` 里。**
> 二者分工固定：改行为改 `SKILL.md`，本文只维护"有哪些、什么时候用哪个、彼此什么关系"。
> 不要把 `SKILL.md` 的内容抄进本文——那会立刻变成第二事实源并开始漂移。

---

## 一、为什么单独一个库

skill 原先散落在 `~/.claude/skills` 下（一度还把整个 Streamlit 项目塞在某个 skill 目录里），
2026-08-17 统一迁到 `X:\coding\skills`，2026-08-20 纳入 git。

纳管前的实际代价：改 skill 没有 diff 可复核、改坏了没有版本可退、
"上周是不是改过这段"只能靠回忆。skill 是**直接改变 AI 行为**的文件，
比普通配置更需要可追溯——一处措辞改动可能让后续所有会话的做法都变。

## 二、关键机制：目录联接（改这里就是改生效版本）

`~/.claude/skills` 下的每一项都是**指向本仓的链接，不是真实目录**：

| `~/.claude/skills/` 下的名字 | 链接类型 | 指向 |
|---|---|---|
| `branch-workflow` | SymbolicLink | `X:\coding\skills\common\branch-workflow` |
| `coding-standards` | Junction | `X:\coding\skills\common\coding-standards` |
| `self-check` | Junction | `X:\coding\skills\common\self-check` |
| `investment-dca` | Junction | `X:\coding\skills\projects\investment-dca` |
| `sp500-nasdaq100-gold-dca` | Junction | `X:\coding\skills\projects\sp500-nasdaq100-gold-dca` |
| `kimi-webbridge` | Junction | `X:\coding\skills\tools\kimi-webbridge` |

注意三点：

1. **联接是平铺的**，分类目录（`common` / `projects` / `tools`）只存在于本仓，
   Claude Code 那边看到的是 6 个同级技能。分类怎么调整都不影响加载。
2. **`~/.claude/skills` 下任何真实目录都会被扫成一个技能。**
   备份副本别放那里——`xxx.old` 会变成一个重复技能项。
3. **skill 在会话启动时加载，改完当前会话不生效。** 本仓建立当天实测：
   改写 `branch-workflow/SKILL.md` 后，同一会话的技能清单仍然是旧内容。
   验证改动必须开新会话或 `/clear`。

新增 skill 后建联接：

```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\<名字>" -Target "X:\coding\skills\<分类>\<名字>"
```

（Junction 不需要管理员权限，SymbolicLink 需要——所以默认用 Junction。）

## 三、目录结构

```
X:\coding\skills\
├── README.md                  # 本文
├── .gitignore                 # 排除 __pycache__ / *.pyc
├── common\                    # 跨项目通用规范
│   ├── branch-workflow\       SKILL.md
│   ├── coding-standards\      SKILL.md
│   └── self-check\            SKILL.md
├── projects\                  # 绑定具体项目的 skill
│   ├── investment-dca\        SKILL.md + scripts\dca_advisor.py    ⚠️ 见第五节
│   └── sp500-nasdaq100-gold-dca\  SKILL.md（脚本在项目仓里，不在这）
└── tools\                     # 外部工具的操作说明
    └── kimi-webbridge\        SKILL.md + references\operations.md   ⚠️ 第三方
```

## 四、六个 skill

| skill | 分类 | 一句话 | 归属 |
|---|---|---|---|
| [coding-standards](common/coding-standards/SKILL.md) | 通用 | 研发规范总纲：目录结构、命名、Clean Code、SOLID、Git、Python、文档 | 自写 |
| [branch-workflow](common/branch-workflow/SKILL.md) | 通用 | 分支管理可执行细则：六步命令、机密预检、`--ff-only` | 自写 |
| [self-check](common/self-check/SKILL.md) | 通用 | 用户指出一个问题时，扫描并一并修正所有同类项 | 自写 |
| [sp500-nasdaq100-gold-dca](projects/sp500-nasdaq100-gold-dca/SKILL.md) | 项目 | 三资产动态定投每日决策（**现行版**） | 自写 |
| [investment-dca](projects/investment-dca/SKILL.md) | 项目 | 三资产定投建议（**旧版，与上一条冲突**） | 自写 |
| [kimi-webbridge](tools/kimi-webbridge/SKILL.md) | 工具 | 通过本地守护进程操控用户真实浏览器 | 第三方（Kimi） |

---

### coding-standards — 研发规范总纲

**何时用**：新项目启动、代码审查、重构。是其余规范类 skill 的根。

**内容**：铁律 7 条（先对齐再动手／先定骨架再写功能／单文件 ≤ 300 行／一个文件一件事／
改一个功能只改一个文件／数据流单向／不为图快往文件末尾追加）、目录骨架与三种拆法、
命名规范、Clean Code、SOLID、Git 规范（Conventional Commits + `.gitignore` 必选项 + 分支策略）、
Python 工具链与错误处理、文档规范、项目启动清单。

**边界**：§5.3「分支策略」只留口径，可执行细则交给 `branch-workflow`——两者是总纲与展开的关系，
提交信息格式以本篇 §5.1 为准，`branch-workflow` 不重复。

---

### branch-workflow — 分支管理可执行细则

**何时用**：任何可能让测试变红的改动动手之前。判断口径一句话：**这次改动可能让 `pytest` 变红吗？**
会 → 建分支；纯文档／回填 hash → 直接默认分支。

**内容**：`main` / `origin` / `origin/main` 三个名字的辨析（§〇）、六步命令、
四条硬要求（绝不 squash/rebase、push 前两条机密预检、每批提交后报分支状态、合并前后各跑一次门禁）、
八个常见坑、完成标准清单。

**为什么存在**：不是流程错，是**沟通缺口**——曾整批改动都在分支上做完却从没告诉用户默认分支一步没动，
用户问"这不是只有一个 master 吗？没合是怎么没合？"。硬要求 3 就是为这个加的。

**注意**：文中命令统一用 `$MAIN` 变量而非硬编码分支名，因为不同项目默认分支不同
（`sp500-nasdaq100-gold-dca` 用 `main`，本仓用 `master`）。照抄前先取值。

---

### self-check — 自查机制

**何时用**：用户指出报告／数据／代码里的任何一个问题时，立即触发。

**核心**：用户指出一个问题 = 可能存在 N 个同类问题。四步——定位问题类型 → 扫描所有同类项 →
列出全部发现 → 一并修正。目的是避免"修一个、用户再指一个"的反复打扰。

**特殊之处**：这个 skill 自带**自查记录**（文件末尾），每次触发后追加
「用户指出／自查发现／修正内容／教训」四行。所以它是唯一一个会随使用而增长的 skill。

---

### sp500-nasdaq100-gold-dca — 三资产动态定投（现行版）

**何时用**：每日定投决策、记账、查预算进度。

**做什么**：固定闭环——复盘上一条记录 → 累计持仓 → 自然月剩余预算 → 行情信号 →
今日金额与比例 → 等用户反馈实际执行后再记录。回答固定 9 段，必须中文。

**它不含计算逻辑**：脚本在项目仓 `X:\coding\projects\sp500-nasdaq100-gold-dca` 里
（`scripts/dca_calculator.py` 算、`scripts/dca_action.py` 写），本 skill 只负责
"怎么调、怎么组织回答、什么不许做"。所以项目仓的引擎改了，这里的说明要同期核对。

**中性权重**：标普500 35% / 纳指100 45% / 黄金 20%。
**资金口径**：自然月预算默认 30000 RMB，可用池 ÷ 剩余交易日为每日基准，跳过的份额自动摊入后续交易日。
**记账**：一律走 `scripts/dca_action.py`，不许直接编辑 `data/*.csv`（会绕过写前快照与云端分流）。

**风险边界写在 skill 里且不可省**：不承诺收益、不鼓励杠杆、行情抓取失败必须明说失败而不是编造。
用户风险画像是"不能接受卖出实现的亏损，但可接受较大浮亏"，所以必须明确告知
策略无法保证不亏，也不得暗示"扛住就一定回本"。

---

### investment-dca — 三资产定投建议（旧版，⚠️ 与现行版冲突）

**状态**：被 `sp500-nasdaq100-gold-dca` 取代，但仍是活跃 skill，仍可能被触发。**详见第五节第 1 条。**

**它是什么**：完全自包含的早期版本——`scripts/dca_advisor.py`（754 行）自己抓 Yahoo、
自己算指标、自己记账到 `~/.claude/investment-dca/portfolio.json` 与 `daily_records.csv`，
不依赖任何项目仓。

**与现行版的实质差异**：

| | investment-dca（旧） | sp500-nasdaq100-gold-dca（现行） |
|---|---|---|
| 中性权重 | 标普500 **45%** / 纳指100 **35%** / 黄金 20% | 标普500 **35%** / 纳指100 **45%** / 黄金 20% |
| 金额决定 | 四档离散（强烈建议／建议／试探／不买）乘用户输入金额 | 连续评分模型 → 部署系数 × 每日基准 |
| 预算模型 | 剩余预算 ÷ 自然月剩余天数 | 可用池 ÷ 剩余**交易日**，跳过份额再平均，月末释放 |
| 计价 | 人民币，指数 proxy | USDT 本位（SPY/QQQ/XAUT），双汇率折算 |
| 数据落点 | `~/.claude/investment-dca/` | 项目仓 `data/`，云端 Google Sheets 或本地 CSV |
| 收益口径 | 收益率 + 年化 + XIRR | 同上，另有持有期不足 30 天不年化的保护 |

---

### kimi-webbridge — 浏览器操控（第三方）

**何时用**：需要真实浏览器（带用户已登录会话）访问网页、点击、填表、截图、抓内容时。

**做什么**：通过 `http://127.0.0.1:10086` 的本地守护进程下发 14 个动作
（`navigate` / `snapshot` / `click` / `fill` / `evaluate` / `screenshot` / `save_as_pdf` / `cdp` …）。
一个任务 = 一个 session = 一个标签组。

**Windows 上最要紧的一条**：shell 会把命令行里的非 ASCII 字符（中文）损坏成 `?` 且不可恢复，
所以**每个请求都必须写成临时 JSON 文件再 `curl.exe --data-binary @文件` 发送**，
且必须用 `curl.exe` 而非裸 `curl`（PowerShell 把后者别名成 `Invoke-WebRequest`）。

**归属提醒**：这份由 Kimi（Moonshot）提供，`metadata.version: 1.11.5`，**不是自写的**。
上游更新时应当整目录替换而不是逐行改——本地手改会在下次更新时冲突，且改了也不影响守护进程的真实行为。
自己的使用心得写进别处，不要混进这份文件。

---

## 五、已知问题

1. **两个 DCA skill 的中性权重相反，且都是活跃 skill。**
   `investment-dca` 是 45/35/20，`sp500-nasdaq100-gold-dca` 是 35/45/20——标普和纳指对调。
   两者的 `description` 都写着"为标普500、纳指100和黄金生成每日定投建议"，
   一句"看看今天定投"完全可能匹配到旧的那个，给出与现行策略不同的分配。
   **暂行办法：涉及定投一律显式指名 `sp500-nasdaq100-gold-dca`。**
   根治要么删除／归档 `investment-dca`，要么改写它的 `description` 使其不再匹配日常定投请求——
   两者都是行为变更，需用户拍板后再动。

2. **`dca_advisor.py` 754 行，违反 `coding-standards` 自己的"单文件不超过 300 行"。**
   属旧版遗留，不打算重构（见第 1 条，倾向于归档而非改进）。

3. **`investment-dca/SKILL.md` 的 frontmatter 只有 `description`，没有 `name`。**
   靠目录名推导，能正常加载，但与其余 5 个不一致。

4. **本仓没有测试也没有 CI。** skill 是自然语言指令，正确性只能靠实际会话验证，
   而验证必须开新会话（见第二节第 3 点）。所以改 skill 后请显式跑一次真实场景，
   别只看 diff 就认为改对了。

## 六、改这个库的规矩

1. **一个 skill 一个目录，目录名 = skill 名**（`~/.claude/skills` 那边的联接名与它一致）。
2. **`SKILL.md` 的 frontmatter 必须有 `name` 与 `description`**；`description` 决定它何时被触发，
   写清"什么场景用"，不要只写"做什么"。
3. **不写绝对路径。** 用 `$HOME` / `%USERPROFILE%` 或项目相对路径——硬编码 `C:\Users\<名字>\...`
   既把用户名写进仓库，也让路径一换机器就断。
4. **提交信息用 Conventional Commits**（与 `coding-standards` §5.1 同口径）。
5. **第三方 skill 整目录替换，不逐行改**（见 `kimi-webbridge` 那节）。
6. **默认分支 `master`**，本仓无 CI，纯文档改动可直接提交在其上；
   成批的行为改动仍建议按 `branch-workflow` 走分支。

---

## 变更记录

### 2026-08-20 建库
- **触发**：用户要求给 `X:\coding\skills` 写整体说明与各 skill 说明，并纳入 git。
- **顺序**：先原样提交基线（`45c224f`）再改动，使纳管前的状态可回退——此前改 skill 无版本可退。
- **入库前扫描结论**：无任何真实凭据（两处 `secrets` 字样均为教程里的检查模式串）；
  无真实持仓与成本数据（`dca_advisor.py` 的账本落 `~/.claude/investment-dca/`，在本仓之外）。
  仓库设为**私有**：`30000 RMB` 月度预算属个人财务信息，虽非持仓明细也不宜公开。
- **同期发现并记入第五节**：两个 DCA skill 权重相反且都活跃（最要紧的一条）、
  `dca_advisor.py` 超行数上限、`investment-dca` frontmatter 缺 `name`。
