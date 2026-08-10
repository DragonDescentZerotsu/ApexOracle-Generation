"""Contracts between ApexOracle Generation and ApexOracle-MDLM."""

from __future__ import annotations

from pathlib import Path

import torch
from torch import nn

from apexoracle_mdlm.embeddings import (
    embedding_key_from_atcc_filename,
    embedding_key_from_text_filename,
)
from apexoracle_mdlm.models import FirstTokenCrossAttention, RegressionHead


ROOT = Path(__file__).resolve().parents[1]


class LegacyFirstTokenAttention(nn.Module):
    """Minimal frozen reference for the removed Generation copy."""

    def __init__(self, molecule_dim: int, condition_dim: int, heads: int) -> None:
        super().__init__()
        self.mol_to_genome_dim = nn.Linear(molecule_dim, condition_dim)
        self.key_value_projection = nn.Linear(condition_dim, condition_dim * 2)
        self.mha = nn.MultiheadAttention(condition_dim, heads, dropout=0.1)
        self.attn_norm = nn.LayerNorm(condition_dim)
        self.norm1 = nn.LayerNorm(condition_dim)
        self.ffn = nn.Sequential(
            nn.Linear(condition_dim, condition_dim),
            nn.GELU(),
            nn.Linear(condition_dim, condition_dim),
        )
        self.norm2 = nn.LayerNorm(condition_dim)

    def forward(
        self,
        molecule: torch.Tensor,
        condition: torch.Tensor,
        key_padding_mask: torch.Tensor,
    ) -> torch.Tensor:
        condition_dim = condition.shape[-1]
        query = self.mol_to_genome_dim(molecule)[:, None, :].transpose(0, 1)
        key_value = self.key_value_projection(
            condition.reshape(-1, condition_dim)
        ).reshape(condition.shape[0], condition.shape[1], -1)
        key_value = key_value.transpose(0, 1)
        query_norm = self.attn_norm(query.squeeze(0)).unsqueeze(0)
        attention, _ = self.mha(
            query_norm,
            key_value[:, :, :condition_dim],
            key_value[:, :, condition_dim:],
            key_padding_mask=key_padding_mask.to(torch.bool),
        )
        output = self.norm1(query.squeeze() + attention.squeeze())
        return self.norm2(output + self.ffn(output))


def test_generation_uses_mdlm_contracts_without_local_copy() -> None:
    source = (ROOT / "models" / "dit.py").read_text(encoding="utf-8")
    models_init = (ROOT / "models" / "__init__.py").read_text(encoding="utf-8")
    assert not (ROOT / "models" / "antibiotic_classifier.py").exists()
    assert "antibiotic_classifier" not in source
    assert "antibiotic_classifier" not in models_init
    assert source.count("FirstTokenCrossAttention(") == 6
    assert source.count("RegressionHead(") == 3
    assert source.count("load_atcc_embeddings(") == 6
    assert source.count("load_text_embeddings(") == 3


def test_embedding_filename_contracts_cover_generation_inputs() -> None:
    assert embedding_key_from_atcc_filename(
        "Escherichia_coli_ATCC_BAA_3170.pt"
    ) == "BAA-3170"
    assert embedding_key_from_atcc_filename("custom_strain.pt") == "custom_strain"
    assert embedding_key_from_text_filename("A～B^C.pt") == "A B/C"


def test_canonical_attention_matches_legacy_forward_and_input_gradient() -> None:
    torch.manual_seed(20260810)
    legacy = LegacyFirstTokenAttention(6, 8, 2).eval()
    canonical = FirstTokenCrossAttention(6, 8, 2, dropout=0.1).eval()
    canonical.load_state_dict(legacy.state_dict(), strict=True)

    molecule = torch.randn(2, 6)
    condition = torch.randn(2, 5, 8)
    mask = torch.zeros(2, 5)
    legacy_input = molecule.clone().requires_grad_(True)
    canonical_input = molecule.clone().requires_grad_(True)

    legacy_output = legacy(legacy_input, condition, mask)
    canonical_output = canonical(canonical_input, condition, mask)
    legacy_gradient = torch.autograd.grad(legacy_output.sum(), legacy_input)[0]
    canonical_gradient = torch.autograd.grad(
        canonical_output.sum(), canonical_input
    )[0]

    assert torch.equal(legacy_output, canonical_output)
    assert torch.equal(legacy_gradient, canonical_gradient)


def test_canonical_regression_head_keeps_generation_state_keys() -> None:
    head = RegressionHead(12, 3, 2, 1, 0.2)
    assert tuple(head.state_dict()) == (
        "dense_1.weight",
        "dense_1.bias",
        "dense_2.weight",
        "dense_2.bias",
        "out_proj.weight",
        "out_proj.bias",
    )
