"""DOM serialization for LLM consumption."""

import logging
from typing import Any, Dict, List, Optional
from softlight_automation_framework.dom.views import (
    DOMNode,
    DOMState,
    SerializedDOM,
    NodeType,
)

logger = logging.getLogger(__name__)


class DOMSerializer:
    """
    Serializes DOM state into a format suitable for LLM consumption.
    
    Produces a hierarchical text representation of interactive elements
    with proper indentation and formatting.
    """
    
    def __init__(
        self,
        dom_state: DOMState,
        max_length: int = 40000,
        include_attributes: Optional[List[str]] = None,
    ):
        """
        Initialize the serializer.
        
        Args:
            dom_state: DOM state to serialize
            max_length: Maximum length of output
            include_attributes: Attributes to include (None = default set)
        """
        self.dom_state = dom_state
        self.max_length = max_length
        self.include_attributes = include_attributes or [
            "aria-label", "placeholder", "type", "role",
            "href", "src", "alt", "title", "name", "value"
        ]
        
        # Statistics
        self.stats = {
            "total_elements": 0,
            "interactive_elements": 0,
            "visible_elements": 0,
            "links_count": 0,
            "iframes_count": 0,
            "scroll_containers": 0,
        }
    
    def serialize(self) -> SerializedDOM:
        """
        Serialize the DOM state.
        
        Returns:
            SerializedDOM with text representation and statistics
        """
        logger.debug("Serializing DOM state...")
        
        # Calculate statistics
        self._calculate_stats()
        
        # Build representation
        lines = []
        
        # Add page info markers
        scroll_y = self.dom_state.scroll_y
        viewport_height = self.dom_state.viewport_height
        page_height = self._get_page_height()
        
        pages_above = scroll_y / viewport_height if viewport_height > 0 else 0
        pages_below = max(0, (page_height - scroll_y - viewport_height) / viewport_height) if viewport_height > 0 else 0
        
        has_content_above = pages_above > 0.1
        has_content_below = pages_below > 0.1
        
        # Add start marker
        if has_content_above:
            lines.append(f"... {pages_above:.1f} pages above ...")
        else:
            lines.append("[Start of page]")
        
        # Serialize interactive elements
        elements = self._get_sorted_elements()
        for element in elements:
            line = self._serialize_element(element)
            if line:
                lines.append(line)
        
        # Add end marker
        if not has_content_below:
            lines.append("[End of page]")
        
        # Join and truncate if needed
        representation = "\n".join(lines)
        truncated = False
        
        if len(representation) > self.max_length:
            representation = representation[:self.max_length]
            truncated = True
            logger.debug(f"DOM representation truncated to {self.max_length} chars")
        
        return SerializedDOM(
            llm_representation=representation,
            total_elements=self.stats["total_elements"],
            interactive_elements=self.stats["interactive_elements"],
            visible_elements=self.stats["visible_elements"],
            links_count=self.stats["links_count"],
            iframes_count=self.stats["iframes_count"],
            scroll_containers=self.stats["scroll_containers"],
            has_content_above=has_content_above,
            has_content_below=has_content_below,
            pages_above=pages_above,
            pages_below=pages_below,
            selector_map=self.dom_state.selector_map,
        )
    
    def _calculate_stats(self) -> None:
        """Calculate DOM statistics."""
        for node_data in self.dom_state.nodes.values():
            self.stats["total_elements"] += 1
            
            tag = node_data.get("tag_name", "").lower()
            is_visible = node_data.get("is_visible", False)
            index = node_data.get("index")
            
            if is_visible:
                self.stats["visible_elements"] += 1
            
            if index is not None:
                self.stats["interactive_elements"] += 1
            
            if tag == "a":
                self.stats["links_count"] += 1
            elif tag in ("iframe", "frame"):
                self.stats["iframes_count"] += 1
    
    def _get_page_height(self) -> float:
        """Estimate page height from element positions."""
        max_y = self.dom_state.viewport_height
        
        for node_data in self.dom_state.nodes.values():
            bounds = node_data.get("bounds")
            if bounds:
                bottom = bounds.get("y", 0) + bounds.get("height", 0)
                max_y = max(max_y, bottom)
        
        return max_y
    
    def _get_sorted_elements(self) -> List[Dict[str, Any]]:
        """Get interactive elements sorted by position."""
        elements = []
        
        for node_data in self.dom_state.interactive_elements.values():
            if node_data.get("is_visible", True):
                elements.append(node_data)
        
        # Sort by Y position, then X position
        def sort_key(e):
            bounds = e.get("bounds", {})
            return (bounds.get("y", 0), bounds.get("x", 0))
        
        return sorted(elements, key=sort_key)
    
    def _serialize_element(self, element: Dict[str, Any]) -> str:
        """
        Serialize a single element to string format.
        
        Format: [index]<tag attributes>text</tag>
        """
        index = element.get("index")
        if index is None:
            return ""
        
        tag = element.get("tag_name", "div")
        text = element.get("text", "")
        attrs = element.get("attributes", {})
        depth = element.get("depth", 0)
        
        # Build attribute string
        attr_parts = []
        for attr_name in self.include_attributes:
            if attr_name in attrs:
                value = attrs[attr_name]
                if value:
                    # Truncate long values
                    if len(value) > 50:
                        value = value[:47] + "..."
                    attr_parts.append(f"{attr_name}='{value}'")
        
        # Add accessibility info
        ax = element.get("accessibility", {})
        if ax:
            if ax.get("role") and "role" not in attrs:
                attr_parts.append(f"role='{ax['role']}'")
            if ax.get("name") and "aria-label" not in attrs:
                attr_parts.append(f"aria-label='{ax['name'][:50]}'")
        
        attr_str = " " + " ".join(attr_parts) if attr_parts else ""
        
        # Truncate text
        if len(text) > 100:
            text = text[:97] + "..."
        
        # Build the line with indentation
        indent = "\t" * min(depth, 5)  # Cap indentation depth
        
        # Check if element is new (appeared since last state)
        is_new = element.get("is_new", False)
        prefix = "*" if is_new else ""
        
        return f"{indent}{prefix}[{index}]<{tag}{attr_str}>{text}</{tag}>"
    
    def get_statistics_header(self) -> str:
        """Get formatted statistics header for LLM."""
        parts = []
        parts.append(f"<page_stats>")
        parts.append(f"{self.stats['links_count']} links")
        parts.append(f"{self.stats['interactive_elements']} interactive")
        
        if self.stats["iframes_count"] > 0:
            parts.append(f"{self.stats['iframes_count']} iframes")
        if self.stats["scroll_containers"] > 0:
            parts.append(f"{self.stats['scroll_containers']} scroll containers")
        
        parts.append(f"{self.stats['total_elements']} total elements")
        parts.append("</page_stats>")
        
        return ", ".join(parts[1:-1])


