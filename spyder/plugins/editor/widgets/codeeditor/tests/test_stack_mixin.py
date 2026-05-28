# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Unit tests for custom undo stack delta normalization/merging."""

import pytest

from qtpy.QtGui import QTextCursor, QTextDocument

from spyder.plugins.editor.widgets.codeeditor.stack_mixin import TextDelta, EditBlock, CursorState


def create_cursor(position: int) -> QTextCursor:
    doc = QTextDocument()
    doc.setPlainText(" " * 10000)
    cursor = QTextCursor(doc)
    cursor.setPosition(position)
    return cursor


def create_selection_cursor(anchor: int, position: int) -> QTextCursor:
    doc = QTextDocument()
    doc.setPlainText(" " * 10000)
    cursor = QTextCursor(doc)
    cursor.setPosition(anchor)
    cursor.setPosition(position, QTextCursor.KeepAnchor)
    return cursor


def test_cursor_state_equality_uses_signature_not_identity():
    state1 = CursorState(
        main_cursor=create_cursor(10),
        extra_cursors=(create_selection_cursor(20, 25),),
    )
    state2 = CursorState(
        main_cursor=create_cursor(10),
        extra_cursors=(create_selection_cursor(20, 25),),
    )
    assert state1 == state2
    assert state1.signature() == state2.signature()


def test_cursor_state_inequality_detects_anchor_change():
    state1 = CursorState(
        main_cursor=create_selection_cursor(10, 12),
        extra_cursors=(),
    )
    # Different extra_cursors should make the signature differ reliably
    state2 = CursorState(
        main_cursor=create_selection_cursor(10, 12),
        extra_cursors=(create_cursor(5),),
    )
    assert state1 != state2


def test_text_delta_normalized_strips_common_prefix_suffix():
    delta = TextDelta(position=10, removed_text="abcYdef", inserted_text="abcXdef")
    assert delta.normalized() == TextDelta(position=13, removed_text="Y", inserted_text="X")


def test_text_delta_normalized_returns_self_for_pure_insert_or_remove():
    insert_only = TextDelta(position=5, inserted_text="abc", removed_text="")
    remove_only = TextDelta(position=5, inserted_text="", removed_text="abc")
    assert insert_only.normalized() is insert_only
    assert remove_only.normalized() is remove_only


def test_text_delta_normalized_can_cancel_replace_to_empty_delta():
    # If inserted == removed, the net effect is a no-op; normalization reduces
    # to empty strings (and advances position by the stripped prefix).
    delta = TextDelta(position=100, inserted_text="abc", removed_text="abc")
    assert delta.normalized() == TextDelta(position=103, inserted_text="", removed_text="")


def test_text_delta_normalized_strips_only_prefix_or_only_suffix():
    prefix = TextDelta(position=0, inserted_text="abcX", removed_text="abcY")
    assert prefix.normalized() == TextDelta(position=3, inserted_text="X", removed_text="Y")

    suffix = TextDelta(position=10, inserted_text="Xdef", removed_text="Ydef")
    assert suffix.normalized() == TextDelta(position=10, inserted_text="X", removed_text="Y")


def test_text_delta_merge_replace_overwrite_same_position():
    left = TextDelta(position=5, removed_text="abc", inserted_text="def")
    right = TextDelta(position=5, removed_text="def", inserted_text="xyz")
    merged = TextDelta.merge_text_delta(left, right)
    assert merged == TextDelta(position=5, removed_text="abc", inserted_text="xyz")


def test_text_delta_merge_sequential_inserts_concatenate():
    left = TextDelta(position=10, inserted_text="ab", removed_text="")
    right = TextDelta(position=12, inserted_text="cd", removed_text="")
    assert TextDelta.merge_text_delta(left, right) == TextDelta(
        position=10, inserted_text="abcd", removed_text=""
    )


def test_text_delta_merge_sequential_removals_to_right_concatenate():
    left = TextDelta(position=10, inserted_text="", removed_text="ab")
    right = TextDelta(position=10, inserted_text="", removed_text="cd")
    assert TextDelta.merge_text_delta(left, right) == TextDelta(
        position=10, inserted_text="", removed_text="abcd"
    )


