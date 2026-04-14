"""
probes.py — All 6 probe categories for base model evaluation.

IMPORTANT: All prompts are completion-style, not instruction-style.
Base models complete text — they do not follow instructions.
Every prompt is written as the beginning of a sentence or pattern
that a knowledgeable model should be able to continue correctly.
"""

# Each probe is a dict:
# {
#   "id":           unique string identifier
#   "description":  what this probe tests
#   "prompt":       the completion prompt (no instruction framing)
#   "expected":     list of strings — ANY of which appearing in the
#                   completion counts as a pass
#   "case_sensitive": bool (default False)
# }


# =============================================================================
# 1. COMPLETION CONSISTENCY
# Run each prompt 3x — score based on whether all 3 agree on expected content.
# =============================================================================
CONSISTENCY_PROBES = [
    {
        "id": "con_001",
        "description": "Capital city recall — Paris",
        "prompt": "The capital city of France is",
        "expected": ["paris"],
        "runs": 3,
    },
    {
        "id": "con_002",
        "description": "Basic arithmetic completion",
        "prompt": "2 + 2 = 4 and 3 + 3 = 6 and 4 + 4 =",
        "expected": ["8"],
        "runs": 3,
    },
    {
        "id": "con_003",
        "description": "Scientific constant recall",
        "prompt": "Water freezes at 0 degrees",
        "expected": ["celsius", "centigrade", "c"],
        "runs": 3,
    },
    {
        "id": "con_004",
        "description": "Sequence pattern completion",
        "prompt": "Monday, Tuesday, Wednesday, Thursday,",
        "expected": ["friday"],
        "runs": 3,
    },
]


# =============================================================================
# 2. KNOWLEDGE & FACTUAL RECALL
# =============================================================================
KNOWLEDGE_PROBES = [
    {
        "id": "kno_001",
        "description": "Chemical symbol — Gold",
        "prompt": "The chemical symbol for gold is",
        "expected": ["au"],
    },
    {
        "id": "kno_002",
        "description": "Chemical formula — Water",
        "prompt": "The chemical formula for water is",
        "expected": ["h2o"],
    },
    {
        "id": "kno_003",
        "description": "Planetary order — largest planet",
        "prompt": "The largest planet in our solar system is",
        "expected": ["jupiter"],
    },
    {
        "id": "kno_004",
        "description": "Historical date — WW2 end",
        "prompt": "World War II ended in the year",
        "expected": ["1945"],
    },
    {
        "id": "kno_005",
        "description": "Speed of light (approximate)",
        "prompt": "The speed of light in a vacuum is approximately 300,000 kilometres per",
        "expected": ["second"],
    },
    {
        "id": "kno_006",
        "description": "Python creator",
        "prompt": "The Python programming language was created by",
        "expected": ["guido", "van rossum"],
    },
    {
        "id": "kno_007",
        "description": "Human chromosome count",
        "prompt": "Normal human cells contain",
        "expected": ["46", "23 pairs"],
    },
    {
        "id": "kno_008",
        "description": "Periodic table — first element",
        "prompt": "The first element on the periodic table is",
        "expected": ["hydrogen"],
    },
]


# =============================================================================
# 3. FORMAT COMPLIANCE
# Tests whether the model can follow structural/format patterns.
# =============================================================================
FORMAT_PROBES = [
    {
        "id": "fmt_001",
        "description": "JSON object completion",
        "prompt": '{"name": "Alice", "age": 30, "city":',
        "expected": ['"', "'"],  # should start a string value
    },
    {
        "id": "fmt_002",
        "description": "Numbered list continuation",
        "prompt": "1. Apple\n2. Banana\n3. Cherry\n4.",
        "expected": ["date", "elderberry", "fig", "grape", "kiwi", "lemon",
                     "mango", "orange", "pear", "plum", "peach", "strawberry",
                     "watermelon", "blueberry", "raspberry"],
    },
    {
        "id": "fmt_003",
        "description": "Markdown heading continuation",
        "prompt": "# Introduction\n\n## Background\n\n## ",
        "expected": ["method", "results", "discussion", "conclusion",
                     "overview", "approach", "analysis", "summary"],
    },
    {
        "id": "fmt_004",
        "description": "Key-value pair pattern",
        "prompt": "Name: John\nAge: 25\nCity: London\nCountry:",
        "expected": ["uk", "england", "britain", "united kingdom",
                     "france", "germany", "usa", "canada", "australia"],  # any country
    },
    {
        "id": "fmt_005",
        "description": "CSV row continuation",
        "prompt": "id,name,score\n1,Alice,95\n2,Bob,87\n3,",
        "expected": ["charlie", "carol", "chris", "dave", "eve", "frank"],
    },
    {
        "id": "fmt_006",
        "description": "Python function signature pattern",
        "prompt": "def add(a, b):\n    return a + b\n\ndef multiply(a, b):\n    return",
        "expected": ["a * b", "a*b"],
    },
]


