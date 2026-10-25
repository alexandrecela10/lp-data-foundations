from .docs_arm import DocsArm
from .semantic_arms import GraphArm, SemanticArm, SemanticIds
from .sql_arm import SqlArm

ARMS = {"A": DocsArm, "B": SqlArm, "C": SemanticArm, "C+ids": SemanticIds, "D": GraphArm}
LABELS = {"A": "Documents + search", "B": "Tables + AI-written SQL", "C": "Semantic layer",
          "C+ids": "Semantic layer + identity table + letter search", "D": "C+ids + graph"}
