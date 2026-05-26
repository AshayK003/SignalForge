import os
import tempfile
import pytest

from app.utils.config import Config, load_config
from database.schema import init_db


@pytest.fixture
def tmp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def db(tmp_db_path):
    return init_db(tmp_db_path)


@pytest.fixture
def config():
    return load_config()


@pytest.fixture
def sample_text():
    return """Artificial intelligence is transforming every industry. From healthcare to finance, 
    machine learning models are being deployed to solve complex problems. However, there are significant 
    challenges around interpretability, bias, and regulation.

    Deep learning requires large amounts of data and compute resources. This creates a barrier to entry 
    for smaller organizations. Transfer learning and foundation models are helping to democratize access.

    The regulatory landscape is evolving rapidly. The EU AI Act represents one of the first comprehensive 
    attempts to regulate AI systems. Companies need to prepare for compliance requirements.

    On the technical side, researchers are making progress on model compression, quantization, and 
    efficient architectures. These advances will make AI more accessible and sustainable.

    The key insight is that the organizations that will win are not necessarily those with the best models, 
    but those that can integrate AI into their workflows effectively and responsibly."""


@pytest.fixture
def sample_pdf(tmp_path):
    path = tmp_path / "test.pdf"
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(612, 792)
    writer.write(str(path))
    return str(path)
