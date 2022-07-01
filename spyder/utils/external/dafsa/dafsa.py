# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2019-2020 Tiago Tresoldiy
# Copyright (c) 2016- Spyder Project Contributors
#
# Licensed under the terms of the BSD 3-clause license
# (see LICENSE.txt in this directory for details)
# -----------------------------------------------------------------------------


"""
Main module for computing DAFSA/DAWG graphs from list of strings.

The library computes a Deterministic Acyclic Finite State Automata from a
list of sequences in a non incremental way, with no plans to expand to
incremental computation. The library was originally based on public domain
code by `Steve Hanov (2011) <http://stevehanov.ca/blog/?id=115>`__.

Adapted from dafsa/dafsa.py of
`DAFSA <https://github.com/tresoldi/dafsa>`_.
"""

# Import Python standard libraries
from collections import Counter
import copy
import itertools


def common_prefix_length(seq_a, seq_b):
    """
    Return the length of the common prefix between two sequences.
    Parameters
    ----------
    seq_a : iter
        An iterable holding the first sequence.
    seq_b : iter
        An iterable holding the second sequence.
    Returns
    -------
    length: int
        The length of the common prefix between `seq_a` and `seq_b`.
    Examples
    --------
    >>> import dafsa
    >>> dafsa.utils.common_prefix_length("abcde", "abcDE")
    3
    >>> dafsa.utils.common_prefix_length("abcde", "ABCDE")
    0
    """

    common_prefix_len = 0
    for i in range(min(len(seq_a), len(seq_b))):
        if seq_a[i] != seq_b[i]:
            break
        common_prefix_len += 1

    return common_prefix_len


def pairwise(iterable):
    """
    Iterate pairwise over an iterable.
    The function follows the recipe offered on Python's `itertools`
    documentation.
    Parameters
    ----------
    iterable : iter
        The iterable to be iterate pairwise.
    Examples
    --------
    >>> import dafsa
    >>> list(dafsa.utils.pairwise([1,2,3,4,5]))
    [(1, 2), (2, 3), (3, 4), (4, 5)]
    """

    elem_a, elem_b = itertools.tee(iterable)
    next(elem_b, None)

    return zip(elem_a, elem_b)

