"""Data models for browser state and operations."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class BrowserStateType(str, Enum):
    """Types of browser state."""
    IDLE = "idle"
    NAVIGATING = "navigating"
    LOADING = "loading"
    INTERACTIVE = "interactive"
    COMPLETE = "complete"


@dataclass
class ViewportInfo:
    """Information about the browser viewport."""
    width: int
    height: int
    device_pixel_ratio: float = 1.0
    
    @property
    def css_width(self) -> int:
        """Get CSS pixel width."""
        return int(self.width / self.device_pixel_ratio)
    
    @property
    def css_height(self) -> int:
        """Get CSS pixel height."""
        return int(self.height / self.device_pixel_ratio)


@dataclass
class ScrollPosition:
    """Current scroll position of a page or element."""
    x: float = 0.0
    y: float = 0.0
    max_x: float = 0.0
    max_y: float = 0.0
    
    @property
    def at_top(self) -> bool:
        """Check if scrolled to top."""
        return self.y <= 0
    
    @property
    def at_bottom(self) -> bool:
        """Check if scrolled to bottom."""
        return self.y >= self.max_y
    
    @property
    def pages_above(self) -> float:
        """Number of viewport heights above current position."""
        return self.y / max(self.max_y, 1)
    
    @property
    def pages_below(self) -> float:
        """Number of viewport heights below current position."""
        return (self.max_y - self.y) / max(self.max_y, 1)


@dataclass
class TabInfo:
    """Information about a browser tab."""
    target_id: str
    url: str
    title: str
    is_active: bool = False
    
    @property
    def short_id(self) -> str:
        """Get last 4 characters of target ID for display."""
        return self.target_id[-4:] if len(self.target_id) >= 4 else self.target_id


@dataclass
class PageInfo:
    """Information about the current page."""
    url: str
    title: str
    viewport: ViewportInfo
    scroll: ScrollPosition
    ready_state: str = "complete"
    is_pdf: bool = False
    
    @property
    def domain(self) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        parsed = urlparse(self.url)
        return parsed.netloc


class InteractiveElement(BaseModel):
    """An interactive element on the page."""
    
    index: int = Field(description="Unique index for referencing")
    tag_name: str = Field(description="HTML tag name")
    text: str = Field(default="", description="Visible text content")
    attributes: Dict[str, str] = Field(default_factory=dict, description="HTML attributes")
    
    # Position and size
    x: float = Field(default=0.0, description="X coordinate")
    y: float = Field(default=0.0, description="Y coordinate")
    width: float = Field(default=0.0, description="Element width")
    height: float = Field(default=0.0, description="Element height")
    
    # State
    is_visible: bool = Field(default=True, description="Element is visible")
    is_enabled: bool = Field(default=True, description="Element is enabled")
    is_editable: bool = Field(default=False, description="Element accepts input")
    is_clickable: bool = Field(default=True, description="Element can be clicked")
    
    # Accessibility
    role: Optional[str] = Field(default=None, description="ARIA role")
    aria_label: Optional[str] = Field(default=None, description="ARIA label")
    
    # Parent/child relationships
    parent_index: Optional[int] = Field(default=None, description="Parent element index")
    depth: int = Field(default=0, description="Nesting depth")
    is_new: bool = Field(default=False, description="Element appeared since last state")
    
    @property
    def center_x(self) -> float:
        """Get center X coordinate."""
        return self.x + self.width / 2
    
    @property
    def center_y(self) -> float:
        """Get center Y coordinate."""
        return self.y + self.height / 2
    
    def get_attribute(self, name: str, default: str = "") -> str:
        """Safely get an attribute value."""
        return self.attributes.get(name, default)
    
    def to_llm_string(self, include_position: bool = False) -> str:
        """Format element for LLM consumption."""
        prefix = "*" if self.is_new else ""
        attrs = []
        
        # Add key attributes
        if self.aria_label:
            attrs.append(f"aria-label='{self.aria_label}'")
        if self.role:
            attrs.append(f"role='{self.role}'")
        if "placeholder" in self.attributes:
            attrs.append(f"placeholder='{self.attributes['placeholder']}'")
        if "type" in self.attributes and self.tag_name.lower() == "input":
            attrs.append(f"type='{self.attributes['type']}'")
        if "href" in self.attributes:
            href = self.attributes["href"]
            if len(href) > 50:
                href = href[:47] + "..."
            attrs.append(f"href='{href}'")
        
        attr_str = " " + " ".join(attrs) if attrs else ""
        text = self.text[:50] + "..." if len(self.text) > 50 else self.text
        
        result = f"{prefix}[{self.index}]<{self.tag_name}{attr_str}>{text}</{self.tag_name}>"
        
        if include_position:
            result += f" @({self.x:.0f},{self.y:.0f})"
        
        return result
    
    def get_description(self) -> str:
        """Get a human-readable description of the element."""
        # Priority: aria-label > text > placeholder > tag name
        if self.aria_label:
            return self.aria_label
        if self.text and self.text.strip():
            text = self.text.strip()
            return text[:50] + "..." if len(text) > 50 else text
        if "placeholder" in self.attributes:
            return self.attributes["placeholder"]
        if "title" in self.attributes:
            return self.attributes["title"]
        if "alt" in self.attributes:
            return self.attributes["alt"]
        if "name" in self.attributes:
            return f"{self.tag_name} '{self.attributes['name']}'"
        return f"{self.tag_name} element"


class BrowserState(BaseModel):
    """Complete state of the browser at a point in time."""
    
    # Page information
    url: str = Field(description="Current page URL")
    title: str = Field(description="Page title")
    
    # Viewport
    viewport_width: int = Field(default=1280)
    viewport_height: int = Field(default=720)
    device_pixel_ratio: float = Field(default=1.0)
    
    # Scroll state
    scroll_x: float = Field(default=0.0)
    scroll_y: float = Field(default=0.0)
    page_width: float = Field(default=0.0)
    page_height: float = Field(default=0.0)
    
    # Tabs
    tabs: List[TabInfo] = Field(default_factory=list)
    active_tab_id: Optional[str] = Field(default=None)
    
    # Interactive elements
    elements: List[InteractiveElement] = Field(default_factory=list)
    
    # Screenshot
    screenshot_b64: Optional[str] = Field(default=None, description="Base64 encoded screenshot")
    screenshot_path: Optional[str] = Field(default=None, description="Path to saved screenshot")
    
    # State info
    ready_state: str = Field(default="complete")
    is_pdf: bool = Field(default=False)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Previous state for comparison
    previous_url: Optional[str] = Field(default=None)
    
    @property
    def viewport(self) -> ViewportInfo:
        """Get viewport info."""
        return ViewportInfo(
            width=self.viewport_width,
            height=self.viewport_height,
            device_pixel_ratio=self.device_pixel_ratio
        )
    
    @property
    def scroll(self) -> ScrollPosition:
        """Get scroll position."""
        return ScrollPosition(
            x=self.scroll_x,
            y=self.scroll_y,
            max_x=max(0, self.page_width - self.viewport_width),
            max_y=max(0, self.page_height - self.viewport_height)
        )
    
    @property
    def pages_above(self) -> float:
        """Calculate pages of content above viewport."""
        if self.viewport_height <= 0:
            return 0.0
        return self.scroll_y / self.viewport_height
    
    @property
    def pages_below(self) -> float:
        """Calculate pages of content below viewport."""
        if self.viewport_height <= 0:
            return 0.0
        remaining = self.page_height - self.scroll_y - self.viewport_height
        return max(0, remaining / self.viewport_height)
    
    @property
    def has_content_above(self) -> bool:
        """Check if there's content above the viewport."""
        return self.pages_above > 0.1
    
    @property
    def has_content_below(self) -> bool:
        """Check if there's content below the viewport."""
        return self.pages_below > 0.1
    
    def get_element_by_index(self, index: int) -> Optional[InteractiveElement]:
        """Get element by its index."""
        for element in self.elements:
            if element.index == index:
                return element
        return None
    
    def get_elements_by_tag(self, tag_name: str) -> List[InteractiveElement]:
        """Get all elements with a specific tag."""
        return [e for e in self.elements if e.tag_name.lower() == tag_name.lower()]
    
    def mark_new_elements(self, previous_state: Optional["BrowserState"]) -> None:
        """Mark elements that are new since the previous state."""
        if not previous_state or self.url != previous_state.url:
            return
        
        previous_indices = {e.index for e in previous_state.elements}
        for element in self.elements:
            element.is_new = element.index not in previous_indices
    
    def to_llm_string(self) -> str:
        """Format browser state for LLM consumption."""
        lines = []
        
        # Page info
        lines.append(f"Current URL: {self.url}")
        lines.append(f"Page Title: {self.title}")
        
        # Scroll info
        lines.append(f"<page_info>{self.pages_above:.1f} pages above, {self.pages_below:.1f} pages below</page_info>")
        
        # Tabs
        if len(self.tabs) > 1:
            lines.append("\nOpen Tabs:")
            for tab in self.tabs:
                marker = "*" if tab.is_active else " "
                lines.append(f"  {marker}Tab {tab.short_id}: {tab.title[:30]} - {tab.url[:50]}")
        
        # Elements
        lines.append("\nInteractive Elements:")
        
        if self.has_content_above:
            lines.append(f"... {self.pages_above:.1f} pages above ...")
        else:
            lines.append("[Start of page]")
        
        # Group elements by depth for indentation
        for element in self.elements:
            indent = "\t" * element.depth
            lines.append(f"{indent}{element.to_llm_string()}")
        
        if not self.has_content_below:
            lines.append("[End of page]")
        
        return "\n".join(lines)


@dataclass
class BrowserStateHistory:
    """Historical record of browser state."""
    url: Optional[str]
    title: Optional[str]
    screenshot_b64: Optional[str] = None
    screenshot_path: Optional[str] = None
    interacted_elements: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "url": self.url,
            "title": self.title,
            "screenshot_path": self.screenshot_path,
            "interacted_elements": self.interacted_elements,
        }
    
    def get_screenshot(self) -> Optional[str]:
        """Get screenshot as base64 string."""
        if self.screenshot_b64:
            return self.screenshot_b64
        if self.screenshot_path:
            import base64
            from pathlib import Path
            path = Path(self.screenshot_path)
            if path.exists():
                return base64.b64encode(path.read_bytes()).decode("utf-8")
        return None

