# Edit distance functions -- See en.wikipedia.org/wiki/Edit_distance

#   ╭───────────  deletion
#   │  ╭────────  insertion
#   │  │  ╭─────  substitution
#   │  │  │  ╭──  transposition
#   │  │  │  │
#   d  i  s  t    Damerau–Levenshtein
#   d  i  s  –    Levenshtein
#   d  i  –  t
#   d  i  –  –    Longest common subsequence
#   –  –  s  t
#   –  –  s  –    Hamming
#   –  –  –  t    Jaro


def DamerauLevenshtein(seq1, seq2):
    vec = [(len(seq2) + 1) * [0] for i in range(len(seq1) + 1)]
    for i in range(len(seq1) + 1):
        vec[i][0] = i
    for j in range(1, len(seq2) + 1):
        vec[0][j] = j
        for i in range(1, len(seq1) + 1):
            cost = int(seq1[i-1] != seq2[j-1])
            vec[i][j] = min(vec[i-1][j] + 1,     # deletion
                           vec[i][j-1] + 1,     # insertion
                           vec[i-1][j-1] + cost)  # substitution
            if i > 1 and j > 1 and seq1[i-1] == seq2[j-2] and seq1[i-2] == seq2[j-1]:
                vec[i][j] = min(vec[i][j], vec[i-2][j-2] + cost)  # transposition
    return vec[len(seq1)][len(seq2)]

def Hamming(seq1, seq2):
    assert len(seq1) == len(seq2)  # Sequences must be equally long
    return sum(sym1 != sym2 for sym1, sym2 in zip(seq1, seq2))

def Jaro(seq1, seq2):
    assert len(seq1) == len(seq2)  # Sequences must be equally long
    pass

def Levenshtein(seq1, seq2):
    vec1 = [i1 for i1 in range(len(seq1) + 1)]
    vec2 = [0 for _ in range(len(seq1) + 1)]
    for i2, sym2 in enumerate(seq2, 1):
        vec2[0] = i2
        for i1, sym1 in enumerate(seq1, 1):
            vec2[i1] = vec1[i1-1] if sym1 == sym2 else min(vec1[i1], vec1[i1-1], vec2[i1-1]) + 1
        vec1, vec2 = vec2, vec1
    return vec1[-1]

def LongestCommonSubsequence(seq1, seq2):
    pass


# To do

def JaroWinkler(seq1, seq2):
    pass
