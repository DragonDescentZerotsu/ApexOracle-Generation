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

### G2：论文入口和 portable config——待完成

- 从历史 resolved config 提取 paper-compatible preset，不直接把当前可变根配置称为论文终版；
- 将 checkpoint、embedding 和输出目录改为显式 CLI/config 参数或 super-repo asset resolver；
- 把论文 MIC+peptide 主路径与后续 synergy generation 分开标记；
- 新建只写全新目录的最小公开 smoke，禁止覆盖历史 `outputs/`。

### G3：clean module release——待完成

- 审计剩余 debug、重复 launcher、`diffusion_mdlm.py` 和上游/作者代码边界；
- 补 license/NOTICE、依赖和 fresh-clone smoke；
- 创建独立 `DragonDescentZerotsu/ApexOracle-Generation` remote 后才允许 push；
- 最后由 super-repo 固定 clean commit，不直接推上游 `origin`。

## 变更控制

- 每批只改变一个可验证 contract，不同时修改 sampler 数学和目录结构。
- legacy 删除必须有 snapshot、replacement、caller scan 和 parity/characterization evidence。
- 只显式 stage 文件；不得 `git add -A`，不得提交 ignored assets。
- GPU parity 使用空闲 GPU 和全新输出目录，并在文档中记录非确定性边界。
