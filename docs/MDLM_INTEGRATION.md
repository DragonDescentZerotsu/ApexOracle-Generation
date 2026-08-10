# ApexOracle-Generation 与 MDLM integration

## Canonical dependency

Generation 仍拥有 sampler、DLM generation backbone、remasking schedule 和输出逻辑。MDLM 只提供已经冻结的
downstream contracts：

- `FirstTokenCrossAttention`；
- `RegressionHead`；
- `load_atcc_embeddings`；
- `load_text_embeddings`。

开发环境应安装 `ApexOracle-MDLM`，或在 super-repo 中显式设置：

```bash
PYTHONPATH=/path/to/ApexOracle-MDLM/src python -m pytest -q \
  tests/test_apexoracle_mdlm_integration.py
```

Generation 不通过机器绝对路径寻找 MDLM source，也不再保留 `models/antibiotic_classifier.py` 的长期副本。

## 已验证事实

正式 noisy MIC、peptide 和 DLM checkpoints、BAA-3170 condition assets 下：

- fixed 2×64 token batch 的 legacy/canonical guidance output SHA-256 均为
  `72766f647e6495952edddcd75efecb81ebdca98ba35518f1e1fae514f72d316e`；
- 对全部 one-hot token 的 gradient SHA-256 均为
  `857abdf783f4d4d7eb308d30aa353267b615df445c98fe004128c5e96439619a`；
- genome/ATCC text/text-only keys 均为 `567/568/1079`；
- canonical 完成 BAA-3170、length 368、batch 2、256 steps、MIC/peptide guidance 15/15、
  `t_on/t_off=0.55/0.45` 的 full sampler；
- canonical 与第一次 legacy full run 的 resolved config SHA-256 均为
  `864a7513976852077626dcd4f320f0d5dbef522377c6515071478e190aebb080`；
- 四次 full runs（含删除 duplicate 后的最终 active tree）均为 2/2 complete、1/2 RDKit-valid，输出 schema 一致。

## Full sampler bitwise 边界

第一次 legacy、legacy repeat、canonical 迁移中间态和最终 no-copy active tree token JSON SHA-256 分别为：

- `af6837cc86099b1df2d55581cd18dfd7477b3951797f490dd54385bfcd2af1e6`；
- `c52e5ad7a8be60b35fb0d2a1c51be4359b841f15831466bfbeec8b35e95df63b`；
- `af272b6f6d2de63f5e8ae3efcdee1401d73d1028984bb541215bb3331e2767`。
- `4ed023ff4786e778cf988f4081d1ae6c7a31a34a35357bcaa6e17f4b2e98d13a`。

legacy 自身同 seed 不相同。启用 `torch.use_deterministic_algorithms(True)` 后，第一步 nucleus filtering 的
`cumsum_cuda_kernel` 报告没有 deterministic implementation 并停止。因此不能把最终随机 token 文件逐字节相同
写成 migration gate。当前可支持的结论是：canonical component forward/gradient exact，完整 256-step runtime、
配置和输出 contract 可运行；不能声称历史 sampler 在本硬件上同 seed bitwise reproducible。

完整 ignored logs 位于 `outputs/refactor_parity_20260810/`，compact machine-readable 记录位于
`reproducibility/full_sampler_mdlm_parity.json`。
