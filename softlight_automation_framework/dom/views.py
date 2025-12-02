"""Data models for DOM extraction and representation."""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class NodeType(IntEnum):
    """DOM node types (matching W3C spec)."""
    ELEMENT_NODE = 1
    TEXT_NODE = 3
    CDATA_SECTION_NODE = 4
    PROCESSING_INSTRUCTION_NODE = 7
    COMMENT_NODE = 8
    DOCUMENT_NODE = 9
    DOCUMENT_TYPE_NODE = 10
    DOCUMENT_FRAGMENT_NODE = 11


@dataclass
class DOMRect:
    """Bounding rectangle for a DOM element."""
    x: float
    y: float
    width: float
    height: float
    
    @property
    def center_x(self) -> float:
        """Get center X coordinate."""
        return self.x + self.width / 2
    
    @property
    def center_y(self) -> float:
        """Get center Y coordinate."""
        return self.y + self.height / 2
    
    @property
    def area(self) -> float:
        """Get rectangle area."""
        return self.width * self.height
    
    def intersects(self, other: "DOMRect") -> bool:
        """Check if this rect intersects with another."""
        return (
            self.x < other.x + other.width and
            self.x + self.width > other.x and
            self.y < other.y + other.height and
            self.y + self.height > other.y
        )
    
    def contains_point(self, x: float, y: float) -> bool:
        """Check if point is inside rectangle."""
        return (
            self.x <= x <= self.x + self.width and
            self.y <= y <= self.y + self.height
        )


@dataclass
class ComputedStyles:
    """Computed CSS styles for an element."""
    display: str = "block"
    visibility: str = "visible"
    opacity: str = "1"
    position: str = "static"
    overflow: str = "visible"
    pointer_events: str = "auto"
    
    @property
    def is_visible(self) -> bool:
        """Check if element is visible based on styles."""
        if self.display == "none":
            return False
        if self.visibility == "hidden":
            return False
        try:
            if float(self.opacity) <= 0:
                return False
        except (ValueError, TypeError):
            pass
        return True
    
    @property
    def is_interactive(self) -> bool:
        """Check if element can receive pointer events."""
        return self.pointer_events != "none"


@dataclass
class AccessibilityInfo:
    """Accessibility information for an element."""
    role: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_interactive_role(self) -> bool:
        """Check if element has an interactive ARIA role."""
        interactive_roles = {
            "button", "link", "menuitem", "option", "tab",
            "checkbox", "radio", "textbox", "combobox",
            "listbox", "slider", "spinbutton", "searchbox",
            "switch", "gridcell", "treeitem"
        }
        return self.role in interactive_roles if self.role else False


@dataclass
class DOMNode:
    """Representation of a DOM node."""
    
    # Node identification
    node_id: int
    backend_node_id: int
    node_type: NodeType
    
    # Node content
    tag_name: str
    node_value: Optional[str] = None
    text_content: str = ""
    
    # Attributes
    attributes: Dict[str, str] = field(default_factory=dict)
    
    # Position and size
    bounds: Optional[DOMRect] = None
    absolute_position: Optional[DOMRect] = None
    
    # Styles
    computed_styles: Optional[ComputedStyles] = None
    
    # Accessibility
    accessibility: Optional[AccessibilityInfo] = None
    
    # Interactivity
    is_visible: bool = True
    is_clickable: bool = False
    is_editable: bool = False
    is_scrollable: bool = False
    
    # Tree structure
    parent_id: Optional[int] = None
    children_ids: List[int] = field(default_factory=list)
    depth: int = 0
    
    # Frame info (for iframes)
    frame_id: Optional[str] = None
    content_document_id: Optional[int] = None
    
    # Shadow DOM
    shadow_root_type: Optional[str] = None
    shadow_root_id: Optional[int] = None
    
    # Indexing
    index: Optional[int] = None  # Assigned index for LLM interaction
    
    @property
    def is_element(self) -> bool:
        """Check if this is an element node."""
        return self.node_type == NodeType.ELEMENT_NODE
    
    @property
    def is_text(self) -> bool:
        """Check if this is a text node."""
        return self.node_type == NodeType.TEXT_NODE
    
    @property
    def is_interactive(self) -> bool:
        """Check if element is interactive."""
        if not self.is_element:
            return False
        
        # Check tag name
        interactive_tags = {
            "a", "button", "input", "select", "textarea",
            "label", "details", "summary", "dialog"
        }
        if self.tag_name.lower() in interactive_tags:
            return True
        
        # Check attributes
        if self.attributes.get("onclick"):
            return True
        if self.attributes.get("tabindex"):
            return True
        if self.attributes.get("contenteditable") == "true":
            return True
        if self.attributes.get("role") in {
            "button", "link", "menuitem", "option", "tab",
            "checkbox", "radio", "textbox", "combobox"
        }:
            return True
        
        return False
    
    def get_attribute(self, name: str, default: str = "") -> str:
        """Safely get an attribute value."""
        return self.attributes.get(name, default)
    
    def has_attribute(self, name: str) -> bool:
        """Check if attribute exists."""
        return name in self.attributes
    
    def get_text(self, max_length: int = 100) -> str:
        """Get truncated text content."""
        text = self.text_content.strip()
        if len(text) > max_length:
            return text[:max_length - 3] + "..."
        return text
    
    def to_selector_info(self) -> Dict[str, Any]:
        """Convert to selector info for element interaction."""
        return {
            "backend_node_id": self.backend_node_id,
            "tag_name": self.tag_name,
            "attributes": self.attributes,
            "bounds": {
                "x": self.bounds.x if self.bounds else 0,
                "y": self.bounds.y if self.bounds else 0,
                "width": self.bounds.width if self.bounds else 0,
                "height": self.bounds.height if self.bounds else 0,
            } if self.bounds else None,
        }