# comment on internal node_id, meaningless
class DAFSANode:
    """
    Class representing node objects in a DAFSA.

    Each object carries an internal ``node_id`` integer identifier which must
    be locally unique within a DAFSA, but is meaningless. There is no
    implicit order nor a sequential progression must be observed.

    As in previous implementation by Hanov (2011), minimization is performed
    by comparing nodes, with equivalence determined by the standard
    Python ``.__eq__()`` method which overloads the equality operator. Nodes
    are considered identical if they have identical edges, which edges
    pointing from or to the same node. In particular, edge weight and node
    finalness, respectively expressed by the ``.weight`` and ``.final``
    properties, are *not* considered. This allows to correctly count edges
    after minimization and to have final pass-through nodes.

    Parameters
    ----------
    node_id : int
        The global unique ID for the current node.
    """

    # pylint: disable=too-few-public-methods

    def __init__(self, node_id):
        """
        Initializes a DAFSANode.
        """

        # Initialize as an empty node
        self.edges = {}
        self.final = False
        self.weight = 0

        # Set values node_id value
        self.node_id = node_id

    def __str__(self):
        """
        Return a textual representation of the node.

        The representation lists any edge, with ``id`` and ``attr``ibute. The
        edge dictionary is sorted at every call, so that, even if
        more expansive computationally, the function is guaranteed to be
        idempotent in all implementations.

        Please note that, as counts and final state are not accounted for,
        the value returned by this method might be ambiguous, with different
        nodes returning the same value. For unambigous representation,
        the ``.__repr__()`` method must be used.

.. code:: python
        >>> from dafsa import DAFSANode, DAFSAEdge
        >>> node = DAFSANode(0)
        >>> node.final = True
        >>> node.edges["x"] = DAFSAEdge(DAFSANode(1), 1)
        >>> str(node)
        'x|1'

        Returns
        -------
        string : str
            The (potentially ambiguous) textual representation of the
            current node.
        """

        # Build the buffer; please note the differences in implementation
        # when compared to `.__repr__()`
        buf = ";".join(
            [
                "%s|%i" % (label, self.edges[label].node.node_id)
                for label in sorted(self.edges)
            ]
        )

        return buf

    def __repr__(self):
        """
        Return an unambigous textual representation of the node.

        The representation lists any edge, with all properties. The
        edge dictionary is sorted at every call, so that, even if
        more expansive computationally, the function is guaranteed to be
        idempotent in all implementations.

        Please note that, as the return value includes information such as
        edge weight, it cannot be used for minimization. For such purposes,
        the potentially ambiguous ``.__str__()`` method must be used.

.. code:: python
        >>> from dafsa import DAFSANode, DAFSAEdge
        >>> node = DAFSANode(0)
        >>> node.final = True
        >>> node.edges["x"] = DAFSAEdge(DAFSANode(1), 1)
        >>> repr(node)
        '0(#1/0:<x>/1)'

        Returns
        -------
        string : str
            The unambiguous textual representation of the current node.
        """

        # Build the buffer; please note the differences in implementation
        # when compared to `.__str__()`
        buf = ";".join(
            [
                "|".join(
                    [
                        "#%i/%i:<%s>/%i"
                        % (
                            self.edges[label].node.node_id,
                            self.weight,
                            label,
                            self.edges[label].weight,
                        )
                        for label in sorted(self.edges)
                    ]
                )
            ]
        )

        # Add node information on start ("0"), final ("F"), or normal node
        # ("n")
        if self.node_id == 0:
            buf = "0(%s)" % buf
        elif self.final:
            buf = "F(%s)" % buf
        else:
            buf = "n(%s)" % buf

        return buf

    def __eq__(self, other):
        """
        Checks whether two nodes are equivalent.

        Please note that this method checks for *equivalence* (in particular,
        disregarding edge weight), and not for *equality*.

        Paremeters
        ----------
        other : DAFSANode
            The DAFSANode to be compared with the current one.

        Returns
        -------
        eq : bool
            A boolean indicating if the two nodes are equivalent.
        """

        # This is the most sensitive method for performance, as the string
        # conversion is quite expansive computationally. We thus check
        # for difference in less expansive ways before calling __str__.
        if len(self.edges) != len(other.edges):
            return False

        # By our definition, final nodes cannot be equal to non-final
        # nodes, even with equal transitions.
        if self.final != other.final:
            return False

        # Direct comparison, without building a string, so we can leave
        # as soon as possible
        for label in self.edges:
            if label not in other.edges:
                return False

            if (
                self.edges[label].node.node_id
                != other.edges[label].node.node_id
            ):
                return False

        return True

    def __gt__(self, other):
        """
        Return a "greater than" comparison between two nodes.

        Internally, the method reuses the ``.__str__()`` method, so that
        the logic for comparison is implemented in a single place. As such,
        while it guarantees idempotency when sorting nodes, it does not
        check for properties suc like "node length", "entropy", or
        "information amount", only providing a convenient complementary
        method to ``.__eq__()``.

        Paremeters
        ----------
        other : DAFSANode
            The DAFSANode to be compared with the current one.

        Returns
        -------
        gt : bool
            A boolean indicating if the current node is greater than the one
            it is compared with (that is, if it should be placed after it
            in an ordered sequence).
        """

        return self.__str__() > other.__str__()

    def __hash__(self):
        """
        Return a hash for the node.

        The returned has is based on the potentially ambigous string
        representation provided by the ``.__str__()`` method, allowing to
        use nodes as, among others, dictionary keys. The choice of the
        potentially ambiguous ``.__str__()`` over ``.__repr__()`` is intentional
        and by design and complemented by the ``.repr_hash()`` method.

        Returns
        -------
        hash : number
            The hash from the (potentially ambigous) textual representation of
            the current node.
        """

        return self.__str__().__hash__()

    def repr_hash(self):
        """
        Return a hash for the node.

        The returned has is based on the unambigous string
        representation provided by the ``.__repr__()`` method, allowing to
        use nodes as, among others, dictionary keys. The method is
        complemented by the ``.__hash__()`` one.

        Returns
        -------
        hash : number
            The hash from the unambigous textual representation of the
            current node.
        """

        return self.__repr__().__hash__()


