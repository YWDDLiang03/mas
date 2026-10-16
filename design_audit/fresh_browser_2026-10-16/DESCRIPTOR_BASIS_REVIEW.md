# RDKit 描述符来源分类与版本修正审阅

结论：本轮启用的 logP、PAINS_alert、BRENK_alert、NIH_alert 可按其实际生成路径标为 database_entry / derived。它们由 RDKit 对已有结构计算，不是 ADMET 神经网络 ensemble 的输出，也不是实验测量。其余训练 ADMET 端点继续保持 model_prediction / predicted。该判断依据算法实现，与候选排名无关。

## 核验来源

本机没有安装 admet_ai。本次读取与历史缓存声明版本一致的 [ADMET-AI 2.0.1 官方发行包](https://pypi.org/project/admet-ai/2.0.1/)，核对 PyPI SHA256 后只提取 Python 源码，没有安装包、导入模型、运行预测或重算描述符。

- 官方 wheel SHA256：fef3527f637abb00d272cf824e8eef0136fe31ebde6c56881f1a8c02c0417806。
- 源码 manifest：var/fresh-browser-20261016/descriptor-source-proof/distribution-source-manifest.json，固定每个实际提取文件的路径和 SHA256。
- admet_ai/physchem.py SHA256：f2e7cadcc73cfd0d47a4122f9131bdb1ea0f9fc0ba83f0a562bfec6966cec1e6。
- admet_ai/admet_model.py SHA256：70a0bd4687f0d897485584a4314c6c254dd1d721228002d2c458131d66e5aedd。

代码位于上述 descriptor-source-proof/admet_ai/ 目录。仓库的 [physchem.py](https://github.com/swansonk14/admet_ai/blob/main/admet_ai/physchem.py) 可用于导航，版本依据以校验过的 2.0.1 发行源码为准。

| 字段 | 实际方法 | 语义 | 源码位置 |
|---|---|---|---|
| logP | rdkit.Chem.Crippen.MolLogP | 从结构计算的 Crippen logP | physchem.py:5、79 |
| PAINS_alert | len(catalog_pains.GetMatches(mol)) | 匹配 PAINS 目录条目的个数 | physchem.py:19–21、32–38、86 |
| BRENK_alert | len(catalog_brenk.GetMatches(mol)) | 匹配 BRENK 目录条目的个数 | physchem.py:23–25、41–47、87 |
| NIH_alert | len(catalog_nih.GetMatches(mol)) | 匹配 NIH 目录条目的个数 | physchem.py:27–29、50–56、88 |

三个 alert 的输出是 count，不是 Boolean，也不是临床毒性概率。logP 是指定参数化算法的结构估计值，不能因此冒称实验测量或与所有 lipophilicity/logP 方法无条件互换。可复现性本身不是改为 derived 的依据：固定权重的神经网络也可以可复现，仍然是 predicted。这里区分的是源码明确分开的描述符计算路径与 ADMET 模型推理路径。

ADMETModel.predict 在 admet_model.py:169–187 分别调用物化计算和训练模型分支，再把结果按列拼接。_make_ensemble_predictions 在约 246–271 行通过训练模型推理后求 ensemble 均值，因此 HIA、BBB、CYP、Bioavailability、Clearance、DILI 等 TDC 字段仍是预测。是否可从已有缓存读取与它们的科学 basis 是两件事。

另有独立发现：Lipinski 在 physchem.py:59–73 返回满足四项规则的个数，当前一个未启用提议却写作 violation count。它保持 deferred，不在本次四项迁移内，不顺手改方向或启用。

## 四项精确变更

固定任务 task_01M52CBE5GYPK9F0MCZYBMPH84 的原 rules@v1 中，以下四条均是已启用、无 cutoff 的 ordering preference，单位分别为 log units / count，未声明 transform、bound support 或自定义权重：

- rule_predicted-logp-rdkit@v1
- rule_predicted-pains-alert-count@v1
- rule_predicted-brenk-alert-count@v1
- rule_predicted-nih-alert-count@v1

每项仅变更：

1. acceptable_value_sources：model_prediction 改为 database_entry。
2. acceptable_determination_bases：predicted 改为 derived。
3. 路由由 predicted_property_lookup / admet_prediction 改为 property_estimate / admet_computed_property，保留原 endpoint、inchikey 与其他参数。

独立 computed tool 由 provider 负责人定义为 tool_compute_admet_descriptors，implementation_version=admet-ai-2.0.1-rdkit-descriptor-projection-1，读取固定缓存，不新计算。原预测工具和原版本不变。新版本保留原名字、definition、direction、aggregation、unit、cutoff、quantity_id、claim/source refs。名字中的历史 Predicted 字样本次也不改。

## 可审核的执行入口

scripts/correct_descriptor_basis.py 默认只读。它限制为上述已核实端点以及原冻结启用的无 cutoff ordering preference，核对完整旧记录、源文件 hash、迁移脚本 hash、单位、原 policy 和全部科学字段。含明确 bounds/transform、争议、多种工具混合、自定义权重或其他政策的对象须另审，不由本脚本推测。

Dry run 已生成 var/fresh-browser-20261016/descriptor-basis-dry-run.json：4 items，excluded 为空，主库未变。

- 最终迁移脚本 SHA256：7992ff0b5d2777950416b498ae093196386630a2914974fe974124bd4d848a83。
- 最终计划 SHA256：d6f12aa13cf0296885a6a37df3c85c9d56c3aea1f02b98030d5aa4e122850ce0。

```powershell
.venv\Scripts\python.exe -B scripts\correct_descriptor_basis.py --store var\primary\store --task task_01M52CBE5GYPK9F0MCZYBMPH84 --rule-set rules@v1 --proof var\fresh-browser-20261016\descriptor-source-proof\distribution-source-manifest.json --out var\fresh-browser-20261016\descriptor-basis-dry-run.json
```

仅在主控明确执行时使用：

```powershell
.venv\Scripts\python.exe -B scripts\correct_descriptor_basis.py --store var\primary\store --apply --plan var\fresh-browser-20261016\descriptor-basis-dry-run.json --expect-plan-sha256 d6f12aa13cf0296885a6a37df3c85c9d56c3aea1f02b98030d5aa4e122850ce0 --out var\fresh-browser-20261016\descriptor-basis-applied.json
```

Apply 追加新 attribute/rule 版本并先建立 fresh review，再记录标准 machine_adjudication / decision.recorded。route=evidence_basis_corrected，actor 为 system，approval_kind=software_status，confirmed_by_a_person=false，附来源 hash、方法和逐字段 diff。它核验的是已证明的算法来源分类，没有伪造专家判断或新阈值批准。不会重写旧 snapshot、profile、规则、claim 或 source。之后仍须新 freeze/profile 并独立评估，不能把 snapshot1 当作新政策结果。

## 验证及边界

var/fresh-browser-20261016/descriptor-migration-temp-validation.json 记录临时 store 检查：4 个新版本、4 个系统核验 receipt、0 个人决策、旧 freeze 保留、新 freeze 可读；训练 BBB 项保持 v1/predicted；新 freeze 后重复 apply 幂等。没有在 primary 执行 apply。

derived 进入现行直接偏好覆盖率的依据是已固定的评分政策，不代表实验验证。缓存必须仍固定结构、包版本和来源 hash；本次没有补算任何缺失候选。修正是否带来足够覆盖及实际排名，以新的完整运行记录为准，当前不预写成功。

执行补记：主控于 2026-10-16T15:55Z 对上述精确计划执行了 apply，成功追加四个 v2 与系统核验记录。收据见 `audit/descriptor-basis-applied.json`。随后经浏览器启动独立的新评估 `run_01M52Q4VRB00T5Z3QJW08SSV96`，新冻结为 `rules@v2`；原结果继续保留。
