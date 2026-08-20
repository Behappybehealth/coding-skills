# _archive — 已退役的 skill

这里的东西**只归档不删除，且不再更新**。放进来的判据只有一条：
它已经不再是活跃 skill（`~/.claude/skills` 下的联接已移除），但保留下来仍有参考价值。

归档 ≠ 删除的理由：skill 是自然语言指令，退役版本记录着"当时是怎么想的"，
而这层信息在 git diff 里读不出来——diff 只显示某段文字消失了，不显示它为什么曾经存在。

---

## investment-dca（2026-08-20 退役）

三资产定投建议的**早期自包含版本**：`scripts/dca_advisor.py`（754 行）自己抓 Yahoo、
自己算指标、自己记账，不依赖任何项目仓。

**为什么退役**：被 `projects/sp500-nasdaq100-gold-dca` 完全取代，而且两者并存是**有害的**，
不只是冗余——它们的中性权重是相反的：

| | investment-dca（本档） | sp500-nasdaq100-gold-dca（现行） |
|---|---|---|
| 中性权重 | 标普500 **45%** / 纳指100 **35%** / 黄金 20% | 标普500 **35%** / 纳指100 **45%** / 黄金 20% |
| 金额决定 | 四档离散（强烈建议／建议／试探／不买）× 用户输入金额 | 连续评分模型 → 部署系数 × 每日基准 |
| 预算模型 | 剩余预算 ÷ 自然月剩余**天数** | 可用池 ÷ 剩余**交易日**，跳过份额再平均，月末释放 |
| 计价 | 人民币，指数 proxy（`^GSPC`/`^NDX`/`GC=F`） | USDT 本位（`SPY`/`QQQ`/`XAUT`），双汇率折算 |
| 数据落点 | `~/.claude/investment-dca/`（在任何仓库之外） | 项目仓 `data/`，云端 Google Sheets 或本地 CSV |

两者的 `description` 又高度相似（都写着"为标普500、纳指100和黄金生成每日定投建议"），
所以一句「看看今天定投」有可能匹配到本档，给出与现行策略**主仓对调**的分配。
这是退役的直接动因：并存的风险不是"多一个选项"，是**静默给出错误分配**。

**退役怎么做的**：移除 `~/.claude/skills/investment-dca` 联接（用
`[System.IO.Directory]::Delete(path, $false)`，非递归，只删链接不碰目标），
再 `git mv` 进本目录。Claude Code 只扫 `~/.claude/skills`，联接一没它就不再是技能。

**没有孤立数据**：退役时确认 `~/.claude/investment-dca/` **不存在**——
这个 skill 从未产生过账本，所以归档不遗弃任何历史记录。真实定投记录一直在
`projects/sp500-nasdaq100-gold-dca` 那条链上（项目仓 `data/` 或云端表格）。

**万一要复活**（不建议）：重建联接即可，内容无需改动。
```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\investment-dca" -Target "X:\coding\skills\_archive\investment-dca"
```
复活前先想清楚上面那张表——两个 skill 同时活跃的问题会原样回来。