class DAFSAEdge(dict):
    """
    Class representing edge objects in a DAFSA.

    This class overloads a normal Python dictionary, and in simpler
    implementations could potentially be replaced with a pure dictionary.
    It was implemented as its own object for homogeneity and for planned
    future expansions, particularly in terms of fuzzy automata.

    Parameters
    ----------
    node : DAFSANode
        Reference to the target node, mandatory. Please note that it
        must be a DAFSANode object and *not* a node id.
    weight : int
        Edge weight as collected from training data. Defaults to 0.
    """

    def __init__(self, node, weight=0):
        """
        Initializes a DAFSA edge.
        """

        # Call super class initialization.
        super().__init__()

        # Validate values and set them
        if not isinstance(node, DAFSANode):
            raise TypeError(
                "`node` must be a DAFSANode (perhaps a `node_id` was passed?)."
            )
        self.node = node
        self.weight = weight

    def __str__(self):
        """
        Return a textual representation of the node.

        The representation only include the ``node_id``, without information
        on the node actual contents.

        Returns
        -------
        string : str
            The (potentially ambiguous) textual representation of the
            current edge.
        """

        return "{node_id: %i, weight: %i}" % (self.node.node_id, self.weight)

    def __repr__(self):
        """
        Return a full textual representation of the node.

        The representation includes information on the entire contents of
        the node.

        Returns
        -------
        string : str
            The unambiguous textual representation of the current edge.
        """

        return "{node: <%s>, weight: %i}" % (repr(self.node), self.weight)

    def __hash__(self):
        """
        Return a hash for the edge.

        The returned has is based on the potentially ambigous string
        representation provided by the ``.__str__()`` method, allowing to
        use edges as, among others, dictionary keys. The choice of the
        potentially ambiguous ``.__str__()`` over ``.__repr__()`` is intentional
        and by design and complemented by the ``.repr_hash()`` method.

        Returns
        -------
        hash : number
            The hash from the (potentially ambigous) textual representation of
            the current edge.
        """

        return self.__str__().__hash__()

    def repr_hash(self):
        """
        Return a hash for the edge.

        The returned has is based on the unambigous string
        representation provided by the ``.__repr__()`` method, allowing to
        use edges as, among others, dictionary keys. The method is
        complemented by the ``.__hash__()`` one.

        Returns
        -------
        hash : number
            The hash from the unambigous textual representation of the
            current edge.
        """

        return self.__repr__().__hash__()


