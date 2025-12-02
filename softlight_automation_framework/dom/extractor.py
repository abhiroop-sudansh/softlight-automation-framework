"""DOM extraction using CDP for comprehensive page analysis."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from softlight_automation_framework.dom.views import (
    DOMNode,
    DOMRect,
    DOMState,
    ComputedStyles,
    AccessibilityInfo,
    NodeType,
    DOMSnapshot,
    AccessibilityTree,
)

logger = logging.getLogger(__name__)


class DOMExtractor:
    """
    Extracts DOM tree and interactive elements from a page using CDP.
    
    Provides comprehensive DOM analysis including:
    - Full DOM tree structure
    - Computed styles
    - Bounding rectangles
    - Accessibility information
    - Interactive element detection
    """
    
    def __init__(
        self,
        cdp_session: Any,
        viewport_width: int = 1280,
        viewport_height: int = 720,
    ):
        """
        Initialize the DOM extractor.
        
        Args:
            cdp_session: CDP session for browser communication
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height
        """
        self.cdp_session = cdp_session
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        
        self._nodes: Dict[int, DOMNode] = {}
        self._selector_map: Dict[int, Dict[str, Any]] = {}
        self._interactive_index = 1
    
    async def extract(self) -> Tuple[DOMState, Dict[int, Dict[str, Any]]]:
        """
        Extract the complete DOM state.
        
        Returns:
            Tuple of (DOMState, selector_map)
        """
        logger.debug("Extracting DOM...")
        
        # Get DOM snapshot with styles and layout
        snapshot = await self._get_dom_snapshot()
        
        # Get accessibility tree
        ax_tree = await self._get_accessibility_tree()
        
        # Get DOM tree
        dom_tree = await self._get_dom_tree()
        
        # Build enhanced DOM tree
        await self._build_dom_tree(dom_tree, snapshot, ax_tree)
        
        # Create DOM state
        state = DOMState(
            root_node_id=dom_tree.get("root", {}).get("nodeId", 0),
            nodes={n.node_id: self._node_to_dict(n) for n in self._nodes.values()},
            interactive_elements={
                n.index: self._node_to_dict(n)
                for n in self._nodes.values()
                if n.index is not None
            },
            selector_map=self._selector_map,
            viewport_width=self.viewport_width,
            viewport_height=self.viewport_height,
        )
        
        logger.debug(
            f"Extracted {len(self._nodes)} nodes, "
            f"{len(self._selector_map)} interactive elements"
        )
        
        return state, self._selector_map
    
    async def _get_dom_snapshot(self) -> DOMSnapshot:
        """Get DOM snapshot using CDP."""
        try:
            result = await self.cdp_session.send(
                "DOMSnapshot.captureSnapshot",
                {
                    "computedStyles": [
                        "display", "visibility", "opacity",
                        "position", "overflow", "pointer-events"
                    ],
                    "includePaintOrder": True,
                    "includeDOMRects": True,
                }
            )
            return DOMSnapshot(
                documents=result.get("documents", []),
                strings=result.get("strings", []),
            )
        except Exception as e:
            logger.warning(f"Failed to get DOM snapshot: {e}")
            return DOMSnapshot()
    
    async def _get_accessibility_tree(self) -> AccessibilityTree:
        """Get accessibility tree using CDP."""
        try:
            result = await self.cdp_session.send("Accessibility.getFullAXTree")
            return AccessibilityTree(nodes=result.get("nodes", []))
        except Exception as e:
            logger.warning(f"Failed to get accessibility tree: {e}")
            return AccessibilityTree()
    
    async def _get_dom_tree(self) -> Dict[str, Any]:
        """Get DOM tree using CDP."""
        try:
            result = await self.cdp_session.send(
                "DOM.getDocument",
                {"depth": -1, "pierce": True}
            )
            return result
        except Exception as e:
            logger.warning(f"Failed to get DOM tree: {e}")
            return {}
    
    async def _build_dom_tree(
        self,
        dom_tree: Dict[str, Any],
        snapshot: DOMSnapshot,
        ax_tree: AccessibilityTree,
    ) -> None:
        """Build enhanced DOM tree from raw data."""
        root = dom_tree.get("root")
        if not root:
            return
        
        # Build lookup tables from snapshot
        snapshot_lookup = self._build_snapshot_lookup(snapshot)
        ax_lookup = self._build_ax_lookup(ax_tree)
        
        # Recursively process nodes
        await self._process_node(
            root,
            snapshot_lookup,
            ax_lookup,
            parent_id=None,
            depth=0,
        )
    
    def _build_snapshot_lookup(
        self,
        snapshot: DOMSnapshot
    ) -> Dict[int, Dict[str, Any]]:
        """Build lookup table from DOM snapshot."""
        lookup = {}
        
        for doc in snapshot.documents:
            nodes = doc.get("nodes", {})
            layout = doc.get("layout", {})
            
            node_indices = layout.get("nodeIndex", [])
            bounds_list = layout.get("bounds", [])
            styles_list = layout.get("styles", [])
            
            for i, node_idx in enumerate(node_indices):
                backend_node_id = nodes.get("backendNodeId", [])[node_idx] if node_idx < len(nodes.get("backendNodeId", [])) else None
                
                if backend_node_id is None:
                    continue
                
                entry = {"backend_node_id": backend_node_id}
                
                # Add bounds
                if i < len(bounds_list):
                    b = bounds_list[i]
                    if len(b) >= 4:
                        entry["bounds"] = DOMRect(x=b[0], y=b[1], width=b[2], height=b[3])
                
                # Add styles
                if i < len(styles_list):
                    style_indices = styles_list[i]
                    styles = {}
                    style_names = ["display", "visibility", "opacity", "position", "overflow", "pointer-events"]
                    for j, style_idx in enumerate(style_indices):
                        if j < len(style_names) and style_idx >= 0:
                            styles[style_names[j]] = snapshot.get_string(style_idx)
                    if styles:
                        entry["styles"] = ComputedStyles(**styles)
                
                lookup[backend_node_id] = entry
        
        return lookup
    
    def _build_ax_lookup(
        self,
        ax_tree: AccessibilityTree
    ) -> Dict[int, Dict[str, Any]]:
        """Build lookup table from accessibility tree."""
        lookup = {}
        
        for node in ax_tree.nodes:
            backend_node_id = node.get("backendDOMNodeId")
            if backend_node_id is None:
                continue
            
            entry = {
                "role": node.get("role", {}).get("value"),
                "name": node.get("name", {}).get("value"),
                "description": node.get("description", {}).get("value"),
                "properties": {},
            }
            
            # Extract properties
            for prop in node.get("properties", []):
                prop_name = prop.get("name")
                prop_value = prop.get("value", {}).get("value")
                if prop_name and prop_value is not None:
                    entry["properties"][prop_name] = prop_value
            
            lookup[backend_node_id] = entry
        
        return lookup
    
    async def _process_node(
        self,
        node: Dict[str, Any],
        snapshot_lookup: Dict[int, Dict[str, Any]],
        ax_lookup: Dict[int, Dict[str, Any]],
        parent_id: Optional[int],
        depth: int,
    ) -> Optional[DOMNode]:
        """Process a single DOM node and its children."""
        node_id = node.get("nodeId")
        backend_node_id = node.get("backendNodeId")
        node_type_value = node.get("nodeType", 1)
        
        if node_id is None or backend_node_id is None:
            return None
        
        try:
            node_type = NodeType(node_type_value)
        except ValueError:
            node_type = NodeType.ELEMENT_NODE
        
        # Get attributes
        attributes = {}
        attrs_list = node.get("attributes", [])
        for i in range(0, len(attrs_list), 2):
            if i + 1 < len(attrs_list):
                attributes[attrs_list[i]] = attrs_list[i + 1]
        
        # Get snapshot data
        snapshot_data = snapshot_lookup.get(backend_node_id, {})
        bounds = snapshot_data.get("bounds")
        styles = snapshot_data.get("styles")
        
        # Get accessibility data
        ax_data = ax_lookup.get(backend_node_id, {})
        accessibility = AccessibilityInfo(
            role=ax_data.get("role"),
            name=ax_data.get("name"),
            description=ax_data.get("description"),
            properties=ax_data.get("properties", {}),
        ) if ax_data else None
        
        # Determine visibility
        is_visible = True
        if styles and not styles.is_visible:
            is_visible = False
        if bounds and (bounds.width <= 0 or bounds.height <= 0):
            is_visible = False
        
        # Create DOM node
        dom_node = DOMNode(
            node_id=node_id,
            backend_node_id=backend_node_id,
            node_type=node_type,
            tag_name=node.get("nodeName", "").lower(),
            node_value=node.get("nodeValue"),
            attributes=attributes,
            bounds=bounds,
            computed_styles=styles,
            accessibility=accessibility,
            is_visible=is_visible,
            parent_id=parent_id,
            depth=depth,
            frame_id=node.get("frameId"),
        )
        
        # Get text content
        if node_type == NodeType.TEXT_NODE:
            dom_node.text_content = node.get("nodeValue", "")
        
        # Check if interactive
        if dom_node.is_element and dom_node.is_interactive and is_visible:
            # Assign interaction index
            dom_node.index = self._interactive_index
            self._selector_map[self._interactive_index] = dom_node.to_selector_info()
            self._interactive_index += 1
            dom_node.is_clickable = True
        
        # Check if editable
        tag = dom_node.tag_name.lower()
        if tag in ("input", "textarea") or attributes.get("contenteditable") == "true":
            dom_node.is_editable = True
        
        # Check if scrollable
        if node.get("isScrollable"):
            dom_node.is_scrollable = True
        
        # Store node
        self._nodes[node_id] = dom_node
        
        # Process children
        children_ids = []
        for child in node.get("children", []):
            child_node = await self._process_node(
                child,
                snapshot_lookup,
                ax_lookup,
                parent_id=node_id,
                depth=depth + 1,
            )
            if child_node:
                children_ids.append(child_node.node_id)
        
        dom_node.children_ids = children_ids
        
        # Process content document (for iframes)
        content_doc = node.get("contentDocument")
        if content_doc:
            doc_node = await self._process_node(
                content_doc,
                snapshot_lookup,
                ax_lookup,
                parent_id=node_id,
                depth=depth + 1,
            )
            if doc_node:
                dom_node.content_document_id = doc_node.node_id
        
        # Process shadow roots
        for shadow_root in node.get("shadowRoots", []):
            shadow_node = await self._process_node(
                shadow_root,
                snapshot_lookup,
                ax_lookup,
                parent_id=node_id,
                depth=depth + 1,
            )
            if shadow_node:
                dom_node.shadow_root_id = shadow_node.node_id
                dom_node.shadow_root_type = shadow_root.get("shadowRootType")
        
        # Aggregate text content from children
        if dom_node.is_element:
            text_parts = []
            for child_id in children_ids:
                child = self._nodes.get(child_id)
                if child and child.is_text:
                    text_parts.append(child.text_content)
                elif child and child.text_content:
                    text_parts.append(child.text_content)
            dom_node.text_content = " ".join(text_parts).strip()
        
        return dom_node
    
    def _node_to_dict(self, node: DOMNode) -> Dict[str, Any]:
        """Convert a DOMNode to a dictionary."""
        return {
            "node_id": node.node_id,
            "backend_node_id": node.backend_node_id,
            "tag_name": node.tag_name,
            "text": node.get_text(),
            "attributes": node.attributes,
            "bounds": {
                "x": node.bounds.x,
                "y": node.bounds.y,
                "width": node.bounds.width,
                "height": node.bounds.height,
            } if node.bounds else None,
            "is_visible": node.is_visible,
            "is_clickable": node.is_clickable,
            "is_editable": node.is_editable,
            "index": node.index,
            "depth": node.depth,
            "accessibility": {
                "role": node.accessibility.role,
                "name": node.accessibility.name,
            } if node.accessibility else None,
        }
    
    def get_node_by_index(self, index: int) -> Optional[DOMNode]:
        """Get a DOM node by its interaction index."""
        for node in self._nodes.values():
            if node.index == index:
                return node
        return None
    
    def get_visible_elements(self) -> List[DOMNode]:
        """Get all visible interactive elements."""
        return [
            node for node in self._nodes.values()
            if node.is_visible and node.index is not None
        ]
    
    def get_elements_in_viewport(self) -> List[DOMNode]:
        """Get elements within the current viewport."""
        viewport = DOMRect(
            x=0, y=0,
            width=self.viewport_width,
            height=self.viewport_height
        )
        
        return [
            node for node in self._nodes.values()
            if node.bounds and viewport.intersects(node.bounds)
        ]