# =============================================================================
# 4. INSTRUCTION FOLLOWING PATTERNS
# Tests how well the base model responds to common prompt formats
# that are used in SFT training data. Crucial for data design.
# =============================================================================
INSTRUCTION_PROBES = [
    {
        "id": "ins_001",
        "description": "Q&A format — simple fact",
        "prompt": "Q: What colour is the sky on a clear day?\nA:",
        "expected": ["blue"],
    },
    {
        "id": "ins_002",
        "description": "Q&A format — arithmetic",
        "prompt": "Q: What is 15 multiplied by 4?\nA:",
        "expected": ["60"],
    },
    {
        "id": "ins_003",
        "description": "Alpaca instruction format",
        "prompt": "### Instruction\nName the three primary colours.\n\n### Response\nThe three primary colours are",
        "expected": ["red", "blue", "yellow"],
    },
    {
        "id": "ins_004",
        "description": "Human/Assistant chat format",
        "prompt": "Human: What is the capital of Germany?\nAssistant:",
        "expected": ["berlin"],
    },
    {
        "id": "ins_005",
        "description": "Fill-in-the-blank pattern",
        "prompt": "Complete the following sentence: The sun rises in the",
        "expected": ["east"],
    },
    {
        "id": "ins_006",
        "description": "Task completion prefix",
        "prompt": "Task: List the four seasons.\nAnswer: The four seasons are spring,",
        "expected": ["summer", "autumn", "fall", "winter"],
    },
]


# =============================================================================
# 5. GEOMETRY & SPATIAL REASONING
# Specifically targets the GC-08 failure zone from NeuroForge history.
# =============================================================================
GEOMETRY_PROBES = [
    {
        "id": "geo_001",
        "description": "Triangle angle sum",
        "prompt": "The sum of all interior angles in a triangle is",
        "expected": ["180"],
    },
    {
        "id": "geo_002",
        "description": "Square properties — sides",
        "prompt": "A square has 4 equal sides and",
        "expected": ["4 right", "four right", "4 equal angle", "90", "right angle"],
    },
    {
        "id": "geo_003",
        "description": "Circle degrees",
        "prompt": "A full circle contains",
        "expected": ["360"],
    },
    {
        "id": "geo_004",
        "description": "Rectangle area formula",
        "prompt": "The area of a rectangle is calculated by multiplying its length by its",
        "expected": ["width", "breadth"],
    },
    {
        "id": "geo_005",
        "description": "Right triangle — Pythagorean theorem",
        "prompt": "In a right triangle with sides 3 and 4, the hypotenuse is",
        "expected": ["5"],
    },
    {
        "id": "geo_006",
        "description": "Spatial rotation — square",
        "prompt": "When a square is rotated 45 degrees, it resembles a",
        "expected": ["diamond", "rhombus"],
    },
    {
        "id": "geo_007",
        "description": "3D shape — cube faces",
        "prompt": "A cube has",
        "expected": ["6 face", "six face"],
    },
    {
        "id": "geo_008",
        "description": "Parallel lines",
        "prompt": "Two parallel lines will",
        "expected": ["never meet", "never intersect", "not intersect", "not cross"],
    },
]


# =============================================================================
# 6. REASONING & LOGIC
# =============================================================================
REASONING_PROBES = [
    {
        "id": "rea_001",
        "description": "Syllogism — basic deduction",
        "prompt": "All dogs are mammals. Rex is a dog. Therefore, Rex is",
        "expected": ["a mammal", "mammal"],
    },
    {
        "id": "rea_002",
        "description": "Numeric pattern — powers of 2",
        "prompt": "1, 2, 4, 8, 16, 32,",
        "expected": ["64"],
    },
    {
        "id": "rea_003",
        "description": "Transitive comparison",
        "prompt": "If A is greater than B, and B is greater than C, then A is greater than",
        "expected": ["c"],
    },
    {
        "id": "rea_004",
        "description": "Modus ponens",
        "prompt": "If it rains, the ground gets wet. It is raining. Therefore, the ground is",
        "expected": ["wet"],
    },
    {
        "id": "rea_005",
        "description": "Fibonacci sequence",
        "prompt": "1, 1, 2, 3, 5, 8, 13,",
        "expected": ["21"],
    },
    {
        "id": "rea_006",
        "description": "Multi-step arithmetic",
        "prompt": "A store has 100 apples. It sells 35 on Monday and 28 on Tuesday. The store now has",
        "expected": ["37"],
    },
    {
        "id": "rea_007",
        "description": "Analogical reasoning",
        "prompt": "Hot is to cold as day is to",
        "expected": ["night"],
    },
    {
        "id": "rea_008",
        "description": "Contrapositive reasoning",
        "prompt": "Every prime number greater than 2 is odd. 4 is even. Therefore, 4 is",
        "expected": ["not prime", "composite"],
    },
]


# Master category map
ALL_CATEGORIES = {
    "consistency":   {"label": "Completion Consistency",          "probes": CONSISTENCY_PROBES},
    "knowledge":     {"label": "Knowledge & Factual Recall",      "probes": KNOWLEDGE_PROBES},
    "format":        {"label": "Format Compliance",               "probes": FORMAT_PROBES},
    "instruction":   {"label": "Instruction Following Patterns",  "probes": INSTRUCTION_PROBES},
    "geometry":      {"label": "Geometry & Spatial Reasoning",    "probes": GEOMETRY_PROBES},
    "reasoning":     {"label": "Reasoning & Logic",               "probes": REASONING_PROBES},
}
