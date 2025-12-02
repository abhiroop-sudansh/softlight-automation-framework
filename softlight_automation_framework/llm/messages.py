"""Message types for LLM communication."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


@dataclass
class ImageContent:
    """Image content for vision models."""
    
    url: str  # Can be base64 data URL or HTTP URL
    media_type: str = "image/png"
    detail: Literal["auto", "low", "high"] = "auto"
    
    @classmethod
    def from_base64(
        cls,
        base64_data: str,
        media_type: str = "image/png",
        detail: Literal["auto", "low", "high"] = "auto"
    ) -> "ImageContent":
        """Create from base64 encoded image data."""
        url = f"data:{media_type};base64,{base64_data}"
        return cls(url=url, media_type=media_type, detail=detail)
    
    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI API format."""
        return {
            "type": "image_url",
            "image_url": {
                "url": self.url,
                "detail": self.detail,
            }
        }


@dataclass
class Message:
    """Base message class."""
    
    role: Literal["system", "user", "assistant"]
    content: Union[str, List[Union[str, ImageContent]]]
    name: Optional[str] = None
    cache: bool = False  # For API caching hints
    
    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI API format."""
        msg: Dict[str, Any] = {"role": self.role}
        
        if isinstance(self.content, str):
            msg["content"] = self.content
        else:
            # Multi-part content (text + images)
            parts = []
            for item in self.content:
                if isinstance(item, str):
                    parts.append({"type": "text", "text": item})
                elif isinstance(item, ImageContent):
                    parts.append(item.to_openai_format())
            msg["content"] = parts
        
        if self.name:
            msg["name"] = self.name
        
        return msg


@dataclass
class SystemMessage(Message):
    """System message for LLM instructions."""
    
    role: Literal["system"] = field(default="system", init=False)
    
    def __init__(
        self,
        content: str,
        name: Optional[str] = None,
        cache: bool = True
    ):
        super().__init__(
            role="system",
            content=content,
            name=name,
            cache=cache
        )


@dataclass
class UserMessage(Message):
    """User message (includes browser state and screenshots)."""
    
    role: Literal["user"] = field(default="user", init=False)
    
    def __init__(
        self,
        content: Union[str, List[Union[str, ImageContent]]],
        name: Optional[str] = None,
        cache: bool = True
    ):
        super().__init__(
            role="user",
            content=content,
            name=name,
            cache=cache
        )
    
    @classmethod
    def with_screenshot(
        cls,
        text: str,
        screenshot_b64: str,
        detail: Literal["auto", "low", "high"] = "auto"
    ) -> "UserMessage":
        """Create a user message with text and screenshot."""
        image = ImageContent.from_base64(screenshot_b64, detail=detail)
        return cls(content=[text, image])
    
    @classmethod
    def with_multiple_images(
        cls,
        text: str,
        images: List[str],
        detail: Literal["auto", "low", "high"] = "auto"
    ) -> "UserMessage":
        """Create a user message with text and multiple images."""
        content: List[Union[str, ImageContent]] = [text]
        for img_b64 in images:
            content.append(ImageContent.from_base64(img_b64, detail=detail))
        return cls(content=content)


@dataclass
class AssistantMessage(Message):
    """Assistant message (LLM response)."""
    
    role: Literal["assistant"] = field(default="assistant", init=False)
    tool_calls: Optional[List[Dict[str, Any]]] = None
    
    def __init__(
        self,
        content: str,
        name: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        cache: bool = False
    ):
        super().__init__(
            role="assistant",
            content=content,
            name=name,
            cache=cache
        )
        self.tool_calls = tool_calls
    
    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI API format."""
        msg = super().to_openai_format()
        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls
        return msg


class MessageHistory:
    """Manages conversation message history."""
    
    def __init__(self, max_messages: Optional[int] = None):
        """
        Initialize message history.
        
        Args:
            max_messages: Maximum number of messages to keep (None = unlimited)
        """
        self._messages: List[Message] = []
        self._max_messages = max_messages
        self._system_message: Optional[SystemMessage] = None
    
    def set_system_message(self, message: SystemMessage) -> None:
        """Set the system message (always kept)."""
        self._system_message = message
    
    def add(self, message: Message) -> None:
        """Add a message to history."""
        self._messages.append(message)
        self._truncate_if_needed()
    
    def add_user(self, content: Union[str, List[Union[str, ImageContent]]]) -> None:
        """Add a user message."""
        self.add(UserMessage(content=content))
    
    def add_assistant(self, content: str) -> None:
        """Add an assistant message."""
        self.add(AssistantMessage(content=content))
    
    def get_messages(self) -> List[Message]:
        """Get all messages including system message."""
        messages = []
        if self._system_message:
            messages.append(self._system_message)
        messages.extend(self._messages)
        return messages
    
    def to_openai_format(self) -> List[Dict[str, Any]]:
        """Convert all messages to OpenAI API format."""
        return [msg.to_openai_format() for msg in self.get_messages()]
    
    def _truncate_if_needed(self) -> None:
        """Truncate history if max_messages is set."""
        if self._max_messages and len(self._messages) > self._max_messages:
            # Keep only the most recent messages
            self._messages = self._messages[-self._max_messages:]
    
    def clear(self) -> None:
        """Clear message history (keeps system message)."""
        self._messages.clear()
    
    def __len__(self) -> int:
        """Get number of messages (excluding system)."""
        return len(self._messages)
    
    def get_last_assistant_message(self) -> Optional[AssistantMessage]:
        """Get the last assistant message."""
        for msg in reversed(self._messages):
            if isinstance(msg, AssistantMessage):
                return msg
        return None

