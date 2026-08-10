# Generation G3 legacy cleanup

## 已由代码和 caller scan 验证的事实

- `debug.py` 只有 obsolete hard-coded checkpoint load 和 `print(0)`，无 assertion、输出资产或 caller。
- `diffusion_mdlm.py` 只被 `main.py` import，但没有任何 symbol 被使用。它与 MDLM upstream runtime
  `diffusion.py` 只有三个 text hunks；其中唯一可能影响模型的 tokenizer-derived vocabulary 已存在于当前
  Generation `diffusion.py`。ApexOracle sampler 主路径只使用后者。
- 13 个 `mol_generate_gpu_*` 共含 213 条 active commands，其中 198 个 normalized `strain × length` jobs；
  三个 `11775` launchers byte-identical，两个 `47085` launchers byte-identical。四个 `temp_Ben_gpu_*` 只是将
  其中六个 launcher 串起来。
- 在 Generation、Core 和 MDLM 的 tracked source/docs 中，没有发现上述 debug/duplicate/launcher 的 live
  runtime consumer。

## Canonical replacement

通用多任务入口为：

```bash
python scripts/reproduce/run_mic_peptide_grid.py \
  --job-manifest jobs.csv \
  --mdlm-root /path/to/ApexOracle-MDLM \
  --core-root /path/to/ApexOracle-Core \
  --output-root /path/to/new-grid-run \
  --confirm-experimental-extension
```

CSV 必须包含 `job_id,strain,target_length,device`；可选列为 `global_batch_size,num_sample_batches`。同一 device
内顺序运行，不同 device queue 并行；每个 job 使用 G2 的 portable MIC+peptide launcher，并拥有独立且必须
尚不存在的输出目录。grid 明确标为 experimental extension，不得冒充 frozen paper run。

## 恢复

删除的完整 source 继续由 annotated tag 恢复，例如：

```bash
git show legacy-code-snapshot-2026-08-10:diffusion_mdlm.py
git show legacy-code-snapshot-2026-08-10:scripts/mol_generate_gpu_00_11775.sh
```

所有 source hashes、历史 active grids 和删除 gate 见
`reproducibility/g3_legacy_cleanup.json`。ignored outputs、checkpoint、cache 和数据均未移动或删除。
