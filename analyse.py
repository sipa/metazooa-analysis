#!/usr/bin/env python3

import json
import sys
import math

SCIENTIFIC = {}

DATASET = sys.argv[1]
assert DATASET == "metaflora" or DATASET == "metazooa"

class TreeNode:
    """Represents a node in the phylogenetic tree."""

    def __init__(self, scientific, depth=0):
        global SCIENTIFIC
        self.scientific = scientific
        self.depth = depth
        self.children = []
        self.parent = None
        self.leaves = set()
        self.is_species = False
        SCIENTIFIC[scientific] = self

    def add_child(self, child):
        """Add a child node."""
        child.parent = self
        self.children.append(child)

    def __repr__(self):
        return f"TreeNode({self.scientific}, depth={self.depth}, leaves=[{','.join(self.leaves)}])"

    def to_dict(self):
        """Convert tree to nested dictionary."""
        result = {"scientific": self.scientific, "depth": self.depth}
        if self.children:
            result["children"] = [child.to_dict() for child in self.children]
        return result

    def print_tree(self, f, indent=0):
        """Print tree in indented format."""
        if self.is_species:
            print("  " * indent + f"* {self.scientific}: {next(iter(self.leaves))}", file=f)
        elif len(self.children) == 1:
            next(iter(self.children)).print_tree(f, indent)
        else:
            print("  " * indent + f"* {self.scientific}: ({len(self.leaves)} species)", file=f)
            for child in self.children:
                child.print_tree(f, indent + 1)

def calculate_depth(line):
    """
    Calculate the depth of a node based on its prefix characters.

    Args:
        line: String line from the tree file

    Returns:
        tuple: (depth, node_name)
    """
    # If line doesn't start with tree characters or spaces, it's the root
    if not line.startswith((' ', '|', '+', '\\')):
        return 0, line.strip()

    # Find where the node marker (+- or \-) appears
    marker_pos = -1
    for i in range(len(line) - 1):
        if line[i] in ['+', '\\'] and line[i + 1] == '-':
            marker_pos = i
            break

    if marker_pos == -1:
        return 0, ""

    # Node name starts after the '-'
    node_name = line[marker_pos + 2:].strip()

    # Calculate depth based on the column position of the marker
    # Each indentation level is 2 characters wide
    depth = (marker_pos // 2) + 1

    return depth, node_name


def parse_phylo_tree(file_path):
    """
    Parse phylogenetic tree from ASCII format file.

    Args:
        file_path: Path to the tree file

    Returns:
        TreeNode: Root node of the parsed tree
    """
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Stack to keep track of nodes at each depth
    # Format: {depth: node}
    stack = {}
    root = None

    for line in lines:
        if not line.strip():
            continue

        depth, name = calculate_depth(line)

        if not name:
            continue

        # Create new node
        node = TreeNode(name, depth)

        # First node is the root
        if root is None:
            root = node
            stack[depth] = node
            continue

        # Find parent (closest node with smaller depth)
        parent_depth = depth - 1
        while parent_depth >= 0:
            if parent_depth in stack:
                parent = stack[parent_depth]
                parent.add_child(node)
                break
            parent_depth -= 1

        # Update stack at this depth
        stack[depth] = node

        # Clear deeper levels from stack
        depths_to_remove = [d for d in stack.keys() if d > depth]
        for d in depths_to_remove:
            del stack[d]

    return root

TREE = parse_phylo_tree(f"input/phylo-{DATASET}.txt")

SPECIES = {}
with open(f"input/game-{DATASET}.json") as f:
    species = json.load(f)
    for s in species:
        t = SCIENTIFIC[s['scientific']]
        t.is_species = True
        SPECIES[s['name']] = t
        while t is not None:
            t.leaves.add(s['name'])
            t = t.parent

def lca_2nodes(a, b):
    while a.depth > b.depth:
        a = a.parent
    while b.depth > a.depth:
        b = b.parent
    while a.scientific != b.scientific:
        a = a.parent
        b = b.parent
    return a

def lca_species(*lst):
    ret = SPECIES[lst[0]]
    for i in lst[1:]:
        ret = lca_2nodes(ret, SPECIES[i])
    return ret

def get_successors(poss, guess):
    ret = {}
    for real in poss:
        if real == guess:
            continue
        new_lca = lca_species(guess, real).scientific
        ret.setdefault(new_lca, set()).add(real)
    return ret, sorted([len(x) for x in ret.values()], reverse=True)

def build_decision_tree(f, depth, scientific, poss):
    bestguess = None
    bestret = None
    bestbits = [1000000000000000.0]
    for guess in sorted(poss):
        ret, bits = get_successors(poss, guess)
        if bits < bestbits:
            bestguess, bestret, bestbits = guess, ret, bits
    assert bestret is not None
    print("  " * depth + f"* {scientific}: {bestguess}", file=f)
    ret = 0
    for next_scientific in sorted(bestret.keys()):
        ret += build_decision_tree(f, depth + 1, next_scientific, bestret[next_scientific])
    return ret + depth + 1

with open(f"output/species-{DATASET}.txt", "w") as f:
    TREE.print_tree(f)

with open(f"output/decision-{DATASET}.txt", "w") as f:
    build_decision_tree(f, 0, TREE.scientific, set(SPECIES.keys()))
