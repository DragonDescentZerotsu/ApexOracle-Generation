# Generation legacy source 恢复说明

## 恢复点

- branch 创建基线：上游 `edb0f8c28b7caeb4ea7a06a2fee8d74ab6da1661`；
- source-only snapshot commit：`2368c25ce831c187e5b2699b85a6ae1a4cdca31a`；
- annotated tag：`legacy-code-snapshot-2026-08-10`；
- tag object：`c1e41c1719f31522b5619daf29ded76ceb703184`。

该 snapshot 收录本机当时的 11 个 tracked 修改、ApexOracle predictor/config、历史 launcher、debug 和
`diffusion_mdlm.py`。它刻意不收录 cache、outputs、checkpoint、训练数据和论文 PDF。

## 恢复命令

查看或导出单个旧文件：

```bash
git show legacy-code-snapshot-2026-08-10:models/antibiotic_classifier.py
git show legacy-code-snapshot-2026-08-10:models/dit.py > /tmp/legacy_models_dit.py
git show legacy-code-snapshot-2026-08-10:diffusion_mdlm.py
git show legacy-code-snapshot-2026-08-10:scripts/mol_generate_gpu_00_11775.sh
```

建立只读对照 worktree：

```bash
git worktree add --detach /tmp/apexoracle-generation-legacy \
  legacy-code-snapshot-2026-08-10
```

不得 reset 当前重构分支到该 tag，也不得把 snapshot 推送到上游 `kuleshov-group`。该 tag 已与 clean
`main` 显式推送到 `DragonDescentZerotsu/ApexOracle-Generation`，用于逐文件恢复而不是作为默认分支。

## 未纳入 Git 的资产

- `outputs/`：历史 Hydra config、logs、生成 token/SELFIES 和图片，约 13 GB；
- `cache_data/`：Hugging Face/datasets cache，约 5.8 GB；
- `papers/`：第三方论文 PDF，约 13 MB；
- 外部 MDLM/Core checkpoint、genome/text embeddings 和 tokenizer cache。

这些资产原地保留，重构没有移动或删除。
