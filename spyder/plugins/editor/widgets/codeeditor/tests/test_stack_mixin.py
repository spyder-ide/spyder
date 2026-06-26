# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Unit tests for custom undo stack delta normalization/merging."""

import pytest

from spyder.plugins.editor.widgets.codeeditor.stack_mixin import (
    CursorState,
    EditBlock,
    TextDelta,
    UTF16String,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def cursor(position: int) -> tuple[int, int]:
    """Build a collapsed cursor state ``(start, end)``."""
    return (position, position)


def selection(anchor: int, position: int) -> tuple[int, int]:
    """Build a selection cursor state ``(selectionStart, selectionEnd)``."""
    return (min(anchor, position), max(anchor, position))


def td(position, inserted="", removed="", line=0, col=None) -> TextDelta:
    """Concise ``TextDelta`` builder wrapping text in ``UTF16String``.

    For single-line content the column equals the absolute position, so ``col``
    defaults to ``position`` (``line`` defaults to 0). Multi-line cases pass
    ``line``/``col`` explicitly.
    """
    return TextDelta(
        position=position,
        line=line,
        col=position if col is None else col,
        inserted_text=UTF16String(inserted),
        removed_text=UTF16String(removed),
    )


def assert_delta(
    actual: "TextDelta | None", position, inserted="", removed="", line=0, col=None
):
    """Assert a delta's position, text content *and* line/col bookkeeping.

    ``col`` defaults to ``position`` and ``line`` to 0, matching the single-line
    invariant that ``col == position`` (which every operation must preserve for
    single-line edits). Multi-line expectations pass ``line``/``col``.
    """
    assert actual is not None
    assert actual.position == position
    assert actual.inserted_text == inserted
    assert actual.removed_text == removed
    assert actual.line == line
    assert actual.col == (position if col is None else col)


def assert_deltas(actual_list, expected):
    """Assert a list of deltas against ``(position, inserted, removed)`` tuples.

    Each tuple may also carry ``line``/``col`` as 4th/5th items for multi-line
    cases; otherwise the single-line ``line=0``/``col=position`` defaults apply.
    """
    assert len(actual_list) == len(expected)
    for actual, exp in zip(actual_list, expected):
        assert_delta(actual, *exp)


# ---------------------------------------------------------------------------
# CursorState
# ---------------------------------------------------------------------------

def test_cursor_state_equality_uses_signature_not_identity():
    state1 = CursorState(
        main_cursor=cursor(10),
        extra_cursors=(selection(20, 25),),
    )
    state2 = CursorState(
        main_cursor=cursor(10),
        extra_cursors=(selection(20, 25),),
    )
    assert state1 == state2
    assert state1.signature() == state2.signature()


def test_cursor_state_inequality_detects_anchor_change():
    state1 = CursorState(
        main_cursor=selection(10, 12),
        extra_cursors=(),
    )
    # Different extra_cursors should make the signature differ reliably
    state2 = CursorState(
        main_cursor=selection(10, 12),
        extra_cursors=(cursor(5),),
    )
    assert state1 != state2


# ---------------------------------------------------------------------------
# TextDelta.normalized
# ---------------------------------------------------------------------------

def test_text_delta_normalized_strips_common_prefix_suffix():
    delta = td(position=10, removed="abcYdef", inserted="abcXdef")
    assert_delta(delta.normalized(), position=13, inserted="X", removed="Y")


def test_text_delta_normalized_returns_self_for_pure_insert_or_remove():
    insert_only = td(position=5, inserted="abc", removed="")
    remove_only = td(position=5, inserted="", removed="abc")
    assert insert_only.normalized() is insert_only
    assert remove_only.normalized() is remove_only


def test_text_delta_normalized_can_cancel_replace_to_empty_delta():
    # If inserted == removed, the net effect is a no-op; normalization reduces
    # to empty strings (and advances position by the stripped prefix).
    delta = td(position=100, inserted="abc", removed="abc")
    assert_delta(delta.normalized(), position=103, inserted="", removed="")


def test_text_delta_normalized_strips_only_prefix_or_only_suffix():
    prefix = td(position=0, inserted="abcX", removed="abcY")
    assert_delta(prefix.normalized(), position=3, inserted="X", removed="Y")

    suffix = td(position=10, inserted="Xdef", removed="Ydef")
    assert_delta(suffix.normalized(), position=10, inserted="X", removed="Y")


def test_text_delta_normalized_tracks_line_col_across_newline():
    # Prefix "ab\n" crosses a newline, so the column resets while the line
    # advances; the trailing common "d" is stripped as a suffix.
    delta = TextDelta(
        position=10,
        line=0,
        col=10,
        inserted_text=UTF16String("ab\ncd"),
        removed_text=UTF16String("ab\nXd"),
    )
    normalized = delta.normalized()
    assert normalized == TextDelta(
        position=13,
        line=1,
        col=0,
        inserted_text=UTF16String("c"),
        removed_text=UTF16String("X"),
    )


# ---------------------------------------------------------------------------
# TextDelta.merge_text_delta
# ---------------------------------------------------------------------------

def test_text_delta_merge_replace_overwrite_same_position():
    left = td(position=5, removed="abc", inserted="def")
    right = td(position=5, removed="def", inserted="xyz")
    merged = TextDelta.merge_text_delta(left, right)
    assert_delta(merged, position=5, removed="abc", inserted="xyz")


def test_text_delta_merge_sequential_inserts_concatenate():
    left = td(position=10, inserted="ab", removed="")
    right = td(position=12, inserted="cd", removed="")
    assert_delta(
        TextDelta.merge_text_delta(left, right),
        position=10, inserted="abcd", removed="",
    )


def test_text_delta_merge_sequential_removals_to_right_concatenate():
    left = td(position=10, inserted="", removed="ab")
    right = td(position=10, inserted="", removed="cd")
    assert_delta(
        TextDelta.merge_text_delta(left, right),
        position=10, inserted="", removed="abcd",
    )


def test_text_delta_merge_sequential_removals_to_left_concatenate():
    left = td(position=12, inserted="", removed="cd")
    right = td(position=10, inserted="", removed="ab")
    assert_delta(
        TextDelta.merge_text_delta(left, right),
        position=10, inserted="", removed="abcd",
    )


def test_text_delta_merge_replace_overlapping_prefix_pattern():
    left = td(position=10, inserted="ABC", removed="xxx")
    right = td(position=10, inserted="12", removed="AB")
    assert_delta(
        TextDelta.merge_text_delta(left, right),
        position=10, inserted="12C", removed="xxx",
    )


def test_text_delta_merge_returns_none_for_unrelated_deltas():
    left = td(position=10, inserted="a", removed="")
    right = td(position=50, inserted="b", removed="")
    assert TextDelta.merge_text_delta(left, right) is None


def test_text_delta_merge_removal_of_recent_insert_collapses_insert_stream():
    left = td(position=0, inserted="this isas", removed="")
    right = td(position=8, inserted="", removed="s")
    assert_delta(
        TextDelta.merge_text_delta(left, right),
        position=0, inserted="this isa", removed="",
    )


def test_text_delta_merge_remove_then_insert_same_position_becomes_replace():
    left = td(position=7, inserted="", removed="a")
    right = td(position=7, inserted=" ", removed="")
    assert_delta(
        TextDelta.merge_text_delta(left, right),
        position=7, inserted=" ", removed="a",
    )


def test_text_delta_merge_replace_overlapping_suffix_pattern():
    # Pattern observed during multiline/multicursor edits where each new delta
    # replaces a suffix of the previous inserted text.
    deltas = [
        td(position=1679, inserted="1\n1", removed="\n"),
        td(position=1680, inserted="2\n12", removed="\n1"),
        td(position=1681, inserted="3\n123", removed="\n12"),
    ]

    merged = deltas[0]
    for nxt in deltas[1:]:
        merged = TextDelta.merge_text_delta(merged, nxt)
        assert merged is not None

    assert_delta(merged, position=1679, inserted="123\n123", removed="\n")


def test_text_delta_merge_replacement_inside_previous_insert_general_substring():
    left = td(position=5, inserted="abcdef", removed="")
    # replace 'cde' -> 'X' at position 7 (5 + 2)
    right = td(position=7, inserted="X", removed="cde")
    assert_delta(
        TextDelta.merge_text_delta(left, right),
        position=5, inserted="abXf", removed="",
    )


def test_text_delta_merge_partially_overlapping_removals_union():
    left = td(position=10, inserted="", removed="abcdef")
    right = td(position=14, inserted="", removed="efghi")
    assert_delta(
        TextDelta.merge_text_delta(left, right),
        position=10, inserted="", removed="abcdefghi",
    )


def test_text_delta_merge_insertion_bridges_prior_removal_becomes_replace():
    left = td(position=5, inserted="", removed="abc")
    right = td(position=5, inserted="X", removed="")
    assert_delta(
        TextDelta.merge_text_delta(left, right),
        position=5, inserted="X", removed="abc",
    )


def test_text_delta_merge_replace_then_sequential_inserts():
    # Reproduce: replace + two subsequent pure inserts should accumulate all
    # inserted chars, not just the last one.
    removed = "someintg=1\nsomething=2\nhahah=3\n\na\ns\nd\nas"
    d1 = td(position=14, inserted="o", removed=removed)
    d2 = td(position=15, inserted="b", removed="")
    d3 = td(position=16, inserted="s", removed="")
    m12 = TextDelta.merge_text_delta(d1, d2)
    assert_delta(m12, position=14, inserted="ob", removed=removed)
    m123 = TextDelta.merge_text_delta(m12, d3)
    assert_delta(m123, position=14, inserted="obs", removed=removed)


@pytest.mark.parametrize(
    "left,right",
    [
        # Non-adjacent inserts.
        (
            td(position=10, inserted="a", removed=""),
            td(position=12, inserted="b", removed=""),
        ),
        # Mixed insert/remove.
        (
            td(position=10, inserted="a", removed=""),
            td(position=10, inserted="", removed="x"),
        ),
        # Replace but removed doesn't match inserted (overwrite rule).
        (
            td(position=10, inserted="B", removed="A"),
            td(position=10, inserted="C", removed="X"),
        ),
    ],
)
def test_text_delta_merge_text_delta_none_for_non_matching_patterns(left, right):
    assert TextDelta.merge_text_delta(left, right) is None


# ---------------------------------------------------------------------------
# TextDelta.exploded
# ---------------------------------------------------------------------------

def test_text_delta_exploded_splits_wrap_replace_into_two_inserts():
    # Represents inserting "1" at two cursors with unchanged text between.
    delta = td(position=1954, inserted="1\n\n1", removed="\n\n")
    exploded = delta.exploded()
    assert len(exploded) == 2
    # First insert stays at the delta's start.
    assert_delta(exploded[0], position=1954, inserted="1")
    # Second insert lands after the two preserved newlines: two lines down,
    # column reset to 0.
    assert_delta(exploded[1], position=1957, inserted="1", line=2, col=0)


def test_text_delta_exploded_noop_for_non_replace_or_no_substring_match():
    assert_deltas(
        td(position=0, inserted="abc", removed="").exploded(),
        [(0, "abc", "")],
    )
    assert_deltas(
        td(position=0, inserted="abc", removed="xyz").exploded(),
        [(0, "abc", "xyz")],
    )


def test_text_delta_exploded_returns_original_when_removed_occurs_multiple_times():
    # If the removed text appears multiple times, we can't unambiguously split.
    delta = td(position=10, inserted="XaaYaaZ", removed="aa")
    assert_deltas(delta.exploded(), [(10, "XaaYaaZ", "aa")])


def test_text_delta_exploded_handles_prefix_or_suffix_only_inserts():
    # inserted = removed + suffix
    delta = td(position=10, inserted="aaZZ", removed="aa")
    assert_deltas(delta.exploded(), [(12, "ZZ", "")])

    # inserted = prefix + removed
    delta = td(position=10, inserted="ZZaa", removed="aa")
    assert_deltas(delta.exploded(), [(10, "ZZ", "")])


def test_text_delta_exploded_can_return_empty_delta_for_complete_cancellation():
    delta = td(position=10, inserted="abc", removed="abc")
    assert_deltas(delta.exploded(), [(13, "", "")])


# ---------------------------------------------------------------------------
# TextDelta.shift / net_length
# ---------------------------------------------------------------------------

def test_text_delta_shift_and_net_length():
    delta = td(position=10, inserted="abcd", removed="xy")
    assert delta.net_length() == 2
    assert delta.shift(0) is delta
    # A plain position shift does not move line/col (no col_shift given).
    assert_delta(delta.shift(5), position=15, inserted="abcd", removed="xy", col=10)
    # An explicit line/col shift moves all three coordinates.
    assert_delta(
        delta.shift(5, line_shift=1, col_shift=3),
        position=15, inserted="abcd", removed="xy", line=1, col=13,
    )


# ---------------------------------------------------------------------------
# EditBlock.merge
# ---------------------------------------------------------------------------

def test_edit_block_merge_rejects_empty_or_mismatched_before_state():
    base = EditBlock(
        before=CursorState(main_cursor=cursor(0), extra_cursors=()),
        deltas=[td(position=0, inserted="a", removed="")],
        after=CursorState(main_cursor=cursor(1), extra_cursors=()),
    )

    empty_other = EditBlock(
        before=CursorState(main_cursor=cursor(1), extra_cursors=()),
        deltas=[],
        after=CursorState(main_cursor=cursor(1), extra_cursors=()),
    )
    assert base.merge(empty_other) is False

    mismatched = EditBlock(
        # Add an extra cursor so `before` signature is definitely different
        before=CursorState(main_cursor=cursor(2), extra_cursors=(cursor(7),)),
        deltas=[td(position=1, inserted="b", removed="")],
        after=CursorState(main_cursor=cursor(3), extra_cursors=()),
    )
    assert base.merge(mismatched) is False


def test_edit_block_merge_copies_into_empty_block():
    empty = EditBlock(
        before=CursorState(main_cursor=cursor(0), extra_cursors=()),
        deltas=[],
        after=CursorState(main_cursor=cursor(0), extra_cursors=()),
    )

    other = EditBlock(
        before=CursorState(main_cursor=cursor(0), extra_cursors=()),
        deltas=[td(position=0, inserted="x", removed="")],
        after=CursorState(main_cursor=cursor(1), extra_cursors=()),
    )

    assert empty.merge(other)
    assert empty.deltas == other.deltas
    assert empty.after == other.after


def test_edit_block_merge_appends_unmergeable_delta_in_order():
    existing = EditBlock(
        before=CursorState(main_cursor=cursor(0), extra_cursors=()),
        deltas=[td(position=0, inserted="a", removed="")],
        after=CursorState(main_cursor=cursor(1), extra_cursors=()),
    )
    incoming = EditBlock(
        before=CursorState(main_cursor=cursor(1), extra_cursors=()),
        deltas=[td(position=50, inserted="b", removed="")],
        after=CursorState(main_cursor=cursor(2), extra_cursors=()),
    )

    assert existing.merge(incoming)
    assert_deltas(existing.deltas, [(0, "a", ""), (50, "b", "")])


def test_edit_block_merge_shifts_later_existing_deltas_when_length_changes():
    existing = EditBlock(
        before=CursorState(main_cursor=cursor(0), extra_cursors=()),
        deltas=[
            td(position=10, inserted="a", removed=""),
            td(position=20, inserted="X", removed=""),
        ],
        after=CursorState(main_cursor=cursor(1), extra_cursors=()),
    )
    incoming = EditBlock(
        before=CursorState(main_cursor=cursor(1), extra_cursors=()),
        deltas=[td(position=11, inserted="b", removed="")],
        after=CursorState(main_cursor=cursor(2), extra_cursors=()),
    )

    # First delta merges from 'a' -> 'ab' (length_diff=+1), so later delta shifts.
    assert existing.merge(incoming)
    assert_deltas(existing.deltas, [(10, "ab", ""), (21, "X", "")])


def test_edit_block_merge_shifts_later_existing_deltas_for_net_negative_length_diff():
    existing = EditBlock(
        before=CursorState(main_cursor=cursor(0), extra_cursors=()),
        deltas=[
            td(position=10, inserted="", removed="a"),
            td(position=20, inserted="X", removed=""),
        ],
        after=CursorState(main_cursor=cursor(1), extra_cursors=()),
    )
    incoming = EditBlock(
        before=CursorState(main_cursor=cursor(1), extra_cursors=()),
        deltas=[td(position=10, inserted="", removed="b")],
        after=CursorState(main_cursor=cursor(2), extra_cursors=()),
    )

    # First delta merges from remove 'a' -> remove 'ab' (length_diff=-1).
    assert existing.merge(incoming)
    assert_deltas(existing.deltas, [(10, "", "ab"), (19, "X", "")])


def test_edit_block_merge_does_not_shift_deltas_to_the_left_of_current_position():
    existing = EditBlock(
        before=CursorState(main_cursor=cursor(0), extra_cursors=()),
        deltas=[
            td(position=10, inserted="a", removed=""),
            td(position=5, inserted="X", removed=""),
        ],
        after=CursorState(main_cursor=cursor(1), extra_cursors=()),
    )
    incoming = EditBlock(
        before=CursorState(main_cursor=cursor(1), extra_cursors=()),
        deltas=[td(position=11, inserted="b", removed="")],
        after=CursorState(main_cursor=cursor(2), extra_cursors=()),
    )

    assert existing.merge(incoming)
    assert_delta(existing.deltas[0], position=10, inserted="ab", removed="")
    assert_delta(existing.deltas[1], position=5, inserted="X", removed="")


def test_merge_delta_lists_shifts_later_positions_for_multicursor_typing():
    # Two cursors typing sequentially can produce positions like:
    #   first keypress:  [p0 '1', p1 '1']
    #   second keypress: [p0+1 '2', p1+2 '2']
    # When the first delta merges to '12', the second delta must be shifted
    # to keep it mergeable and replayable.
    existing = EditBlock(
        before=CursorState(main_cursor=cursor(2180), extra_cursors=(cursor(2182),)),
        deltas=[
            td(position=2180, inserted="1", removed=""),
            td(position=2182, inserted="1", removed=""),
        ],
        after=CursorState(main_cursor=cursor(2181), extra_cursors=(cursor(2183),)),
    )

    incoming = EditBlock(
        before=CursorState(main_cursor=cursor(2181), extra_cursors=(cursor(2183),)),
        deltas=[
            td(position=2181, inserted="2", removed=""),
            td(position=2184, inserted="2", removed=""),
        ],
        after=CursorState(main_cursor=cursor(2182), extra_cursors=(cursor(2184),)),
    )

    assert existing.merge(incoming)
    assert_deltas(existing.deltas, [(2180, "12", ""), (2183, "12", "")])
    assert existing.after == incoming.after


def test_edit_block_merge_shifts_only_following_items_not_previous_ones():
    existing = EditBlock(
        before=CursorState(main_cursor=cursor(0), extra_cursors=()),
        deltas=[
            td(position=10, inserted="a", removed=""),
            td(position=15, inserted="b", removed=""),
            td(position=20, inserted="c", removed=""),
        ],
        after=CursorState(main_cursor=cursor(1), extra_cursors=()),
    )
    incoming = EditBlock(
        before=CursorState(main_cursor=cursor(1), extra_cursors=()),
        deltas=[td(position=16, inserted="B", removed="")],
        after=CursorState(main_cursor=cursor(2), extra_cursors=()),
    )

    # Merge into the middle delta: 'b' + 'B' -> 'bB' (length_diff=+1)
    assert existing.merge(incoming)
    assert_deltas(
        existing.deltas,
        [(10, "a", ""), (15, "bB", ""), (21, "c", "")],
    )


def test_edit_block_merge_shifts_same_position_later_deltas():
    # Multiple deltas at the same position: merging into the first should
    # shift the later one as well.
    existing = EditBlock(
        before=CursorState(main_cursor=cursor(0), extra_cursors=()),
        deltas=[
            td(position=10, inserted="a", removed=""),
            td(position=10, inserted="b", removed=""),
        ],
        after=CursorState(main_cursor=cursor(1), extra_cursors=()),
    )
    incoming = EditBlock(
        before=CursorState(main_cursor=cursor(1), extra_cursors=()),
        deltas=[td(position=11, inserted="d", removed="")],
        after=CursorState(main_cursor=cursor(2), extra_cursors=()),
    )

    assert existing.merge(incoming)
    assert_deltas(existing.deltas, [(10, "ad", ""), (11, "b", "")])
