# AGENTS.md

## 维护语言与当前阶段

- 本文件及后续维护说明应尽量使用中文；代码文件名、配置键、模型名、指标缩写和命令可保留英文。
- 新增结论时必须区分：**已由代码或日志验证的事实**、**根据现有证据作出的推断**、**仍待作者确认的事项**。
- **2026-08-10 作者已明确开始 Generation 重构：**先建立 source-only snapshot，再按可验证 contract 增量迁移；
  仍不得覆盖历史实验配置、结果、checkpoint、cache 或数据。当前计划、恢复点和验收状态记录在
  `REFACTOR_PLAN.md`、`docs/LEGACY_SNAPSHOT.md` 与 `docs/MDLM_INTEGRATION.md`。
- 除上述已授权重构范围外，不得修改 checkpoint、cache、历史运行输出或数据；新 smoke/parity 只能写入全新
  ignored 目录。

## 仓库定位

- 本仓库上游为 `kuleshov-group/discrete-diffusion-guidance`，许可证为 Apache-2.0；ApexOracle 的公开 fork
  为 `DragonDescentZerotsu/ApexOracle-Generation`，上游 remote 只用于读取和血缘核验。
- 上游项目实现离散扩散模型及多种 guidance 方法。本地工作树在此基础上加入了 ApexOracle 的 SELFIES 分子生成、MIC guidance、peptide guidance 和后续 synergy guidance。
- ApexOracle 主仓库不复制这里的生成实现；当前实现已作为独立模块维护，并由 super-repo 使用固定 commit
  的 submodule 引用。
- **当前公开边界：** clean implementation commit `80d9a2cf9b0921f29e4a44edf5557ccac39f5af9` 已由
  ApexOracle `v0.2.0` 固定；后续只允许经过测试的维护提交，不能把 upstream `main` 当作 ApexOracle
  论文生成实现。

## 当前 Git 状态与保护规则

### 已验证事实

- 重构开始时 `HEAD`、本地 `main` 和上游 `origin/main` 均为 commit
  `edb0f8c28b7caeb4ea7a06a2fee8d74ab6da1661`（`Clean up`）；这是历史基线，不是当前公开 fork 状态。
- 重构开始时存在的大量作者历史改动已由 source-only recovery tag、ledger 和 clean commits 接管；
  checkpoint、cache、outputs 与数据始终未进入 Git。
- `/data2/tianang/projects/discrete-diffusion-guidance` 与 `node002:/data1/tianang/Projects/discrete-diffusion-guidance` 的部分关键文件内容不同，说明两台机器保存了不同历史阶段。
- **2026-08-10 source-only 恢复点已建立：** commit
  `2368c25ce831c187e5b2699b85a6ae1a4cdca31a`、annotated tag
  `legacy-code-snapshot-2026-08-10`；cache、outputs、checkpoint、数据和论文 PDF 均未纳入。该 annotated
  tag 已推送 ApexOracle public fork；上游 `kuleshov-group` 未接收任何 ApexOracle commit。
- **2026-08-10 MDLM integration 已验证：**三个 ApexOracle predictor 家族改用
  `apexoracle_mdlm.models.FirstTokenCrossAttention`、`RegressionHead` 和 canonical embedding loaders；无 live
  caller 的 `models/antibiotic_classifier.py` duplicate 已由 snapshot 保存后从 active tree 删除。正式权重下
  fixed 2×64 token guidance forward 与对全部 one-hot token 的 gradient 均 `torch.equal`；canonical 完成
  BAA-3170、length 368、256 steps、15/15 guidance 的 full sampler。legacy 同 seed 两次 token SHA 不同，
  deterministic mode 又被 CUDA `cumsum` 明确拒绝，因此 final token byte equality 不是合法 gate。精确 hash、
  命令边界和解释见 `docs/MDLM_INTEGRATION.md` 与
  `reproducibility/full_sampler_mdlm_parity.json`。