def test_text_delta_merge_sequential_removals_to_left_concatenate():
    left = TextDelta(position=12, inserted_text="", removed_text="cd")
    right = TextDelta(position=10, inserted_text="", removed_text="ab")
    assert TextDelta.merge_text_delta(left, right) == TextDelta(
        position=10, inserted_text="", removed_text="abcd"
    )


def test_text_delta_merge_replace_overlapping_prefix_pattern():
    left = TextDelta(position=10, inserted_text="ABC", removed_text="xxx")
    right = TextDelta(position=10, inserted_text="12", removed_text="AB")
    assert TextDelta.merge_text_delta(left, right) == TextDelta(
        position=10, inserted_text="12C", removed_text="xxx"
    )


def test_text_delta_merge_returns_none_for_unrelated_deltas():
    left = TextDelta(position=10, inserted_text="a", removed_text="")
    right = TextDelta(position=50, inserted_text="b", removed_text="")
    assert TextDelta.merge_text_delta(left, right) is None


def test_text_delta_merge_removal_of_recent_insert_collapses_insert_stream():
    left = TextDelta(position=0, inserted_text="this isas", removed_text="")
    right = TextDelta(position=8, inserted_text="", removed_text="s")
    assert TextDelta.merge_text_delta(left, right) == TextDelta(
        position=0, inserted_text="this isa", removed_text=""
    )


def test_text_delta_merge_remove_then_insert_same_position_becomes_replace():
    left = TextDelta(position=7, inserted_text="", removed_text="a")
    right = TextDelta(position=7, inserted_text=" ", removed_text="")
    assert TextDelta.merge_text_delta(left, right) == TextDelta(
        position=7, inserted_text=" ", removed_text="a"
    )


def test_text_delta_merge_replace_overlapping_suffix_pattern():
    # Pattern observed during multiline/multicursor edits where each new delta
    # replaces a suffix of the previous inserted text.
    deltas = [
        TextDelta(position=1679, inserted_text="1\n1", removed_text="\n"),
        TextDelta(position=1680, inserted_text="2\n12", removed_text="\n1"),
        TextDelta(position=1681, inserted_text="3\n123", removed_text="\n12"),
    ]

    merged = deltas[0]
    for nxt in deltas[1:]:
        merged = TextDelta.merge_text_delta(merged, nxt)
        assert merged is not None

    assert merged == TextDelta(position=1679, inserted_text="123\n123", removed_text="\n")


def test_text_delta_exploded_splits_wrap_replace_into_two_inserts():
    # Represents inserting "1" at two cursors with unchanged text between.
    delta = TextDelta(position=1954, inserted_text="1\n\n1", removed_text="\n\n")
    exploded = delta.exploded()
    assert exploded == (
        TextDelta(position=1954, inserted_text="1", removed_text=""),
        TextDelta(position=1957, inserted_text="1", removed_text=""),
    )


def test_text_delta_exploded_noop_for_non_replace_or_no_substring_match():
    assert TextDelta(position=0, inserted_text="abc", removed_text="").exploded() == (
        TextDelta(position=0, inserted_text="abc", removed_text=""),
    )
    assert TextDelta(position=0, inserted_text="abc", removed_text="xyz").exploded() == (
        TextDelta(position=0, inserted_text="abc", removed_text="xyz"),
    )


def test_text_delta_exploded_returns_original_when_removed_occurs_multiple_times():
    # If the removed text appears multiple times, we can't unambiguously split.
    delta = TextDelta(position=10, inserted_text="XaaYaaZ", removed_text="aa")
    assert delta.exploded() == (delta.normalized(),)


