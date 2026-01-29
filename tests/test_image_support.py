import base64
import io
import pytest
from PIL import Image, ImageDraw

from deubot.agent import GermanLearningAgent, MessageOutput
from deubot.database import PhrasesDB
from deubot.message import UserMessage


def create_test_image_with_text(text: str) -> bytes:
    """Create a test image with the given text."""
    img = Image.new("RGB", (200, 100), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 40), text, fill="black")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.mark.unit
def test_user_message_text_only():
    """UserMessage with text only works correctly."""
    msg = UserMessage(text="Hello")
    assert msg.text == "Hello"
    assert msg.image_base64 is None


@pytest.mark.unit
def test_user_message_with_image():
    """UserMessage with image and caption works correctly."""
    image_bytes = create_test_image_with_text("Test")
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    msg = UserMessage(text="What is this?", image_base64=image_b64)
    assert msg.text == "What is this?"
    assert msg.image_base64 == image_b64


@pytest.mark.unit
def test_build_user_content_text_only(tmp_path):
    """Agent builds simple string content for text-only messages."""
    db = PhrasesDB(str(tmp_path / "phrases.json.gz"))
    agent = GermanLearningAgent(
        api_key="fake-key",
        model="gpt-4o",
        light_model="gpt-4o-mini",
        db=db,
    )
    msg = UserMessage(text="Hello world")
    content = agent._build_user_content(msg)
    assert content == "Hello world"


@pytest.mark.unit
def test_build_user_content_with_image(tmp_path):
    """Agent builds content array for messages with images."""
    db = PhrasesDB(str(tmp_path / "phrases.json.gz"))
    agent = GermanLearningAgent(
        api_key="fake-key",
        model="gpt-4o",
        light_model="gpt-4o-mini",
        db=db,
    )
    image_bytes = create_test_image_with_text("Test")
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    msg = UserMessage(text="Describe this", image_base64=image_b64)
    content = agent._build_user_content(msg)

    assert isinstance(content, list)
    assert len(content) == 2
    assert content[0]["type"] == "input_text"
    assert content[0]["text"] == "Describe this"
    assert content[1]["type"] == "input_image"
    assert content[1]["image_url"].startswith("data:image/jpeg;base64,")


@pytest.mark.unit
def test_build_user_content_image_no_caption(tmp_path):
    """Agent uses default prompt when image has no caption."""
    db = PhrasesDB(str(tmp_path / "phrases.json.gz"))
    agent = GermanLearningAgent(
        api_key="fake-key",
        model="gpt-4o",
        light_model="gpt-4o-mini",
        db=db,
    )
    image_bytes = create_test_image_with_text("Test")
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    msg = UserMessage(image_base64=image_b64)
    content = agent._build_user_content(msg)

    assert isinstance(content, list)
    assert content[0]["text"] == "What's in this image?"


@pytest.mark.llm
def test_agent_processes_image_with_german_word(agent):
    """Agent can process an image containing German text."""
    image_bytes = create_test_image_with_text("Hund")
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    msg = UserMessage(text="What German word is in this image?", image_base64=image_b64)

    outputs = list(agent.process_message(msg))

    # Should have at least one message output
    message_outputs = [o for o in outputs if isinstance(o, MessageOutput)]
    assert len(message_outputs) > 0

    # The response should mention "Hund" or "dog"
    response_text = " ".join(o.message for o in message_outputs).lower()
    assert "hund" in response_text or "dog" in response_text


@pytest.mark.llm
def test_agent_processes_text_only_message(agent):
    """Agent still works with text-only UserMessage."""
    msg = UserMessage(text="Translate 'hello' to German")

    outputs = list(agent.process_message(msg))

    message_outputs = [o for o in outputs if isinstance(o, MessageOutput)]
    assert len(message_outputs) > 0

    response_text = " ".join(o.message for o in message_outputs).lower()
    assert "hallo" in response_text