- **2026-08-10 paper portable config：** canonical preset 为 `configs/paper/mic_peptide.yaml`；公开 launcher
  `scripts/reproduce/run_paper_mic_peptide.py` 必须显式接收 `--mdlm-root`、`--core-root` 和尚不存在的
  `--output-dir`，并可用 `--dry-run` 或 `--smoke`。它固定论文 256-step、15/15 guidance 与 remasking schedule，
  不启用 experimental synergy。GPU 1 的 1-sample smoke exit code 0，token-level complete 1 条、结构过滤后
  0-row/0-image；只能解释为 runtime/output contract 通过，不能解释为 candidate yield。验证命令：
  `PYTHONPATH=/path/to/ApexOracle-MDLM/src python -m pytest -q
  tests/test_apexoracle_mdlm_integration.py tests/test_paper_mic_peptide_config.py`。完整边界见
  `docs/PAPER_MIC_PEPTIDE_CONFIG.md` 与 `reproducibility/paper_mic_peptide_protocol.json`。
- **2026-08-10 G3 legacy cleanup：** `debug.py` 无 caller/产物，`diffusion_mdlm.py` 无 symbol consumer 且不含
  当前 `diffusion.py` 之外的 ApexOracle sampler 行为；13 个硬编码 `mol_generate_gpu_*` 与四个只负责串行调用的
  `temp_Ben_gpu_*` 已由通用 `scripts/reproduce/run_mic_peptide_grid.py` 替代。上述文件及先前删除的 duplicate
  全部保留在 annotated recovery tag，逐文件 SHA-256/caller/replacement gate 见
  `reproducibility/g3_legacy_cleanup.json`。验证命令为 `python scripts/audit/check_release_tree.py` 以及
  `PYTHONPATH=/path/to/ApexOracle-MDLM/src python -m pytest -q tests/test_apexoracle_mdlm_integration.py
  tests/test_paper_mic_peptide_config.py tests/test_generation_grid.py tests/test_release_tree.py`。
- **2026-08-10 Generation clean release：** public remote
  `https://github.com/DragonDescentZerotsu/ApexOracle-Generation.git` 已创建，默认分支为 `main`；G3 code commit
  `3a68dd0` 与 annotated recovery tag 已推送。fresh clone 的 release audit、全仓 14 tests 和双 strain
  resolved-config dry-run 均通过。`origin` 继续指向 `kuleshov-group`，严禁向其推送 ApexOracle commits。
- **2026-08-10 compact public generation assets：** Hugging Face
  `Kiria-Nozan/ApexOracle-Generation` revision `2fb1aa08187eaa359263be6c12c8a41868d8959c` 固定 inference-only
  DLM/noisy-MIC/noisy-peptide checkpoints 与 BAA-3170 genome/text；合计 4,059,311,443 bytes。canonical launcher
  新增 `--asset-root`，只允许该 compact bundle 用于 BAA-3170；完整 paper profile 保持全 condition banks。
  11 focused tests、全部资产 SHA-256、resolved dry-run 和真实 H100 256-step smoke 均通过，得到 1 complete
  SELFIES、exit 0；不得解释为 deterministic generation、candidate yield 或实验 activity。

### 操作约束

- 不得对本工作树执行 `git reset --hard`、`git clean`、批量格式化或覆盖式同步。
- 不得把现有 modified/untracked 文件当作本次审计新产生的内容，也不得擅自删除。
- `outputs/`、`cache_data/`、模型权重和生成分子文件均不得提交到 Git。
- 任何未来清理都应先建立文件清单、SHA-256 清单和恢复点，再逐项迁移；不得以 upstream `HEAD` 覆盖本地实现。

## ApexOracle 生成主流程

论文相关的主要调用链为：

```text
Hydra 配置
  -> main.py::guide_sample_AMP
  -> diffusion.py::Diffusion.sample_AMP
  -> classifier.py::Classifier
  -> models/dit.py::DIT_Reg_Cls_AMP
  -> diffusion.py::_cbg_denoise_antibiotic_remdm_loop
  -> eval_utils.py（SELFIES 校验、RDKit 转换、图片和文本输出）
```

### 各文件功能

- `main.py`
  - Hydra 入口。
  - 上游训练路径由 `_train` 等函数负责。
  - ApexOracle 路径由 `guide_sample_AMP` 负责：加载 DLM checkpoint，恢复 `models.dit.DIT`，调用 `sample_AMP`，验证和解码 SELFIES，并保存结果。
  - 当前 ApexOracle 路径直接使用 Hugging Face 的 `ibm-research/materials.selfies-ted` tokenizer。