def test_text_delta_exploded_handles_prefix_or_suffix_only_inserts():
    # inserted = removed + suffix
    delta = TextDelta(position=10, inserted_text="aaZZ", removed_text="aa")
    assert delta.exploded() == (
        TextDelta(position=12, inserted_text="ZZ", removed_text=""),
    )

    # inserted = prefix + removed
    delta = TextDelta(position=10, inserted_text="ZZaa", removed_text="aa")
    assert delta.exploded() == (
        TextDelta(position=10, inserted_text="ZZ", removed_text=""),
    )


def test_text_delta_exploded_can_return_empty_delta_for_complete_cancellation():
    delta = TextDelta(position=10, inserted_text="abc", removed_text="abc")
    assert delta.exploded() == (TextDelta(position=13, inserted_text="", removed_text=""),)


def test_text_delta_shift_and_net_length():
    delta = TextDelta(position=10, inserted_text="abcd", removed_text="xy")
    assert delta.net_length() == 2
    assert delta.shift(0) is delta
    assert delta.shift(5) == TextDelta(position=15, inserted_text="abcd", removed_text="xy")


def test_edit_block_merge_rejects_empty_or_mismatched_before_state():
    base = EditBlock(
        before=CursorState(main_cursor=create_cursor(0), extra_cursors=()),
        deltas=[TextDelta(position=0, inserted_text="a", removed_text="")],
        after=CursorState(main_cursor=create_cursor(1), extra_cursors=()),
    )

    empty_other = EditBlock(
        before=CursorState(main_cursor=create_cursor(1), extra_cursors=()),
        deltas=[],
        after=CursorState(main_cursor=create_cursor(1), extra_cursors=()),
    )
    assert base.merge(empty_other) is False

    mismatched = EditBlock(
        # Add an extra cursor so `before` signature is definitely different
        before=CursorState(main_cursor=create_cursor(2), extra_cursors=(create_cursor(7),)),
        deltas=[TextDelta(position=1, inserted_text="b", removed_text="")],
        after=CursorState(main_cursor=create_cursor(3), extra_cursors=()),
    )
    assert base.merge(mismatched) is False


def test_edit_block_merge_copies_into_empty_block():
    empty = EditBlock(
        before=CursorState(main_cursor=create_cursor(0), extra_cursors=()),
        deltas=[],
        after=CursorState(main_cursor=create_cursor(0), extra_cursors=()),
    )

    other = EditBlock(
        before=CursorState(main_cursor=create_cursor(0), extra_cursors=()),
        deltas=[TextDelta(position=0, inserted_text="x", removed_text="")],
        after=CursorState(main_cursor=create_cursor(1), extra_cursors=()),
    )

    assert empty.merge(other)
    assert empty.deltas == other.deltas
    assert empty.after == other.after


def test_edit_block_merge_appends_unmergeable_delta_in_order():
    existing = EditBlock(
        before=CursorState(main_cursor=create_cursor(0), extra_cursors=()),
        deltas=[TextDelta(position=0, inserted_text="a", removed_text="")],
        after=CursorState(main_cursor=create_cursor(1), extra_cursors=()),
    )
    incoming = EditBlock(
        before=CursorState(main_cursor=create_cursor(1), extra_cursors=()),
        deltas=[TextDelta(position=50, inserted_text="b", removed_text="")],
        after=CursorState(main_cursor=create_cursor(2), extra_cursors=()),
    )

    assert existing.merge(incoming)
    assert existing.deltas == [
        TextDelta(position=0, inserted_text="a", removed_text=""),
        TextDelta(position=50, inserted_text="b", removed_text=""),
    ]


def test_edit_block_merge_shifts_later_existing_deltas_when_length_changes():
    existing = EditBlock(
        before=CursorState(main_cursor=create_cursor(0), extra_cursors=()),
        deltas=[
            TextDelta(position=10, inserted_text="a", removed_text=""),
            TextDelta(position=20, inserted_text="X", removed_text=""),
        ],
        after=CursorState(main_cursor=create_cursor(1), extra_cursors=()),
    )
    incoming = EditBlock(
        before=CursorState(main_cursor=create_cursor(1), extra_cursors=()),
        deltas=[TextDelta(position=11, inserted_text="b", removed_text="")],
        after=CursorState(main_cursor=create_cursor(2), extra_cursors=()),
    )

    # First delta merges from 'a' -> 'ab' (length_diff=+1), so later delta shifts.
    assert existing.merge(incoming)
    assert existing.deltas == [
        TextDelta(position=10, inserted_text="ab", removed_text=""),
        TextDelta(position=21, inserted_text="X", removed_text=""),
    ]


