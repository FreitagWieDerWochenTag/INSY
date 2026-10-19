"""Training data for the exercises (tables taken from Aufgabenstellung.pdf)."""

XOR_INPUTS = [[0, 0], [0, 1], [1, 0], [1, 1]]
XOR_TARGETS = [[0], [1], [1], [0]]

# 4-bit BCD input (MSB first) -> segments [A, B, C, D, E, F, G]
SEVEN_SEG_INPUTS = [[(d >> b) & 1 for b in (3, 2, 1, 0)] for d in range(10)]
SEVEN_SEG_TARGETS = [
    [1, 1, 1, 1, 1, 1, 0],  # 0
    [0, 1, 1, 0, 0, 0, 0],  # 1
    [1, 1, 0, 1, 1, 0, 1],  # 2
    [1, 1, 1, 1, 0, 0, 1],  # 3
    [0, 1, 1, 0, 0, 1, 1],  # 4
    [1, 0, 1, 1, 0, 1, 1],  # 5
    [1, 0, 1, 1, 1, 1, 1],  # 6
    [1, 1, 1, 0, 0, 0, 0],  # 7
    [1, 1, 1, 1, 1, 1, 1],  # 8
    [1, 1, 1, 1, 0, 1, 1],  # 9
]
SEGMENT_NAMES = "ABCDEFG"
