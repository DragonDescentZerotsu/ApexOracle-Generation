# Installation and module dependencies

## Source and license boundary

This repository retains the upstream Apache-2.0 `LICENSE`; ApexOracle modifications are distributed under that
repository-level license. `NOTICE` records the upstream source and the scope of the ApexOracle additions. External
checkpoints, datasets, tokenizers and the MDLM/Core modules are not relicensed or vendored here.

## Environment

The historical complete environment is recorded in `requirements.yaml`:

```bash
conda env create -f requirements.yaml
conda activate discdiff
```

The ApexOracle path additionally requires a source checkout of `ApexOracle-MDLM` and the external model/data assets
listed in `docs/PAPER_MIC_PEPTIDE_CONFIG.md`. The portable launcher adds `<mdlm-root>/src` to `PYTHONPATH`; it does not
copy MDLM code into this repository. `ApexOracle-Core` owns the condition embeddings and MIC guidance checkpoint.
The future ApexOracle super-repo is responsible for locking compatible commits of all three modules.

## Source-only validation

The tests that do not load the multi-GB model assets can be run with:

```bash
PYTHONPATH=/path/to/ApexOracle-MDLM/src \
  python -m pytest -q \
  tests/test_apexoracle_mdlm_integration.py \
  tests/test_paper_mic_peptide_config.py \
  tests/test_generation_grid.py
```

Run `python scripts/audit/check_release_tree.py` before publication. A real end-to-end launch additionally needs a
CUDA GPU and the three checkpoints whose SHA-256 values are frozen in
`reproducibility/paper_mic_peptide_protocol.json`.