def test_edit_block_merge_shifts_later_existing_deltas_for_net_negative_length_diff():
    existing = EditBlock(
        before=CursorState(main_cursor=create_cursor(0), extra_cursors=()),
        deltas=[
            TextDelta(position=10, inserted_text="", removed_text="a"),
            TextDelta(position=20, inserted_text="X", removed_text=""),
        ],
        after=CursorState(main_cursor=create_cursor(1), extra_cursors=()),
    )
    incoming = EditBlock(
        before=CursorState(main_cursor=create_cursor(1), extra_cursors=()),
        deltas=[TextDelta(position=10, inserted_text="", removed_text="b")],
        after=CursorState(main_cursor=create_cursor(2), extra_cursors=()),
    )

    # First delta merges from remove 'a' -> remove 'ab' (length_diff=-1).
    assert existing.merge(incoming)
    assert existing.deltas == [
        TextDelta(position=10, inserted_text="", removed_text="ab"),
        TextDelta(position=19, inserted_text="X", removed_text=""),
    ]


def test_edit_block_merge_does_not_shift_deltas_to_the_left_of_current_position():
    existing = EditBlock(
        before=CursorState(main_cursor=create_cursor(0), extra_cursors=()),
        deltas=[
            TextDelta(position=10, inserted_text="a", removed_text=""),
            TextDelta(position=5, inserted_text="X", removed_text=""),
        ],
        after=CursorState(main_cursor=create_cursor(1), extra_cursors=()),
    )
    incoming = EditBlock(
        before=CursorState(main_cursor=create_cursor(1), extra_cursors=()),
        deltas=[TextDelta(position=11, inserted_text="b", removed_text="")],
        after=CursorState(main_cursor=create_cursor(2), extra_cursors=()),
    )

    assert existing.merge(incoming)
    assert existing.deltas[0] == TextDelta(position=10, inserted_text="ab", removed_text="")
    assert existing.deltas[1] == TextDelta(position=5, inserted_text="X", removed_text="")


def test_merge_delta_lists_shifts_later_positions_for_multicursor_typing():
    # Two cursors typing sequentially can produce positions like:
    #   first keypress:  [p0 '1', p1 '1']
    #   second keypress: [p0+1 '2', p1+2 '2']
    # When the first delta merges to '12', the second delta must be shifted
    # to keep it mergeable and replayable.
    existing = EditBlock(
        before=CursorState(main_cursor=create_cursor(2180), extra_cursors=(create_cursor(2182),)),
        deltas=[
            TextDelta(position=2180, inserted_text="1", removed_text=""),
            TextDelta(position=2182, inserted_text="1", removed_text=""),
        ],
        after=CursorState(main_cursor=create_cursor(2181), extra_cursors=(create_cursor(2183),))
    )

    incoming = EditBlock(
        before=CursorState(main_cursor=create_cursor(2181), extra_cursors=(create_cursor(2183),)),
        deltas= [
            TextDelta(position=2181, inserted_text="2", removed_text=""),
            TextDelta(position=2184, inserted_text="2", removed_text=""),
        ],
        after=CursorState(main_cursor=create_cursor(2182), extra_cursors=(create_cursor(2184),))
    )
    
    assert existing.merge(incoming)
    assert existing.deltas == [
        TextDelta(position=2180, inserted_text="12", removed_text=""),
        TextDelta(position=2183, inserted_text="12", removed_text=""),
    ]
    assert existing.after == incoming.after


