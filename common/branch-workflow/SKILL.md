---
name: branch-workflow
description: 分支管理规范——任何可能改变行为的改动都先建 fix/feat 分支，跑完门禁再 ff-only 合入默认分支并 push。含默认分支/origin/远端跟踪分支的术语辨析、逐步命令、机密预检、commit hash 稳定性要求、以及"人在分支上而用户以为已合入"这类沟通坑的对策。
---

# 分支管理规范（Branch Workflow）

> **铁律：默认分支永远是"跑得通的最新状态"。任何可能让测试变红的改动都不在它上面直接写。**
> （2026-08-20 用户立规：修问题都要建 fix 分支，验证后统一合入默认分支）

---

## 〇、先分清三个名字

这三个最容易混，且混了会导致"以为推上去了其实没推"这类实质错误：

| 写法 | 是什么 | 存在哪 |
|---|---|---|
| `main` / `master` | **你本机的分支** | 本机 `.git/refs/heads/<名>` |
| `origin` | **远端仓库的别名——不是分支** | 远端 URL（GitHub 等），`git remote -v` 可查 |
| `origin/main` | 远端那条分支在本机的**只读快照** | 本机 `.git/refs/remotes/origin/<名>` |

一句话记忆：**带斜杠的是"远端的影子"，不带斜杠的是"你手上的"；`origin` 单独出现时指整个远端仓库。**

关键陷阱：`origin/<默认分支>` 只在 `fetch` / `pull` / `push` 时更新，平时是死的。所以"本地领先 origin N 个提交"的准确含义是「本机比**上次联网时看到的**远端多 N 个」，不是实时对比。向用户汇报时别把它说成"远端就是这样"。

**默认分支叫什么因项目而异**（`master` 是旧默认，`main` 是 GitHub 2020 年后的默认）。本文命令统一用 `$MAIN`，照抄前先取值：

```bash
MAIN=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')
MAIN=${MAIN:-main}
echo "本项目默认分支：$MAIN"
```

---

## 一、什么时候必须建分支

判断口径只有一句：**这次改动有可能让 `pytest` 变红吗？** 会 → 建分支。

| 场景 | 建分支 | 分支名 |
|---|:---:|---|
| 修 bug（单个或一批） | 必须 | `fix/<主题>-<YYYY-MM-DD>` |
| 加功能 | 必须 | `feat/<主题>` |
| 重构 / 改架构 | 必须 | `refactor/<主题>` |
| 只改文档、注释、CHANGELOG | 不必 | 直接默认分支 |
| 回填 commit hash 这类收尾 | 不必 | 直接默认分支 |
| 只读探查、跑测试、跑 lint | 无所谓 | — |

分支名里的日期写**绝对日期**（`fix/pi-review-2026-08-20`），别写"今天""本周"。一批相关改动共用一条分支，不要一个 bug 一条分支——批次的意义是"一起验证、一起合入"。

---

## 二、六步流程（可直接照抄）

```bash
# 0. 取默认分支名 + 确认起点：工作区干净、在默认分支、与远端同步
MAIN=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')
MAIN=${MAIN:-main}
git status --short          # 应为空
git switch "$MAIN" && git pull

# 1. 建分支
git switch -c fix/<主题>-<YYYY-MM-DD>

# 2~3. 改代码 → 每批跑门禁 → 提交（循环，一批一个主题）
#    门禁照抄项目 CI 的口径，别自创。例（Python 项目）：
python -m ruff check src tests && python -m mypy src && python -m pytest -q
git add -A && git commit -F -   # 提交信息格式见 coding-standards §5.1

# 4. 合入默认分支：优先快进
git switch "$MAIN"
git merge --ff-only fix/<主题>-<YYYY-MM-DD>

# 5. 合后在默认分支上再跑一次门禁，然后 push
python -m pytest -q
git push origin "$MAIN"

# 6. 删分支（远端那条要先问用户）
git branch -d fix/<主题>-<YYYY-MM-DD>
git push origin --delete fix/<主题>-<YYYY-MM-DD>
```

**每批提交都要能独立通过门禁。** 不允许"这批先提交、下批再修好"——那样一旦中途停工，分支上就留了个红的提交，回头没人敢挑着合。

---

## 三、四条硬要求

1. **绝不 squash、绝不 rebase 已提交的批次。**
   CHANGELOG 和架构文档里会引用 commit hash（`- **commit**：\`787091a\``）。squash/rebase 会重写 hash，把这些引用全变成死链，而且没有任何报错提醒你。合并只用 `--ff-only`（直线历史，hash 原样保留）或 `--no-ff`（想留一个合并节点时）。
2. **push 前查机密。** 两条命令，缺一不可：
   ```bash
   git ls-files | grep -i "keys.yaml\|secrets\|\.env"          # 机密文件是否被误跟踪，应为空
   git log -p "origin/$MAIN..HEAD" | grep -nE "sk-[A-Za-z0-9_-]{20,}"  # 真 key 是否进了 diff（占位符除外）
   ```
   命中 `*.example` / `*.template` 这类模板文件不算问题，但要**打开确认里面只有占位符**，别凭文件名放过。
