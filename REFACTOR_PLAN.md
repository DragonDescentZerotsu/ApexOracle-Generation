# ApexOracle-Generation 重构计划

## 目标与边界

本仓库作为统一 ApexOracle super-repo 的独立 `ApexOracle-Generation` submodule，保留上游离散扩散实现和
ApexOracle 的 SELFIES、MIC、peptide、remasking 及实验性 synergy guidance。重构不得改变论文采样协议、
checkpoint schema 或历史输出；数据、checkpoint、cache、Hydra outputs 和论文 PDF 不进入 Git。

## 当前状态（2026-08-10）

### G0：恢复点与血缘冻结——完成

- source-only snapshot commit：`2368c25ce831c187e5b2699b85a6ae1a4cdca31a`；
- annotated tag：`legacy-code-snapshot-2026-08-10`；
- snapshot 排除约 5.8 GB `cache_data/`、约 13 GB `outputs/`、checkpoint、数据和论文 PDF；
- 本机与 node002 的关键 source/config SHA-256 已分别冻结，确认两者不是同一个历史版本；
- 当前只有上游 `origin`，snapshot/tag 尚未 push，绝不能推到 `kuleshov-group`。

恢复方法与资产边界见 `docs/LEGACY_SNAPSHOT.md`，机器间血缘见
`reproducibility/generation_source_lineage.json`。

### G1：MDLM integration 与 sampler parity——完成

- `models/dit.py` 的三个 ApexOracle predictor 家族统一使用
  `apexoracle_mdlm.models.FirstTokenCrossAttention`、`RegressionHead` 与
  `apexoracle_mdlm.embeddings` loader；
- active tree 删除无其他 caller 的 1,839-line `models/antibiotic_classifier.py` duplicate，由 recovery tag 恢复；
- 正式 checkpoint、固定 2×64 token batch 下，legacy/canonical guidance output 与对全部 one-hot token 的
  input gradient SHA-256 均逐字节相同；
- canonical 使用论文参数完成 BAA-3170、length 368、2 samples、256-step full sampler；resolved config 与
  第一次 legacy run byte-identical；
- legacy 同 seed 两次 full sampler 自身产生不同 token SHA。PyTorch deterministic mode 在第一步 CUDA
  `cumsum` 明确失败，因此最终 token 文件不能作为 bitwise migration gate；这个限制不是重构引入的；
- 四次 non-deterministic full runs（含删除 duplicate 后的最终 active tree）均完成 2/2 complete、
  1/2 RDKit-valid，输出 schema 一致。精确证据见
  `docs/MDLM_INTEGRATION.md` 与 `reproducibility/full_sampler_mdlm_parity.json`。

验收命令：

```bash
PYTHONPATH=/path/to/ApexOracle-MDLM/src \
  python -m pytest -q tests/test_apexoracle_mdlm_integration.py
```

### G2：论文入口和 portable config——完成

- [x] 从历史 resolved config 提取 `configs/paper/mic_peptide.yaml`，不改写或冒充当前可变根配置；
- [x] `run_paper_mic_peptide.py` 从显式 Generation/MDLM/Core roots 解析 checkpoint/embedding，并拒绝复用
  已存在 output directory；所有图片、SELFIES、Hydra/manifest 输出限制在新 run directory；
- [x] preset 固定论文 MIC+peptide 主路径，synergy generation 继续是独立 experimental config；
- [x] Hydra dry-run 无 `/share/kuleshov`、`/data1` 或隐式历史 output path；9 项 focused tests 通过；
- [x] GPU 1 完成 1-sample、256-step portable smoke，exit code 0。token-level complete 为 1，结构过滤后
  0-row/0-image；只验证 runtime/output contract，不作为 candidate yield 证据。

协议、资产 hash、输出安全与 smoke hashes 见 `docs/PAPER_MIC_PEPTIDE_CONFIG.md` 和
`reproducibility/paper_mic_peptide_protocol.json`。

### G3：clean module release——进行中

- [x] 审计并清理无 caller 的 `debug.py`、unused `diffusion_mdlm.py`、13 个重复/硬编码 launcher 和四个
  shell orchestrators；完整 source 由 recovery tag 保留；
- [x] 用 `run_mic_peptide_grid.py` 统一未来多 strain/length/GPU 扫描，不保留项目专用命名；
- [x] 保留 upstream Apache-2.0 `LICENSE`，新增 `NOTICE` 与安装/外部资产边界；
- [x] 新增 release-tree audit，检查恢复点、active legacy、大文件和 canonical entry 中的作者绝对路径；
- [ ] 完成 clean commit、fresh-clone tests/dry-run；
- [ ] 创建独立 `DragonDescentZerotsu/ApexOracle-Generation` remote，只推 clean branch 与 recovery tag；
- [ ] 由 super-repo 固定最终 clean commit，不直接推上游 `origin`。

## 变更控制

- 每批只改变一个可验证 contract，不同时修改 sampler 数学和目录结构。
- legacy 删除必须有 snapshot、replacement、caller scan 和 parity/characterization evidence。
- 只显式 stage 文件；不得 `git add -A`，不得提交 ignored assets。
- GPU parity 使用空闲 GPU 和全新输出目录，并在文档中记录非确定性边界。
