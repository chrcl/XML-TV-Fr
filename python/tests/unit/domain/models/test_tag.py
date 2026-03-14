"""Unit tests for Tag value object."""

from xmltvfr.domain.models.tag import Tag


def test_tag_null_value_xml():
    """Tag with None value renders as self-closing element."""
    tag = Tag(name="new", value=None, attributes={}, sorted_children=[])
    assert tag.as_xml() == "<new/>\n"


def test_tag_string_value_xml():
    """Tag with string value renders correctly."""
    tag = Tag(name="title", value="My Show", attributes={"lang": "fr"}, sorted_children=[])
    assert tag.as_xml() == '<title lang="fr">My Show</title>\n'


def test_tag_string_value_escaped_xml():
    """Tag with special chars in string value are escaped."""
    tag = Tag(name="title", value="Show & Tell <1>", attributes={}, sorted_children=[])
    assert tag.as_xml() == "<title>Show &amp; Tell &lt;1&gt;</title>\n"


def test_tag_children_xml():
    """Tag with children renders correctly."""
    child = Tag(name="title", value="Child Show", attributes={}, sorted_children=[])
    parent = Tag(name="programme", value={}, attributes={}, sorted_children=["title"])
    parent.add_child(child)
    xml = parent.as_xml()
    assert "<programme>" in xml
    assert "<title>Child Show</title>" in xml
    assert "</programme>" in xml


def test_tag_sorted_children():
    """Children appear in sorted order."""
    title = Tag(name="title", value="T", attributes={}, sorted_children=[])
    desc = Tag(name="desc", value="D", attributes={}, sorted_children=[])
    parent = Tag(name="programme", value={}, attributes={}, sorted_children=["title", "desc"])
    parent.add_child(desc)
    parent.add_child(title)
    xml = parent.as_xml()
    assert xml.index("<title>") < xml.index("<desc>")


def test_add_child_and_get_children():
    """add_child stores tag, get_children retrieves by name."""
    parent = Tag(name="parent", value={}, attributes={}, sorted_children=[])
    child1 = Tag(name="category", value="Drama", attributes={}, sorted_children=[])
    child2 = Tag(name="category", value="Thriller", attributes={}, sorted_children=[])
    parent.add_child(child1)
    parent.add_child(child2)
    children = parent.get_children("category")
    assert len(children) == 2
    assert children[0].value == "Drama"
    assert children[1].value == "Thriller"


def test_set_child_replaces():
    """set_child replaces all children with given name."""
    parent = Tag(name="parent", value={}, attributes={}, sorted_children=[])
    child1 = Tag(name="title", value="Old", attributes={}, sorted_children=[])
    child2 = Tag(name="title", value="New", attributes={}, sorted_children=[])
    parent.add_child(child1)
    parent.set_child(child2)
    children = parent.get_children("title")
    assert len(children) == 1
    assert children[0].value == "New"


def test_attributes_escaped():
    """Special chars in attributes are escaped."""
    tag = Tag(name="icon", value="", attributes={"src": "http://example.com/a&b.png"}, sorted_children=[])
    xml = tag.as_xml()
    assert 'src="http://example.com/a&amp;b.png"' in xml