3. **每批提交后，向用户报当前分支 + 默认分支落后几个提交。** 一句话就够：「已提交到 `fix/xxx`（`main` 还停在 `abc1234`，落后 3 个）」。不报会出现下面第四节第一条那个坑。
4. **合并前分支上全绿，合并后默认分支上再跑一次。** 快进合并理论上是同一棵树，但一次 `pytest` 很便宜，而"默认分支是红的"这件事很贵。

---

## 四、常见坑

| 坑 | 症状 | 对策 |
|---|---|---|
| 全程在分支上工作却没说 | 用户："这工程不是只有一个分支吗？没合是怎么没合？" | 硬要求 3：每批提交后报分支状态 |
| 把 `origin/main` 当成远端实况 | 汇报"远端是 X"，其实那是上次 fetch 的快照 | 见 §〇；不确定就先 `git fetch` 再说 |
| squash/rebase 换掉 hash | CHANGELOG 里的 hash 全成死链，无报错 | 只用 `--ff-only` / `--no-ff` |
| 分支存在期间默认分支上又有了新提交 | `--ff-only` 失败 | 改用 `git merge --no-ff`，或先把默认分支合进分支解冲突再合回去 |
| 远端分支删除被权限拦 | 工具报「deletes a remote branch…requires the user to name it」 | 合并前就问一句"合完删远端分支吗"，一次性拿到授权 |
| Windows 上一堆 CRLF 警告 | `warning: LF will be replaced by CRLF` | 无害，忽略，别为它改文件 |
| 分支合了但忘 push | 本地领先远端，别的机器拉不到；订阅远端的自动部署/CI 也不会动 | 第 5 步和合并绑定，不拆开做 |
| 改默认分支名 | 订阅它的 CI 触发条件、平台部署分支设置会一起断 | 别为"看着顺眼"改名；真要改先清点所有订阅方 |

---

## 五、完成标准（Definition of Done）

一批改动"做完了"必须同时满足：

- [ ] 门禁三关在默认分支上全绿（照 CI 口径）
- [ ] CHANGELOG 有对应条目：做了什么 / 为什么 / 涉及文件 / 验证方式 / commit hash
- [ ] hash 已回填（最后一条允许写"见本条对应提交"，下次提交时补）
- [ ] 顶层架构有变动的话，架构文档同期更新（不是事后补）
- [ ] 机密预检两条命令都过
- [ ] `git branch -vv` 显示本地与 `origin/<默认分支>` 一致
- [ ] 分支已删除，或明确说明为什么保留
- [ ] 向用户报了最终 hash 和测试数（`105 passed（103→105）`）
- [ ] **push 是否已做要说清**：只提交未推送时，远端 CI 与平台自动部署都还没跑过，别把"本地全绿"说成"CI 已绿"

---

## 六、与 coding-standards 的关系

本 skill 是 `coding-standards` §5.3「分支策略」的可执行展开。提交信息格式（Conventional Commits）仍以 `coding-standards` §5.1 为准，本文不重复。

---

## 变更记录

### 2026-08-20 建立
- **触发**：api-quota-manager 一批 5 处 bug 修复走了 `fix/pi-review-2026-08-20` 分支，合并时用户问"这个 Project 不是只有一个 master 吗？没合是怎么没合？"——暴露的不是流程错，是**沟通缺口**：我在分支上工作了整批，从没告诉用户 master 一步没动。
- **用户立规**：修问题都需要建 fix 分支，验证后统一提交到主干。
- **本次实测有效的细节**：`--ff-only` 保住了 CHANGELOG 里引用的 6 个 hash；机密预检确认 `config/keys.yaml` 从未被跟踪、diff 里只有模板占位符 `sk-xxxx`。

### 2026-08-20 去掉硬编码的 master，补术语辨析
- **触发**：本文原先通篇写 `master`，而 sp500-nasdaq100-gold-dca 用的是 `main`，照本文办事时得逐处换词，用户读起来对不上，问"能不能统一命名"。
- **判断**：真正的不一致在**本文档**，不在仓库。仓库用 `main` 是 GitHub 现行默认，且改仓库分支名要连带改 CI 触发条件与 Streamlit Cloud 后台的部署分支——后者在网页端、改错线上直接断，代价与收益完全不对称。故改文档、不改仓库。
- **改动**：正文一律说「默认分支」，命令用 `$MAIN` 并给出取值命令（`git symbolic-ref --short refs/remotes/origin/HEAD`）；新增 §〇 辨析 `main` / `origin` / `origin/main` 三者——用户混的其实是这三个的角色，而改名并不能消除它们。
- **顺带补进来的两条实战教训**：机密预检命中 `*.example` 要打开看过再放行，别凭文件名放过；DoD 增加"push 做没做要说清"，因为只提交不推送时远端 CI 与平台自动部署一步都不会动，很容易被说成"CI 已绿"。