class DAFSA:
    """
    Class representing a DAFSA object.

    Parameters
    ----------
    sequences : list
        List of sequences to be added to the DAFSA object.
    weight : bool
        Whether to collect edge weights after minimization. Defaults
        to ``True``.
    condense: bool
        Whether to join sequences of transitions into single compound
        transitions whenever possible. Defaults to ``False``.
    delimiter : str
        The delimiter to use in case of joining single path transitions.
        Defaults to a single white space (`" "`).
    minimize : bool
        Whether to minimize the trie into a DAFSA. Defaults to ``True``; this
        option is implemented for development and testing purposes and
        it is not intended for users (there are specific and better libraries
        and algorithms to build tries).
    """

    def __init__(self, sequences, **kwargs):
        """
        Initializes a DAFSA object.
        """

        # Store arguments either internally in the object for reuse (such
        # as `"delimiter"`) or in an in-method variable (such as
        # `"minimize"`)
        self._delimiter = kwargs.get("delimiter", " ")
        minimize = kwargs.get("minimize", True)

        # Initializes an internal counter iterator, which is used to
        # provide unique IDs to nodes
        self._iditer = itertools.count()

        # List of nodes in the graph (during minimization, it is the list
        # of unique nodes that have been checked for duplicates).
        # Includes by default a root node. We also initialize to `None`
        # the .lookup_nodes property, which is used mostly by the
        # `.lookup()` method and will be equal to the `.nodes` property
        # if no single path joining is performed.
        self.nodes = {0: DAFSANode(next(self._iditer))}
        self.lookup_nodes = None

        # Internal list of nodes that still hasn't been checked for
        # duplicates; note that the data structure, a list of
        # parent, attribute, and child, is different from the result
        # stored in `self.nodes` after minimization (as such information
        # is only needed for minimization).
        self._unchecked_nodes = []

        # Variable holding the number of sequences stored; it is initialized
        # to `None`, so we can differentiate from empty sets. Note that it
        # is set as an internal variable, to be accessed with the
        # `.num_sequences()` method in analogy to the number of nodes and
        # edges.
        self._num_sequences = None

        # Initiate sequence insertion: 1. takes a sorted set of the
        # sequences and store its length
        sequences = sorted(sequences)
        self._num_sequences = len(sequences)

        # Make sure the words are sorted, adding a dummy empty `previous`
        # sequence for the pairwise loop
        for previous_seq, seq in pairwise([""] + sequences):
            self._insert_single_seq(seq, previous_seq, minimize)

        # Perform the minimization for the entire graph, until
        # `self._unchecked_nodes` is emptied.
        # The `._minimize()` method will take care of skipping over
        # if no minimization is requested.
        self._minimize(0, minimize)

        # Collect (or update) edge weights if requested. While this means
        # a second pass at all the sequences, it is better to do it in
        # separate step/method: it doesn't affect the computation speed
        # significantly, makes the logic easier to follow, and allows
        # to decide whether to collect the weights or not.
        if kwargs.get("weight", True):
            self._collect_weights(sequences)

        # After the final minimization, we can join single transitions
        # if so requested. In any case, we will make a copy of nodes and edges
        # in their current state, which can be used by other functions
        # and methods (mainly by `.lookup()`) as well as by the user, if so
        # desired.
        self.lookup_nodes = copy.deepcopy(self.nodes)
        if kwargs.get("condense", False):
            self.condense()

    def _insert_single_seq(self, seq, previous_seq, minimize):
        """
        Internal method for single sequence insertion.

        Parameters
        ----------
        seq: sequence
            The sequence being inserted.
        previous_seq : sequence
            The previous sequence from the sorted list of sequences,
            for common prefix length computation.
        minimize : bool
            Flag indicating whether to perform minimization or not.
        """

        # Obtain the length of the common prefix between the current word
        # and the one added before it, then using ._unchecked_nodes for
        # removing redundant nodes, proceeding from the last one down to
        # the the common prefix size. The list will be truncated at that
        # point.
        prefix_len = common_prefix_length(seq, previous_seq)
        self._minimize(prefix_len, minimize)

        # Add the suffix, starting from the correct node mid-way through the
        # graph, provided there are unchecked nodes (otherwise, just
        # start at the root). If there is no shared prefix, the node is
        # obviously the root (the only thing the two sequences share is
        # the start symbol)
        if not self._unchecked_nodes:
            node = self.nodes[0]
        else:
            node = self._unchecked_nodes[-1]["child"]

        # For everything after the common prefix, create as many necessary
        # new nodes and add them.
        for token in seq[prefix_len:]:
            # Create a new child node, build an edge to it, add it to the
            # list of unchecked nodes (there might be duplicates in the
            # future) and proceed until the end of the sequence
            child = DAFSANode(next(self._iditer))
            node.edges[token] = DAFSAEdge(child)
            self._unchecked_nodes.append(
                {"parent": node, "token": token, "child": child}
            )
            node = child

        # This last node from the above loop is a terminal one
        node.final = True

    def _minimize(self, index, minimize):
        """
        Internal method for graph minimization.

        Minimize the graph from the last unchecked item until ``index``.
        Final minimization, with ``index`` equal to zero, will traverse the
        entire data structure.

        The method allows the minimization to be overridden by setting to
        ``False`` the ``minimize`` flag (returning a trie). Due to the logic in
        place for the DAFSA minimization, this ends up executed as a
        non-efficient code, where all comparisons fail, but it is
        necessary to do it this way to clean the list of unchecked nodes.
        This is not an implementation problem: this class is not supposed
        to be used for generating tries (there are more efficient ways of
        doing that), but it worth having the flag in place for experiments.

        Parameters
        ----------
        index : int
            The index until the sequence minimization, right to left.
        minimize : bool
            Flag indicating whether to perform minimization or not.
        """

        # Please note that this loop could be removed, but it would
        # unnecessarily complicate a logic which is already not immediately
        # intuitive (even if less idiomatic). Also note that, to guarantee
        # that the graph is minimized as much as possible with a single
        # call to this method, we restart the loop each time an item is
        # changed, only leaving when it is untouched.
        while True:
            # Sentinel to whether the graph was changed
            graph_changed = False

            for _ in range(len(self._unchecked_nodes) - index):
                # Remove the last item from unchecked nodes and extract
                # information on parent, attribute, and child for checking
                # if we can minimize the graph.
                unchecked_node = self._unchecked_nodes.pop()
                parent = unchecked_node["parent"]
                token = unchecked_node["token"]
                child = unchecked_node["child"]

                # If the child is already among the minimized nodes, replace it
                # with one previously encountered, also setting the sentinel;
                # otherwise, add the state to the list of minimized nodes.
                # The logic is to iterate over all self.nodes items,
                # compare each `node` with the `child` (using the internal
                # `.__eq__()` method), and carry the key/index in case
                # it is found.
                if not minimize:
                    self.nodes[child.node_id] = child
                else:
                    # Use the first node that matches, and make sure to
                    # carry the information about final state of the
                    # child, if that is the case
                    child_idx = None
                    for node_idx, node in self.nodes.items():
                        if node == child:
                            child_idx = node_idx
                            break

                    if child_idx:
                        # Use the first node that matches, and make sure to
                        # carry the information about final state of the
                        # child, if that is the case
                        if parent.edges[token].node.final:
                            self.nodes[child_idx].final = True
                        parent.edges[token].node = self.nodes[child_idx]

                        # Mark the graph as changed, so we restart the loop
                        graph_changed = True
                    else:
                        self.nodes[child.node_id] = child

            # Only leave the loop if the graph was untouched
            if not graph_changed:
                break

    def condense(self):
        """
        Condenses the automaton, merging single-child nodes with their parents.

        The function joins paths of unique edges into single edges with
        compound transitions, removing redundant nodes. A redundant node
        is defined as one that (a) is not final, (b) emits a single transition,
        (b) receives a single transition, and (d) its source emits a single
        transition.

        Internally, the function will call the ``._joining_round()``
        method until no more candidates for joining are available.
        Performing everything in a single step would require a more complex
        logic.
        """

        # Perform joining operations until no more are possible
        while True:
            if self._joining_round() == 0:
                break

    def _joining_round(self):
        """
        Internal method for the unique-edge joining algorithm.

        This function will be called a successive number of times by
        ``._join_transitions()``, until no more candidates for unique-edge
        joining are available (as informed by its return value).

        Returns
        -------
        num_operations: int
            The number of joining operations that was performed. When zero,
            it signals that no more joining is possible.
        """

        # Build inverse map of which state receives from which other state,
        # along with a counter for `sources` and `targets` so that we
        # can exclude nodes receiving more that one edge and/or emitting
        # more than one edge
        edges = []
        for source_id, node in self.nodes.items():
            edges += [
                {"source": source_id, "target": node.edges[label].node.node_id}
                for label in node.edges
            ]
        sources = Counter([edge["source"] for edge in edges])
        targets = Counter([edge["target"] for edge in edges])

        # Select nodes that (a) receive a single transition, (b) are not
        # final, (c) their source has a single emission
        transitions = []
        transitions_nodes = []
        for node_id, node in self.nodes.items():
            if targets[node_id] > 1:
                continue
            if sources[node_id] > 1:
                continue
            if node.final:
                continue

            # Get the transition that leads to this node; `transition_to`
            # is easy because we know to be emitting only one edge
            edge_info = [edge for edge in edges if edge["target"] == node_id][0]
            label_from = [
                label
                for label in self.nodes[edge_info["source"]].edges
                if self.nodes[edge_info["source"]].edges[label].node.node_id
                == edge_info["target"]
            ][0]
            label_to = list(node.edges.keys())[0]

            # collect the transition as long as it does not involve
            # nodes already in the list
            if all([node_id not in transitions_nodes for node_id in edge_info]):
                transitions_nodes += edge_info
                transitions.append(
                    {
                        "edge": edge_info,
                        "label_from": label_from,
                        "label_to": label_to,
                    }
                )

        # Now that we have collected the transitions that we can
        # combine, combine them creating new transitions
        for transition in transitions:
            new_label = self._delimiter.join(
                [transition["label_from"], transition["label_to"]]
            )

            # change the transition
            self.nodes[transition["edge"]["source"]].edges[
                new_label
            ] = DAFSAEdge(
                self.nodes[transition["edge"]["target"]]
                .edges[transition["label_to"]]
                .node,
                self.nodes[transition["edge"]["target"]]
                .edges[transition["label_to"]]
                .weight,
            )
            self.nodes[transition["edge"]["source"]].edges.pop(
                transition["label_from"]
            )
            self.nodes.pop(transition["edge"]["target"])

        # return number of transitions performed
        return len(transitions)

    def _collect_weights(self, sequences):
        """
        Internal method for collecting node and edge weights from sequences.

        This method requires the minimized graph to be already in place.

        Parameters
        ----------
        sequences : list
            List of sequences whose node and edge weights will be collected.
        """

        for seq in sequences:
            # Start at the root
            node = self.nodes[0]
            node.weight += 1

            # Follow the path, updating along the way
            for token in seq:
                node.edges[token].weight += 1
                node = node.edges[token].node
                node.weight += 1

    def lookup(self, sequence, stop_on_prefix=False):
        """
        Check if a sequence can be expressed by the DAFSA.

        The method does not return all possible potential paths, nor
        the cumulative weight: if this is needed, the DAFSA object should
        be converted to a Graph and other libraries, such as ``networkx``,
        should be used.

        Parameters
        ----------
        sequence : sequence
            Sequence to be checked for presence/absence.

        Returns
        -------
        node : tuple of DAFSANode and int, or None
            Either a tuple with a DAFSANode referring to the final state
            that can be reached by following the specified sequence,
            plus the cumulative weight for reaching it, or None if no path
            can be found.
        """

        # Start at the root
        node = self.lookup_nodes[0]

        # If we can follow a path, it is valid, otherwise return None
        cum_weight = 0
        for token in sequence:
            if token not in node.edges:
                return None
            cum_weight += node.edges[token].weight
            node = node.edges[token].node
            if stop_on_prefix and node.final:
                break

        # Check if the last node is indeed a final one (so we don't
        # match prefixes alone)
        if not node.final:
            return None

        return node, cum_weight

    def count_nodes(self):
        """
        Return the number of minimized nodes in the structure.

        Returns
        -------
        node_count : int
            Number of minimized nodes in the structure.
        """

        return len(self.nodes)

    def count_edges(self):
        """
        Return the number of minimized edges in the structure.

        Returns
        -------
        edge_count : int
            Number of minimized edges in the structure.
        """

        return sum([len(node.edges) for node in self.nodes.values()])

    def count_sequences(self):
        """
        Return the number of sequences inserted in the structure.

        Please note that the return value mirrors the number of sequences
        provided during initialization, and *not* a set of it: repeated
        sequences are accounted, as each will be added a single time to
        the object.

        Returns
        -------
        seq_count : int
            Number of sequences in the structure.
        """

        return self._num_sequences

    def __str__(self):
        """
        Return a readable multiline textual representation of the object.

        Returns
        -------
        string : str
            The textual representation of the object.
        """

        # Add basic statistics, being aware of singular/plural
        buf = [
            "DAFSA with %i nodes and %i edges (%i inserted sequences)"
            % (self.count_nodes(), self.count_edges(), self.count_sequences())
        ]

        # Add information on nodes
        # Override pylint false positive
        # pylint: disable=no-member
        for node_id in sorted(self.nodes):
            node = self.nodes[node_id]
            buf += [
                "  +-- #%i: %s %s"
                % (
                    node_id,
                    repr(node),
                    [(attr, n.node.node_id) for attr, n in node.edges.items()],
                )
            ]

        # build a single string and returns
        return "\n".join(buf)
