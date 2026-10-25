from radarwindow.publisher.blotato import split_for_x


def test_short_text_single_tweet():
    assert split_for_x("hello world") == ["hello world"]


def test_exactly_280_single():
    t = "a" * 280
    assert split_for_x(t) == [t]


def test_splits_on_paragraphs():
    text = ("First paragraph about a signal that matters this week. " * 3).strip()
    text = text + "\n\n" + ("Second paragraph with the analysis and the numbers. " * 3).strip()
    parts = split_for_x(text)
    assert len(parts) >= 2
    assert all(len(p) <= 280 for p in parts)


def test_splits_on_sentences_when_no_paragraphs():
    text = ("This is a sentence about model pricing that runs on. " * 8).strip()
    parts = split_for_x(text)
    assert len(parts) >= 2
    assert all(len(p) <= 280 for p in parts)
    # No content lost (ignoring whitespace normalisation)
    assert "".join(parts).replace(" ", "") == text.replace(" ", "").replace("\n", "")


def test_hard_wraps_pathological_long_word():
    text = "x" * 700
    parts = split_for_x(text)
    assert all(len(p) <= 280 for p in parts)
    assert sum(len(p) for p in parts) == 700
