"""Rung 1: char-level tokenizer + tiny GPT from scratch (FR-876 AC-04).

Readable-in-one-sitting nanoGPT-style decoder: token+position
embeddings, causal self-attention blocks, LM head. ~3-5M params at the
default training config.
"""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn

END_STRING = "<|end|>"


class CharTokenizer:
    def __init__(self, chars: list[str]):
        self.chars = chars
        self.stoi = {c: i for i, c in enumerate(chars)}
        self.itos = dict(enumerate(chars))

    @classmethod
    def fit(cls, texts: list[str]) -> CharTokenizer:
        return cls(sorted(set("".join(texts))))

    @property
    def vocab_size(self) -> int:
        return len(self.chars)

    def encode(self, text: str) -> list[int]:
        return [self.stoi[c] for c in text]

    def decode(self, ids: list[int]) -> str:
        return "".join(self.itos[i] for i in ids)


class Block(nn.Module):
    def __init__(self, n_embd: int, n_head: int):
        super().__init__()
        self.ln1 = nn.LayerNorm(n_embd)
        self.attn = nn.MultiheadAttention(n_embd, n_head, batch_first=True)
        self.ln2 = nn.LayerNorm(n_embd)
        self.mlp = nn.Sequential(
            nn.Linear(n_embd, 4 * n_embd), nn.GELU(), nn.Linear(4 * n_embd, n_embd)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        t = x.size(1)
        mask = torch.triu(
            torch.ones(t, t, dtype=torch.bool, device=x.device), diagonal=1
        )
        h = self.ln1(x)
        attn_out, _ = self.attn(h, h, h, attn_mask=mask, need_weights=False)
        x = x + attn_out
        return x + self.mlp(self.ln2(x))


class TinyGPT(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        n_layer: int = 4,
        n_head: int = 4,
        n_embd: int = 256,
        block_size: int = 512,
    ):
        super().__init__()
        self.block_size = block_size
        self.tok_emb = nn.Embedding(vocab_size, n_embd)
        self.pos_emb = nn.Embedding(block_size, n_embd)
        self.blocks = nn.ModuleList(Block(n_embd, n_head) for _ in range(n_layer))
        self.ln_f = nn.LayerNorm(n_embd)
        self.head = nn.Linear(n_embd, vocab_size, bias=False)

    def forward(
        self, idx: torch.Tensor, targets: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        t = idx.size(1)
        pos = torch.arange(t, device=idx.device)
        x = self.tok_emb(idx) + self.pos_emb(pos)
        for block in self.blocks:
            x = block(x)
        logits = self.head(self.ln_f(x))
        loss = None
        if targets is not None:
            loss = F.cross_entropy(
                logits.view(-1, logits.size(-1)), targets.reshape(-1)
            )
        return logits, loss

    @torch.no_grad()
    def sample(
        self,
        tokenizer: CharTokenizer,
        prefix: str,
        max_new_tokens: int = 900,
        temperature: float = 0.8,
        top_k: int = 40,
    ) -> tuple[str, bool]:
        """Returns (text_after_prefix, ended) — ended=False means the
        token budget elapsed before <|end|> (boundary shape-rejects)."""
        self.eval()
        device = next(self.parameters()).device
        idx = torch.tensor([tokenizer.encode(prefix)], device=device)
        for _ in range(max_new_tokens):
            logits, _ = self(idx[:, -self.block_size :])
            logits = logits[:, -1, :] / max(temperature, 1e-6)
            if top_k:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < v[:, [-1]]] = -float("inf")
            probs = F.softmax(logits, dim=-1)
            next_id = torch.multinomial(probs, num_samples=1)
            idx = torch.cat([idx, next_id], dim=1)
            text = tokenizer.decode(idx[0].tolist())[len(prefix) :]
            if text.endswith(END_STRING):
                return text[: -len(END_STRING)].strip(), True
        return tokenizer.decode(idx[0].tolist())[len(prefix) :].strip(), False
