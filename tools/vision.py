"""Vision describe step (FR-826 step 3; FR-769/FR-781 precedent).

Sends the generated image + the original corpus prompt through an
anthropic vision model with structured output. The instruction text
lives in prompts/describe_post.yaml (committed style artifact); the
result is re-validated deterministically by tools.gate.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path

import yaml
from langchain_core.messages import HumanMessage
from yamlgraph.utils.llm_factory import create_llm

from tools.gate import PostDescription

logger = logging.getLogger(__name__)

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "describe_post.yaml"


def load_instruction() -> str:
    return yaml.safe_load(PROMPT_FILE.read_text())["template"]


def describe_image(image_path: str | Path, prompt_text: str, llm=None) -> dict:
    """Return raw dict for the gate; llm injectable for tests."""
    img_b64 = base64.b64encode(Path(image_path).read_bytes()).decode()
    instruction = load_instruction().replace("{original_prompt}", prompt_text)
    message = HumanMessage(
        content=[
            {"type": "text", "text": instruction},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
            },
        ]
    )
    model = llm or create_llm(provider="anthropic")
    structured = model.with_structured_output(PostDescription)
    result = structured.invoke([message])
    return result.model_dump()