- `diffusion.py`
  - 上游离散扩散训练、采样和 guidance 的核心实现。
  - `sample_AMP` 创建 guidance predictor，并进入扩散采样。
  - `_cbg_denoise_antibiotic_remdm_loop` 是论文三阶段 MIC/peptide guidance 与 remasking 的关键实现。
  - 文件还包含 `_cbg_denoise_antibiotic`、`_nos_denoise_AMP` 等其他或历史方法，不能自动视为论文终版。

- `classifier.py`
  - 将 guidance predictor 包装为统一的 Lightning classifier 接口。
  - 根据 `classifier_backbone` 选择通用分类器、MIC+peptide predictor 或后续 synergy predictor。
  - 历史函数名中存在 `guaidance` 拼写，不得在没有行为测试时只为改名而改动调用链。

- `models/dit.py`
  - 包含上游 DIT backbone。
  - `DIT_Reg_Cls_AMP` 加载 noisy MIC regressor、peptide classifier、genome embedding 和 strain text embedding，是论文 MIC+peptide guidance 的主要 predictor。
  - `DIT_Syn_Cls_Pep_Cls_AMP` 属于后续 synergy-guided generation 路径，不应混入当前论文 MIC guidance 的复现说明。

- `apexoracle_mdlm.models`（外部 module）
  - 提供 Generation predictor 使用的 canonical genome/text fusion、attention 和 regression heads。
  - 旧 `models/antibiotic_classifier.py` duplicate 已完成正式 checkpoint output/gradient parity 后从 active tree
    删除，仍可由 recovery tag 恢复。

- `eval_utils.py`
  - 负责 SELFIES 有效性检查、RDKit molecule 构建和绘图，以及生成字符串保存。
  - 输出文件名编码 strain、target MIC、target length 和 noise/clean 等条件。

- `configs/config.yaml`
  - 当前本地工作配置，包含生成 checkpoint、target strain、长度、采样步数和 remasking 参数等绝对路径。
  - 它是可变的工作配置，不是论文终版配置的可信冻结副本。

- `configs/config_mdlm_cls.yaml`
  - 为定制 DLM/DIT 架构恢复模型结构的配置。

- `configs/guidance/cbg_antibiotic.yaml`
  - MIC+peptide CBG/remasking guidance 的工作配置。
  - 当前本机版本的 `gamma_l/gamma_s` 为 `10/10`，与论文终版 `15/15` 不同，因此不得直接用当前文件声称复现论文。

- `configs/guidance/cbg_synergy.yaml`
  - 后续 synergy guidance 配置，不属于论文当前报告的 MIC+peptide guided generation 主协议。

- `configs/guidance/nos_antibiotic.yaml`
  - NOS 风格的替代或探索性 guidance 配置，不是已确认的论文终版入口。

- `scripts/reproduce/run_paper_mic_peptide.py`
  - frozen paper MIC+peptide preset 的 portable launcher；只接收显式 module roots 和全新 output directory。

- `scripts/reproduce/run_mic_peptide_grid.py`
  - 论文后通用 `strain × length × device` CSV grid；同一 device 顺序、不同 device 并行，每个 job 独立输出。
  - 必须显式传 `--confirm-experimental-extension`，不得把 grid 冒充 frozen paper run。

- `dataloader.py`、`noise_schedule.py`、`tokenizer.py`
  - 主要是上游数据、噪声日程和 tokenizer 支持代码。ApexOracle 的当前主路径使用 SELFIES-TED tokenizer，而不是据此断言这些文件全部无关。

- `models/dimamba.py`、`models/unet.py`、`guidance_eval/`、`custom_datasets/`、上游 notebooks 和通用 scripts
  - 属于上游替代 backbone、数据集或评估基础设施；不是已确认的论文 ApexOracle 生成主调用链。

- `outputs/`
  - Hydra resolved config、日志、生成 SELFIES 文本和分子图片等历史运行证据。只读保留，不能原地重跑覆盖。

- `cache_data/`
  - Hugging Face/datasets 等本地 cache，不是源代码，也不是应发布的数据资产。