def test_edit_block_merge_shifts_only_following_items_not_previous_ones():
    existing = EditBlock(
        before=CursorState(main_cursor=create_cursor(0), extra_cursors=()),
        deltas=[
            TextDelta(position=10, inserted_text="a", removed_text=""),
            TextDelta(position=15, inserted_text="b", removed_text=""),
            TextDelta(position=20, inserted_text="c", removed_text=""),
        ],
        after=CursorState(main_cursor=create_cursor(1), extra_cursors=()),
    )
    incoming = EditBlock(
        before=CursorState(main_cursor=create_cursor(1), extra_cursors=()),
        deltas=[TextDelta(position=16, inserted_text="B", removed_text="")],
        after=CursorState(main_cursor=create_cursor(2), extra_cursors=()),
    )

    # Merge into the middle delta: 'b' + 'B' -> 'bB' (length_diff=+1)
    assert existing.merge(incoming)
    assert existing.deltas == [
        TextDelta(position=10, inserted_text="a", removed_text=""),
        TextDelta(position=15, inserted_text="bB", removed_text=""),
        TextDelta(position=21, inserted_text="c", removed_text=""),
    ]


@pytest.mark.parametrize(
    "left,right",
    [
        # Non-adjacent inserts.
        (
            TextDelta(position=10, inserted_text="a", removed_text=""),
            TextDelta(position=12, inserted_text="b", removed_text=""),
        ),
        # Mixed insert/remove.
        (
            TextDelta(position=10, inserted_text="a", removed_text=""),
            TextDelta(position=10, inserted_text="", removed_text="x"),
        ),
        # Replace but removed doesn't match inserted (overwrite rule).
        (
            TextDelta(position=10, inserted_text="B", removed_text="A"),
            TextDelta(position=10, inserted_text="C", removed_text="X"),
        ),
    ],
)
def test_text_delta_merge_text_delta_none_for_non_matching_patterns(left, right):
    assert TextDelta.merge_text_delta(left, right) is None


def test_text_delta_merge_replacement_inside_previous_insert_general_substring():
    left = TextDelta(position=5, inserted_text="abcdef", removed_text="")
    # replace 'cde' -> 'X' at position 7 (5 + 2)
    right = TextDelta(position=7, inserted_text="X", removed_text="cde")
    merged = TextDelta.merge_text_delta(left, right)
    assert merged == TextDelta(position=5, inserted_text="abXf", removed_text="")


def test_text_delta_merge_partially_overlapping_removals_union():
    left = TextDelta(position=10, inserted_text="", removed_text="abcdef")
    right = TextDelta(position=14, inserted_text="", removed_text="efghi")
    merged = TextDelta.merge_text_delta(left, right)
    assert merged == TextDelta(position=10, inserted_text="", removed_text="abcdefghi")


def test_text_delta_merge_insertion_bridges_prior_removal_becomes_replace():
    left = TextDelta(position=5, inserted_text="", removed_text="abc")
    # insert at end of removed region -> should become replace at left.position
    right = TextDelta(position=8, inserted_text="X", removed_text="")
    merged = TextDelta.merge_text_delta(left, right)
    assert merged == TextDelta(position=5, inserted_text="X", removed_text="abc")


def test_edit_block_merge_shifts_same_position_later_deltas():
    # Multiple deltas at the same position: merging into the first should
    # shift the later one as well.
    existing = EditBlock(
        before=CursorState(main_cursor=create_cursor(0), extra_cursors=()),
        deltas=[
            TextDelta(position=10, inserted_text="a", removed_text=""),
            TextDelta(position=10, inserted_text="b", removed_text=""),
        ],
        after=CursorState(main_cursor=create_cursor(1), extra_cursors=()),
    )
    incoming = EditBlock(
        before=CursorState(main_cursor=create_cursor(1), extra_cursors=()),
        deltas=[TextDelta(position=11, inserted_text="d", removed_text="")],
        after=CursorState(main_cursor=create_cursor(2), extra_cursors=()),
    )

    assert existing.merge(incoming)
    assert existing.deltas == [
        TextDelta(position=10, inserted_text="ad", removed_text=""),
        TextDelta(position=11, inserted_text="b", removed_text=""),
    ]
