#!/usr/bin/env python

from molmod import *

# 0) Create a molecule object based on the XYZ file 'caffeine.xyz'. Also
# initialize the graph.
mol = Molecule.from_file("ethanol.xyz")
mol.set_default_graph()

# 1) Print out all the isomorphisms. For the ethanol molecule, this comes down
# to all possible ways to rotate/mirror the methyl moieties, and combination
# thereof.
print "Isomorphisms in the form of one-to-one mappings"
for symmetry in mol.graph.symmetries:
    print symmetry

print "Isomorphisms in the form of permutations"
# 2) One can also request isomorphisms in the form of permutations, which is
# often more convenient:
for cycle in mol.graph.symmetry_cycles:
    print cycle
