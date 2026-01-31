from src.crawler.parser import DefaultHTMLParser

# Minimal HTML sample for testing
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
    <meta property="article:published_time" content="2023-01-01">
</head>
<body>
    <header>Ignored Header</header>
    <nav>Ignored Nav</nav>
    <main>
        <h1>Main Title</h1>
        <p>This is the main content.</p>
        <img src="/img/test.jpg" alt="Test Image" width="100" height="100">
        <a href="/internal">Link 1</a>
    </main>
    <footer>Ignored Footer</footer>
</body>
</html>
"""

def test_parser_extraction():
    parser = DefaultHTMLParser()
    url = "https://example.com/page"

    result = parser.parse(url, SAMPLE_HTML)

    # 1. Assert Basic Fields
    assert result["url"] == url
    assert result["title"] == "Test Page"

    # 2. Assert Content (Noise Removal Check)
    # Header, Nav, Footer should be gone
    assert "Ignored Header" not in result["content"]
    assert "Main Title" in result["content"]
    assert "This is the main content." in result["content"]

    # 3. Assert Metadata
    assert result["published_at"] == "2023-01-01"

    # 4. Assert Images
    # Should find 1 image, normalized to absolute URL
    assert len(result["images"]) == 1
    image = result["images"][0]
    assert image["url"] == "https://example.com/img/test.jpg"
    assert image["alt"] == "Test Image"
    assert "hash" in image # Hash generation logic check

    # 5. Assert Links
    # LinkExtractor integration check
    assert "https://example.com/internal" in result["links"]
