# Partial sweep 既有描述符证据诊断

结论：不是所有 PubChem 计算描述符缺失。MW 的问题是注册到了预测端点，并仅接受预测依据；
现有 PubChem replay 连接正常，已保存确切 MolecularWeight，允许在新版本标准、新复核与新冻结下复用。

本报告只含按规则汇总的统计；不展示候选个体、名次或对照案例。源库以只读模式打开，
未运行 provider、网络请求、新 ADMET 计算或科研工作流，未修改 src、primary 或缓存。

## 已保存 partial 单元

Run: `run_01M51MS4KW71HX2FEMTPJ01JHA`。

共 1,177 个匿名成员、29 条规则、34,131 个已保存单元。

其中 1,176 个成员已保存全部 29 条，另 1 个成员保存了 27 条；该 partial 仍缺最后 2 个单元，不能称整个评估已完成。

| 规则 | pass | fail | available | unknown_missing |
| --- | ---: | ---: | ---: | ---: |
| `rule_computed-lipophilicity-xlogp@v1` | 947 | 143 | 0 | 87 |
| `rule_csf1r-curated-potency@v1` | 0 | 0 | 13 | 1164 |
| `rule_documented-oral-administration@v1` | 450 | 0 | 0 | 727 |
| `rule_fgfr1-curated-potency@v1` | 0 | 0 | 10 | 1167 |
| `rule_hydrogen-bond-acceptors-lipinski@v1` | 1049 | 87 | 0 | 41 |
| `rule_hydrogen-bond-donors-lipinski@v1` | 1089 | 47 | 0 | 41 |
| `rule_lipophilicity-logp-optimal-band@v1` | 253 | 837 | 0 | 87 |
| `rule_lipophilicity-logp@v1` | 0 | 0 | 0 | 1177 |
| `rule_measured-cyp3a4-interaction-liability@v1` | 0 | 0 | 0 | 1177 |
| `rule_measured-human-clearance@v1` | 0 | 0 | 0 | 1177 |
| `rule_measured-human-oral-bioavailability-f@v1` | 0 | 0 | 0 | 1177 |
| `rule_measured-human-plasma-protein-binding@v1` | 0 | 0 | 0 | 1177 |
| `rule_measured-oral-bioavailability-f-any-species@v1` | 0 | 0 | 0 | 1177 |
| `rule_molecular-weight-oral-absorption@v1` | 0 | 0 | 0 | 1177 |
| `rule_predicted-acute-toxicity-ld50@v2` | 0 | 0 | 0 | 1177 |
| `rule_predicted-aqueous-solubility@v1` | 0 | 0 | 1177 | 0 |
| `rule_predicted-caco-2-permeability@v1` | 0 | 0 | 1177 | 0 |
| `rule_predicted-cyp3a4-substrate-probability@v1` | 0 | 0 | 1177 | 0 |
| `rule_predicted-half-life@v1` | 0 | 0 | 0 | 1177 |
| `rule_predicted-human-intestinal-absorption-hia@v1` | 0 | 0 | 1177 | 0 |
| `rule_predicted-oral-bioavailability-ma@v1` | 0 | 0 | 1177 | 0 |
| `rule_predicted-pampa-permeability@v1` | 0 | 0 | 1177 | 0 |
| `rule_predicted-plasma-protein-binding-rate@v1` | 0 | 0 | 0 | 1177 |
| `rule_predicted-qed-drug-likeness@v1` | 0 | 0 | 0 | 1177 |
| `rule_rotatable-bonds-molecular-flexibility@v1` | 924 | 212 | 0 | 41 |
| `rule_topological-polar-surface-area-tpsa@v1` | 661 | 475 | 0 | 41 |
| `rule_vegfr1-curated-potency@v1` | 0 | 0 | 14 | 1163 |
| `rule_vegfr2-curated-potency@v1` | 0 | 0 | 31 | 1145 |
| `rule_vegfr3-curated-potency@v1` | 0 | 0 | 11 | 1165 |

所有 unknown_missing 原因均为“no admitted claim from an accepted source”，没有 tool_error。
完整原原因与搜寻路径在 diagnostic.json 中。MW 的路径只有 predicted_property_lookup；
HBA/HBD/TPSA/RB 的路径为 property_estimate，各自 1,136 有值、41 缺证。
XLogP 两条正确绑定规则各 1,090 有值、87 缺证，未用任何其他 logP 定义替代。

## 现有数值与固定来源证明

按原 first_source_then_first_event 顺序重建，只选择原 binding 指定的完成 source runs：

- PubChem descriptor projection 3,084 行，全部已有 MolecularWeight、TPSA、HBA、HBD、RB。
- 其中 MolecularWeight 全部能解析为有限正数；这里只校验保存值，不计算分子描述符。
- Projection entries digest 与原 binding 完全一致：
  `87cd7a51d407f4008c04b1a0fa89b2e76049ad058f76c18a45bfbc163b5926dc`。
- 在 partial 的 1,177 个匿名成员中，1,136 个按全部输入（除 property）精确匹配到保存行，
  且全部有 MolecularWeight；41 个没有精确行，继续保留未知。
- `universe_chembl.json` 只含 oral/parenteral/topical、警示、审批和撤市等字段，
  未保存这些描述符，因此不能把该文件当成 MW 数值来源。

## 最小修复路线

由根任务使用版本化修订，把 MW 的证据请求改为
`property_estimate / computed_property / property=MolecularWeight`、InChIKey 输入，
接受 `database_entry / derived`；保留单位、方向、predicate、cutoff 和 bound_support。
新复核与 strict freeze 决定是否启用。旧版本与本次缺证单元保留；新 MW 版本需重新形成对应单元，
其他确切未变条目的合法 partial 单元按既有续跑检查复用。

其余路线、缓存选择及排名口径不变，不将 XLogP、ALogP、RDKit logP 按名称近似替换。
本报告没有推断其他普遍缺证预测或临床量可以改用相近字段。

精确统计及 source run/digest 见 [diagnostic.json](diagnostic.json)。
只读复核脚本为 [diagnose_readonly.py](diagnose_readonly.py)。
