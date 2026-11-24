"""Conservative difficulty rubric for generated knowledge-check questions.

Original comprehensive packs contain no difficulty metadata. Previously every
generated question was unconditionally seeded as Easy, even when it requires
multiple calculations or advanced technical reasoning.

The item's explicit authored difficulty always wins. In the legacy packs,
questions are assessed by the task required (recognition, application or
multistep reasoning), not by subject alone or an arbitrary quota. These
fallback rules are intentionally conservative and can be replaced per-item
with a curated `difficulty` value in a source pack.
"""
from __future__ import annotations

import re

LEVELS = {"Beginner", "Easy", "Medium", "Hard"}

# Named families in the generated quantitative pack. Each family uses the
# same solution method, with varying input values, so its tier is stable.
QUANT_BEGINNER = (
    "array left-rotation", "fifo after dequeues", "adjacency matrix entries",
    "sequence increment", "alphabet shift", "seating row length",
)
QUANT_HARD = (
    "age relationship", "f1 calculation", "balanced accuracy",
    "sql left join cardinality",
)
QUANT_MEDIUM = (
    "complete-graph edges", "postfix expression", "arithmetic recursion",
    "geometric sequence", "hcf numbers", "lcm numbers", "knn distance",
    "population variance", "quadratic gradient", "sql inner join duplicates",
    "sql row number", "travel path distance", "full binary-tree leaves",
    "shopping bill", "perfect binary-tree height", "classification precision",
    "classification recall", "classification specificity",
)
QUANT_EASY = (
    "sql count", "sql sum", "sql average", "sql distinct users",
    "sql threshold filter", "profit cost", "interest principal",
    "discount amount", "travel distance", "arithmetic mean",
    "undirected complete-graph edges", "rank from bottom", "die probability",
    "two-by-two determinant", "vector dot product",
)

# Advanced terminology typically requires prior specialist study but the
# definition-to-term format is still recognition, not full hard-level work.
SPECIALIST_TERMS = re.compile(
    r"\b(?:bellman.ford|amortiz|segment tree|disjoint.set|topological|"
    r"eigen|hessian|jacobian|gradient accumulation|adamw|lora|qlora|"
    r"quantiz|variational|diffusion|transformer|attention|"
    r"vector clock|exactly.once|distributed transaction|"
    r"two.phase commit|sharding|eventual consistency|"
    r"backpropagation|cross.entropy|bayesian|"
    r"conditional probability|poisson|anova|"
    r"window function|recursive cte|isolation level|"
    r"cap theorem|raft|paxos|kalman|"
    r"causal inference|counterfactual|monte carlo|"
    r"homomorph|elliptic curve|zero.knowledge|"
    r"fixed lod|include lod|exclude lod|"
    r"graph neural|mixed precision|"
    r"system design|circuit breaker|idempotency)\b",
    re.IGNORECASE,
)

BASIC_TERMS = re.compile(
    r"^(?:grep|find|chmod|html label|html form|"
    r"zero factorial|countif purpose|absolute reference|"
    r"operator precedence|arithmetic mean|mean|median|mode|"
    r"text classification|string|integer|list|tuple|"
    r"loop|variable|constructor|encapsulation|inheritance|"
    r"sum|count|minimum|maximum|file|directory|"
    r"simple present|verb agreement|phrasal verb)",
    re.IGNORECASE,
)


def knowledge_difficulty(item: dict, pack_name: str) -> str:
    specified = item.get("difficulty")
    if specified is not None:
        if specified not in LEVELS:
            raise ValueError(f"Invalid authored knowledge-check difficulty: {specified}")
        return specified

    skill = str(item["skill"]).lower().strip()
    prompt = str(item["prompt"]).lower()

    if "05_calculated" in pack_name:
        if skill.startswith(QUANT_HARD):
            return "Hard"
        if skill.startswith(QUANT_MEDIUM):
            return "Medium"
        if skill.startswith(QUANT_BEGINNER):
            return "Beginner"
        if skill.startswith(QUANT_EASY):
            return "Easy"
        # Direct one-formula arithmetic is a simpler application. Remaining
        # scenarios involving multiple conditions need closer reasoning.
        if any(term in skill for term in ("probability", "retention", "threshold")):
            return "Medium"
        return "Easy"

    # Grammar fills and direct definitions should not all be tagged Easy.
    if "06g_english" in pack_name:
        if any(term in skill for term in ("conditional", "reported speech", "passive voice")):
            return "Medium"
        if any(term in skill for term in ("phrasal verb", "verb agreement", "preposition")):
            return "Beginner"
        return "Easy"

    if SPECIALIST_TERMS.search(skill):
        return "Medium"
    if BASIC_TERMS.search(skill):
        return "Beginner"

    # A two-step or conditional application is harder than straightforward
    # term recognition; a named advanced subject alone is not sufficient.
    if any(phrase in prompt for phrase in (
        "what is the probability that", "which expression correctly",
        "given the following", "after performing", "if both", "which condition",
    )):
        return "Medium"
    return "Easy"
