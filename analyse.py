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
        self.species = None
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
        if self.species is not None:
            print("  " * indent + f"* {self.scientific}: {self.species}", file=f)
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
        t.species = s['name']
        SPECIES[s['name']] = t
        while t is not None:
            t.leaves.add(s['name'])
            t = t.parent

def lca_2nodes(a, b):
    while a.depth > b.depth:
        a = a.parent
    while b.depth > a.depth:
        b = b.parent
    while a is not b:
        a = a.parent
        b = b.parent
    return a

def lca_species(*lst):
    ret = SPECIES[lst[0]]
    for i in lst[1:]:
        ret = lca_2nodes(ret, SPECIES[i])
    return ret

def get_successors(poss, guess):
    ret = []
    for real in poss:
        if real == guess:
            continue
        new_lca = lca_species(guess, real)
        found = False
        for i in range(len(ret)):
            if ret[i][0] == new_lca:
                ret[i][1].add(real)
                found = True
                break
        if not found:
            ret.append((new_lca, set([real])))
    return ret

def build_minavg_order(node):
    child_orders = [(sub, build_minavg_order(sub)) for sub in node.children]
    child_orders.sort(key=lambda x: (-len(x[0].leaves), x[1]))
    ret = []
    for _, sub_order in child_orders:
        ret += sub_order
    if node.species is not None:
        ret.append(node.species)
    return ret

def order_to_decision_tree(node, poss, order):
    guess = None
    for species in order:
        if species in poss:
            guess = species
            break
    assert guess is not None
    succ = get_successors(poss, guess)
    return node, guess, [order_to_decision_tree(x[0], x[1], order) for x in succ]

def print_decision_tree(tree, guesses=None):
    node, guess, subs = tree

    # Sort children
    subs.sort(key=lambda x: x[0].depth) # sort phylogenetically
#   subs.sort(key=lambda x: (x[0].scientific, x[0].depth)) # sort lexicographically

    # Recurse to print tree structure.
    subdesc = ""
    max_guesses = 1
    sum_guesses = 1
    species = set([guess])
    sub_guesses = guesses | species
    for sub in subs:
        substr, submax, subsum, subspec = print_decision_tree(sub, sub_guesses)
        subdesc += substr
        max_guesses = max(max_guesses, submax + 1)
        sum_guesses += subsum + len(subspec)
        assert len(species & subspec) == 0
        species |= subspec

    # sanity checks
    for spec in species:
        best_lca = TREE
        for old_guess in guesses:
            lca = lca_species(spec, old_guess)
            if best_lca is None or lca.depth > best_lca.depth:
                best_lca = lca
        assert best_lca == node
    desc = "  " * len(guesses) + f"* {node.scientific}: {guess} (max {max_guesses}, avg {sum_guesses / len(species):.4g}, cnt {len(species)})\n" + subdesc
    assert species.issubset(node.leaves)

    # output resulting string + statistics
    return desc, max_guesses, sum_guesses, species

with open(f"output/species-{DATASET}.txt", "w") as f:
    TREE.print_tree(f)

ORDER = build_minavg_order(TREE)
DECIDE = order_to_decision_tree(TREE, set(TREE.leaves), ORDER)

with open(f"output/decision-{DATASET}.txt", "w") as f:
    desc, _, _, species = print_decision_tree(DECIDE, set())
    assert species == TREE.leaves
    f.write(desc)
