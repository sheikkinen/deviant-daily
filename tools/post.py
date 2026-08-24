"""Post markdown rendering (FR-781 file-hook shape; FR-826 step 6)."""

from __future__ import annotations

from tools.gate import PostDescription

# DA splits \n\n into <p> elements but the empty <p> collapses to zero
# height (live witness 2026-08-19) — NBSP on the separator line keeps the
# blank line visible.
PARA_SEP = "\n\u00a0\n"

# STYLE-CONTRACT.md §3 closing block — static, appended to every DA description
DESCRIPTION_FOOTER = (
    "\u2728 Visit also my DeviantArt Gallery! \u2728\n"
    "https://www.deviantart.com/sheikkinen/gallery"
    + PARA_SEP
    + "\U0001f4c2 Explore Premium Downloads, Galleries, Adoptables, or Commission "
    "Custom Work! The best of the best are reserved for Subscribers! Feel free "
    "to browse through my galleries, check out adoptable characters, or reach "
    "out for custom commissions. Let's bring a piece of my artistic vision "
    "into your world!"
    + PARA_SEP
    + "Thank you for your support and for being part of this creative journey! \U0001f389"
)


def render_artist_comments(post: PostDescription) -> str:
    """DA description: paragraphs, quote, footer (STYLE-CONTRACT §3)."""
    parts = list(post.paragraphs)
    if post.quote:
        parts.append(f"\u201c{post.quote}\u201d")
    parts.append(DESCRIPTION_FOOTER)
    return PARA_SEP.join(parts)


def render_post_md(
    post: PostDescription,
    prompt: str,
    model_name: str,
    da_url: str | None,
    date: str,
) -> str:
    """posts/YYYY-MM-DD.md content: title, paragraphs, quote, tags, provenance."""
    parts = [f"# {post.title}", ""]
    for para in post.paragraphs:
        parts += [para, ""]
    if post.quote:
        parts += [f"> {post.quote}", ""]
    parts += [" ".join(f"#{t}" for t in post.tags), ""]
    parts += [
        "---",
        "",
        f"- date: {date}",
        f"- model: {model_name}",
        f"- deviation: {da_url or 'N/A'}",
        f"- prompt: {prompt}",
        "",
    ]
    return "\n".join(parts)
