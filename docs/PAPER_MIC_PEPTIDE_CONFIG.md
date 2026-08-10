# ApexOracle 论文 MIC+peptide portable config

## 发布入口

Canonical launcher 为：

```bash
python scripts/reproduce/run_paper_mic_peptide.py \
  --mdlm-root /path/to/ApexOracle-MDLM \
  --core-root /path/to/ApexOracle-Core \
  --output-dir /path/to/new-run-YYYYMMDD-HHMMSS \
  --device 0
```

`--output-dir` 必须尚不存在。launcher 不接受历史 `outputs/` 作为隐式默认值，并将图片、SELFIES、Hydra
resolved config 和 `apexoracle_generation_run_manifest.json` 都限制在该新目录内。只做配置解析时加
`--dry-run`；最小 GPU smoke 加 `--smoke`，后者只将 global batch 和 batch count 改为 `1/1`，不改变 256-step
sampler、guidance strength 或 remasking schedule。

## 已由代码和历史配置验证的事实

- `configs/paper/mic_peptide.yaml` 从
  `outputs/qm9/2025.06.11/235615/.hydra/config.yaml` 提取；该历史文件 SHA-256 为
  `d292b32c...17d45`。
- 默认 preset 固定 seed 2、BAA-3170、length 368、target MIC 1、256 steps、global batch 50、10 batches、
  Gaussian sigma `0.5 -> 0.2`、`t_on/t_off=0.55/0.45`、remasking eta `0.02`、alpha `0.5` 和
  MIC/peptide guidance `15/15`。
- DLM、noisy MIC、noisy peptide checkpoint 路径分别从显式 MDLM/Core root 解析；genome/text embeddings
  从显式 Core root 解析。preset 本身不含作者机器绝对路径。
- `reproducibility/full_sampler_mdlm_parity.json` 已验证 canonical MDLM integration 完成同一 schedule 的
  256-step full sampler；legacy sampler 自身不具备同 seed bitwise determinism，因此最终 token byte equality
  不是发布 gate。
- portable launcher 已在 GPU 1 完成 `--smoke`：正式三类 checkpoint 与 condition assets 成功加载，1 条
  token-level complete SELFIES 完成 256 steps，进程 exit code 为 0。该随机样本未通过后续 RDKit/peptide
  filter，因此 canonical 文本为 0 rows、图片为 0；这验证 runtime/output contract，不验证 candidate yield、
  chemical validity rate 或 activity。

## 发布边界

这是论文 MIC+peptide 主路径，不包含 `cbg_synergy.yaml` 或 `DIT_Syn_Cls_Pep_Cls_AMP`。synergy generation
继续保留为明确标注的 experimental extension，不会由本 preset 隐式启用。

资产 hash、输出安全合同和协议数值的机器可读版本见
`reproducibility/paper_mic_peptide_protocol.json`。当前仓库仍只有上游 remote；在创建
`DragonDescentZerotsu/ApexOracle-Generation` 前，不得 push 此分支或 recovery tag。

## 论文后多菌株扫描

以后类似 peptide library、strain panel 或长度网格的扫描，不再复制按 GPU 命名的 shell scripts。先建立 CSV：

```csv
job_id,strain,target_length,device,global_batch_size,num_sample_batches
example_3170,BAA-3170,368,0,50,10
example_custom,ATCC-EXAMPLE,256,1,50,10
```

再运行：

```bash
python scripts/reproduce/run_mic_peptide_grid.py \
  --job-manifest jobs.csv \
  --mdlm-root /path/to/ApexOracle-MDLM \
  --core-root /path/to/ApexOracle-Core \
  --output-root /path/to/new-grid-run \
  --confirm-experimental-extension
```

同一 GPU 的 jobs 顺序运行，不同 GPU queues 并行。每个 job 仍调用本页的 canonical launcher，拥有独立的新
output directory，并记录 resolved command。任意非论文默认 strain 都必须显式给出 `target_length`；这个入口
只是一项通用实验能力，不能把未来的项目数据或结果混入本仓库。
