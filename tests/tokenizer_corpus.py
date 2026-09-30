"""The texts tokenizer_test.py checks: fixed edge cases of every class the pre-tokenizer's patterns tell
apart, random mixes of them, and single words long enough to have overflowed a recursive regex's stack.
Deterministic (a fixed seed), so the golden token ids stay valid.
"""

import random

LETTERS = ["a", "Z", "é", "ß", "ǅ", "ж", "Ω", "ا", "中", "文", "の", "한", "ﬁ", "ª"]
DIGITS = ["0", "7", "٣", "²", "①", "Ⅻ", "߉", "１"]
MARKS = ["\u0301", "\u0308", "\u0654", "\u093f"]
PUNCT = [".", ",", "!", "?", "'", '"', "-", "(", ")", "[", "]", "{", "}", "_", "@", "#", "%", "&", "*", "/", ":", ";", "\\",
         "“", "”", "—", "…", "¿", "«", "»", "、", "。"]
SYMBOLS = ["$", "+", "<", "=", ">", "^", "`", "|", "~", "€", "©", "∑", "😀", "🚀", "✓"]
SPACES = [" ", " ", " ", "\t", "\n", "\r", "\r\n", "\v", "\f", "\u00a0", "\u2003", "\u3000", "\u0085", "\u2028", "\u202f", "\u1680"]
OTHER = ["\x00", "\x01", "\x1c", "\x1f", "\x7f", "\u0378", "\ue000", "\u200b", "\u200d", "\ufeff", "\U000e0001"]
CONTRACTIONS = ["'s", "'S", "'t", "'T", "'re", "'RE", "'Re", "'ve", "'VE", "'m", "'M", "'ll", "'LL", "'lL", "'d", "'D", "'x", "'"]
CLASSES = [LETTERS, DIGITS, MARKS, PUNCT, SYMBOLS, SPACES, OTHER, CONTRACTIONS]

FIXED = [
    "", " ", "  ", "a", "1", "12", "123", "1234", "1234567", "12345678901234567890", "a1b22c333d4444",
    "don't", "DON'T", "I'M", "we'Re", "it's 'S", "'s'ss''s", "a  1", "a   b", "a \n b", "  \n\n  x", "x  ", "x\t\t", " \r\n\r\n ",
    "hello world", "Hello, World!", " ?!", "  ?!", "...\n\n", "a.\r\nb", "x \u00a0y", "\u3000\u3000中文", "e\u0301clair",
    "3.14159 and 2,718", "٣٤٥٦٧", "²³⁴", "①②③④", "$100.00", "C++ <tag> a=b|c^d", "😀😀 🚀rocket", "Ⅻ12", "a\x00b\x1fc\x7f",
    "<s><evidence>\nThe box arrived empty.\n</evidence>\n\nQuestion: Is the customer upset?\nAnswer:",
    "<s><evidence>\n{\n \"item\": \"wireless mouse\",\n \"delivered\": \"5 days ago\"\n}\n</evidence>\n\nQuestion: Refund?\nAnswer:",
]
LONG = ["x" * 5000, "a" * 100000, "1" * 50000, "é" * 30000, " " * 20000, "\n" * 10000, "ab" * 40000, "!" * 30000,
        "a" * 70000 + " " + "1" * 70000 + " " + "!" * 70000, "x" * 255998]


def corpus():
    rng = random.Random(20260930)
    texts = list(FIXED)
    for _ in range(3000):
        n = rng.choice([1, 2, 3, 5, 8, 13, 40, 120])
        texts.append("".join(rng.choice(rng.choice(CLASSES)) * rng.choice([1, 1, 1, 2, 3, 4]) for _ in range(n)))
    return texts + LONG
