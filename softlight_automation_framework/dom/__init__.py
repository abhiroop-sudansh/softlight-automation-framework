"""DOM extraction and serialization module."""

from softlight_automation_framework.dom.extractor import DOMExtractor
from softlight_automation_framework.dom.serializer import DOMSerializer
from softlight_automation_framework.dom.views import (
    DOMNode,
    DOMRect,
    DOMState,
    SerializedDOM,
)

__all__ = [
    "DOMExtractor",
    "DOMSerializer",
    "DOMNode",
    "DOMRect",
    "DOMState",
    "SerializedDOM",
]