def serialize_dom_for_llm(
    dom_state: DOMState,
    url: str = "",
    title: str = "",
    tabs: List[Dict[str, str]] = None,
    active_tab_id: str = "",
    max_length: int = 40000,
) -> str:
    """
    High-level function to serialize DOM state for LLM consumption.
    
    Args:
        dom_state: DOM state to serialize
        url: Current page URL
        title: Current page title
        tabs: List of open tabs
        active_tab_id: ID of the active tab
        max_length: Maximum output length
        
    Returns:
        Formatted string for LLM prompt
    """
    serializer = DOMSerializer(dom_state, max_length=max_length)
    serialized = serializer.serialize()
    
    lines = []
    
    # Add page stats
    lines.append(f"<page_stats>{serializer.get_statistics_header()}</page_stats>")
    
    # Add current tab info
    if active_tab_id:
        lines.append(f"Current tab: {active_tab_id[-4:]}")
    
    # Add tabs list
    if tabs and len(tabs) > 1:
        lines.append("Available tabs:")
        for tab in tabs:
            marker = "*" if tab.get("target_id") == active_tab_id else " "
            tab_title = tab.get("title", "")[:30]
            tab_url = tab.get("url", "")[:50]
            tab_id = tab.get("target_id", "")[-4:]
            lines.append(f"  {marker}Tab {tab_id}: {tab_url} - {tab_title}")
    
    # Add page position info
    lines.append(f"\n<page_info>{serialized.get_page_position_string()}</page_info>")
    
    # Add interactive elements
    lines.append("\nInteractive elements:")
    lines.append(serialized.llm_representation)
    
    return "\n".join(lines)


def get_element_description(element: Dict[str, Any]) -> str:
    """
    Get a human-readable description of an element.
    
    Args:
        element: Element data dictionary
        
    Returns:
        Description string like "button 'Submit'" or "input[type=text]"
    """
    tag = element.get("tag_name", "element")
    text = element.get("text", "")
    attrs = element.get("attributes", {})
    ax = element.get("accessibility", {})
    
    # Try to get the best descriptive text
    label = (
        attrs.get("aria-label") or
        ax.get("name") or
        attrs.get("title") or
        attrs.get("placeholder") or
        text
    )
    
    if label:
        label = label[:30] + "..." if len(label) > 30 else label
    
    # Build description based on tag
    if tag == "a":
        return f"link '{label}'" if label else "link"
    elif tag == "button":
        return f"button '{label}'" if label else "button"
    elif tag == "input":
        input_type = attrs.get("type", "text")
        desc = f"input[type={input_type}]"
        if label:
            desc += f" '{label}'"
        return desc
    elif tag == "select":
        return f"dropdown '{label}'" if label else "dropdown"
    elif tag == "textarea":
        return f"textarea '{label}'" if label else "textarea"
    else:
        return f"{tag} '{label}'" if label else tag