## 论文生成协议

以下参数已由论文 Methods 与历史 resolved Hydra config 交叉验证：

| 参数 | 论文协议 |
| --- | --- |
| 扩散步数 | `256` |
| target MIC | `1` |
| Gaussian sigma | 从 `0.5` 线性降至 `0.2` |
| `t_on` | `0.55` |
| `t_off` | `0.45` |
| `alpha(t_on)` | `0.5` |
| 中间阶段 remasking rate | `0.02` |
| 第一、三阶段 | `gamma_MIC=15`，`gamma_peptide=0` |
| 第二阶段 | `gamma_MIC=0`，`gamma_peptide=15` |
| guidance predictor 训练输入 | 加噪序列 |

`_cbg_denoise_antibiotic_remdm_loop` 的阶段行为为：

1. `time > t_on`：只使用 MIC regressor。
2. `t_off < time <= t_on`：执行 remasking，只使用 peptide classifier。
3. `time <= t_off`：再次只使用 MIC regressor。

上述为论文协议和实现结构的对应关系；不代表当前根配置可直接无修改复现该运行。

## 已定位的论文相关历史运行证据

### Guided 运行

- 路径：`outputs/qm9/2025.06.11/235615/.hydra/config.yaml`
- SHA-256：`d292b32c0b3674cd1a60d61802b228b5bfde3aef3e9a18dcdf0c32fa94917d45`
- 已验证参数包括 BAA-3170、target MIC `1`、length `368`、`256` steps、`0.5 -> 0.2`、`t_on=0.55`、`t_off=0.45`、`alpha_on=0.5`、remasking `0.02` 和 guidance strength `15/15`。

### 历史上被绘图脚本称为 “Unconditional” 的运行

- 路径：`outputs/qm9/2025.06.16/111320/.hydra/config.yaml`
- SHA-256：`27fa7b946bc433fb98e8588658d8f9378f147e35eaba17722e9be78132627465`
- target MIC 为 `1000`，但 resolved config 仍指定了 `cbg_antibiotic` guidance method 和 guidance checkpoint。
- **仍待作者确认：**该基线是否在算法意义上真正 unguided。现有证据只支持“历史绘图代码把 target MIC 1000 组标为 Unconditional”，不支持把它无条件描述成完全没有 guidance 的采样。

## 权重与数据依赖

权重二进制必须保持外部只读，不进入 Git。已核验的关键文件为：

| 用途 | 路径 | SHA-256 |
| --- | --- | --- |
| DLM generator | `/data2/tianang/projects/mdlm/Checkpoints_fangping/last_reg_v1.ckpt` | `a509b94e3780a0848b3f799ccfe754ed07524169973b08d85fdbc597f0592615` |
| noisy MIC guidance | `/data2/tianang/projects/Synergy/Checkpoints/genome_text_learnable_emb/guidance_regressor_pad_no_mask/noise_guidance_best_R2_all_peptide_epoch_100.pth` | `f24faf670b804edebbd4d6530a42c1351b62040046e14ebded67335aefc9c3a4` |
| noisy peptide classifier | `/data2/tianang/projects/mdlm/cls-guide-pad-no-mask-checkpoints/epoch-epoch=1-step-step=134000-train_loss-train_loss=0.008.ckpt` | `40f638ca5668f20a641a538035015b1741ab69cded300cba27f7148cc291945b` |
| fixed-`t=1e-3` MIC reporting model | `/data2/tianang/projects/Synergy/Checkpoints/genome_text_learnable_emb/guidance_regressor_non_pad_t1e-3/mic_candidate_scorer_all_peptide_non_pad_t1e-3_epoch13.pth` | `c0d7c2be49ef179a25a19dcd9c54c592c282b6961e51aff60e95fabc13786802` |

已验证的设计边界：生成 guidance 使用 random-time noisy predictor；Mac 上的历史最终评估脚本使用
fixed-`t=1e-3` MIC model 做生成后预测。这两种 predictor 的用途不能混写。旧资产名中的 `clean`/`noise`
只是历史命名，canonical 路径已按真实 protocol 修正；旧名仅由 MDLM provenance 保留。

