from app.reports.pdf_gen import strip_markdown


def test_strip_bold():
    assert strip_markdown("**bold**") == "bold"


def test_strip_headers():
    assert strip_markdown("# Header") == "Header"


def test_strip_links():
    assert (
        strip_markdown("[OpenAI](https://openai.com)")
        == "OpenAI"
    )


def test_strip_inline_code():
    assert strip_markdown("Use `print()`") == "Use print()"


def test_strip_blockquote():
    assert strip_markdown("> quoted") == "quoted"


def test_strip_bullet_list():
    assert strip_markdown("- item") == "item"


def test_strip_numbered_list():
    assert strip_markdown("1. first") == "first"


def test_strip_image_markdown():
    assert strip_markdown("![Logo](logo.png)") == "Logo"


def test_strip_multiple_markdown():
    text = """
# Title

**Bold**

- Item 1
- Item 2

[Google](https://google.com)

`code`
"""

    result = strip_markdown(text)

    assert "Title" in result
    assert "Bold" in result
    assert "Item 1" in result
    assert "Google" in result
    assert "code" in result

    assert "#" not in result
    assert "**" not in result
    assert "[" not in result
    assert "](" not in result

