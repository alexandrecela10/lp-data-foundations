from .docs_arm import DocsArm
from .semantic_arms import GraphArm, SemanticArm, SemanticIds
from .sql_arm import SqlArm

ARMS = {"A": DocsArm, "B": SqlArm, "C": SemanticArm, "C+ids": SemanticIds, "D": GraphArm}
LABELS = {"A": "Documents and an AI chatbot", "B": "AI writes the database query", "C": "Agreed definitions (semantic layer)",
          "C+ids": "C + company name list + letter search", "D": "C+ids + graph"}