Genome embedding 和 strain text embedding 当前通过 Synergy 路径读取。它们是输入资产，不得由本仓库的清理过程重新计算、覆盖或就地更名。

## 本机、node002 与 Mac 的证据边界

- 本机和 node002 的仓库都基于 upstream commit `edb0f8c...`，但 `main.py`、`diffusion.py`、`models/dit.py`、配置和部分 predictor 代码并不完全一致。
- node002 的 `cbg_antibiotic.yaml` 保留了 `15/15` guidance strength；本机当前文件为 `10/10`。历史 resolved config 与论文均支持 `15/15` 是论文报告值。
- Mac 历史脚本 `/Users/kirianozan/Documents/Study/Penn/projects/ApexOracle/mdlm/judge_generated_mols_MIC.py` 读取 `generated_mol_SELFIES-new-test`，用 clean 13-epoch MIC checkpoint 比较 target MIC `1` 和 `1000` 两组。
- **根据现有证据作出的推断：**BAA-3170 与 BAA-3197 的早期生成脚本和输出最接近论文阶段；当前本机多菌株批量生成脚本多为论文后扩展。
- **仍待作者确认：**最终 Fig. 3 的每个绘图点与具体生成文本、运行目录和随机运行之间尚无完整 manifest，不能仅凭修改时间建立精确血缘。

## 论文实验与论文后扩展的边界

### 论文主路径

- DLM SELFIES generator。
- strain-conditioned noisy MIC guidance。
- noisy peptide/non-peptide guidance。
- 256-step 三阶段 CBG/remasking 协议。
- BAA-3170/BAA-3197 相关早期运行和后续 fixed-`t=1e-3` MIC model 评估。

### 论文后或尚未确认的扩展

- `cbg_synergy.yaml`、`DIT_Syn_Cls_Pep_Cls_AMP` 和 synergy-guided generation。
- recovery tag 中面向更多 BS/ATCC/PAO1/PA14 strain 的历史硬编码批量生成；active tree 统一使用 CSV grid。
- Mac 上后续大型 generation benchmark 目录或 CSV。

这些代码可以保留在外部工具仓库中，但未来发布时应与论文主复现入口分开标注。

## 环境与运行注意事项

- `requirements.yaml` 记录的上游环境名为 `discdiff`，包括 Python 3.9、PyTorch 2.2.2、CUDA 12.4、Lightning 2.2.1、Transformers 4.38.2、RDKit、SELFIES、flash-attn 和 mamba 等依赖。
- 该文件描述的是历史环境约束，不代表当前机器已有一个逐项完全一致且已验证的可复现环境。
- 生成过程会同时加载多个大 checkpoint，GPU 显存和主机内存需求较高。不得把导入成功当成端到端验证。
- 历史 root config 仍包含机器绝对路径，仅作 upstream/legacy workspace 兼容；canonical paper preset 和两个
  release launchers 不含作者机器绝对路径。
- MDLM integration 的开发/测试入口为
  `PYTHONPATH=/path/to/ApexOracle-MDLM/src python -m pytest -q tests/test_apexoracle_mdlm_integration.py`；super-repo
  负责固定 MDLM submodule commit 并安装该 package。Generation 不通过硬编码绝对路径查找 MDLM source。
- 历史 YAML 中可能存在 `Ture` 等拼写，源码中也有 `guaidance` 等历史命名。任何修正都必须先冻结 resolved config 和行为测试，不能静默“清理”。

## 当前发布验收标准

1. `legacy-code-snapshot-2026-08-10` 必须可恢复所有被清理 source；不得删除或覆盖该 tag。
2. Canonical paper launcher 必须保持 256-step、15/15 guidance 与 remasking schedule，且拒绝复用 output。
3. Generic grid 必须继续调用 canonical launcher；未来 case-study 只把 job/data lineage 写进外部 manifest，不能
   复制新的项目专用 launcher 到 active tree。
4. `python scripts/audit/check_release_tree.py`、focused tests 和 fresh-clone dry-run 必须通过。
5. checkpoint、embedding、outputs、cache、论文 PDF 和项目数据不进入 Git；只将 clean branch/tag 推到
   ApexOracle 自有 remote，永远不推上游 `kuleshov-group`。