class DOMState(BaseModel):
    """Complete DOM state representation."""
    
    # Root node
    root_node_id: int = Field(description="Root node ID")
    
    # All nodes indexed by node_id
    nodes: Dict[int, Dict[str, Any]] = Field(default_factory=dict)
    
    # Interactive elements with assigned indices
    interactive_elements: Dict[int, Dict[str, Any]] = Field(default_factory=dict)
    
    # Selector map for element interaction
    selector_map: Dict[int, Dict[str, Any]] = Field(default_factory=dict)
    
    # Page info
    url: str = ""
    title: str = ""
    
    # Viewport
    viewport_width: int = 1280
    viewport_height: int = 720
    scroll_x: float = 0.0
    scroll_y: float = 0.0
    
    def get_node(self, node_id: int) -> Optional[Dict[str, Any]]:
        """Get a node by ID."""
        return self.nodes.get(node_id)
    
    def get_interactive_element(self, index: int) -> Optional[Dict[str, Any]]:
        """Get an interactive element by index."""
        return self.interactive_elements.get(index)
    
    def get_selector(self, index: int) -> Optional[Dict[str, Any]]:
        """Get selector info for an element."""
        return self.selector_map.get(index)


@dataclass
class SerializedDOM:
    """Serialized DOM representation for LLM consumption."""
    
    # Text representation
    llm_representation: str = ""
    
    # Statistics
    total_elements: int = 0
    interactive_elements: int = 0
    visible_elements: int = 0
    links_count: int = 0
    iframes_count: int = 0
    scroll_containers: int = 0
    
    # Page info
    has_content_above: bool = False
    has_content_below: bool = False
    pages_above: float = 0.0
    pages_below: float = 0.0
    
    # Selector map for element interaction
    selector_map: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    
    def get_statistics_string(self) -> str:
        """Get statistics as a formatted string."""
        parts = [
            f"{self.links_count} links",
            f"{self.interactive_elements} interactive",
        ]
        if self.iframes_count > 0:
            parts.append(f"{self.iframes_count} iframes")
        if self.scroll_containers > 0:
            parts.append(f"{self.scroll_containers} scroll containers")
        parts.append(f"{self.total_elements} total")
        
        return ", ".join(parts)
    
    def get_page_position_string(self) -> str:
        """Get page position as a formatted string."""
        return f"{self.pages_above:.1f} pages above, {self.pages_below:.1f} pages below"


@dataclass
class DOMSnapshot:
    """Raw DOM snapshot from CDP."""
    
    documents: List[Dict[str, Any]] = field(default_factory=list)
    strings: List[str] = field(default_factory=list)
    
    def get_string(self, index: int) -> str:
        """Get string by index from string table."""
        if 0 <= index < len(self.strings):
            return self.strings[index]
        return ""


@dataclass
class AccessibilityTree:
    """Accessibility tree from CDP."""
    
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    
    def get_node_by_backend_id(self, backend_node_id: int) -> Optional[Dict[str, Any]]:
        """Get AX node by backend DOM node ID."""
        for node in self.nodes:
            if node.get("backendDOMNodeId") == backend_node_id:
                return node
        return None

