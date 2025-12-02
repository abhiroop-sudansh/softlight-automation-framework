"""Custom exceptions for the browser automation framework."""

from typing import Optional


class BrowserAutomationError(Exception):
    """Base exception for all browser automation errors."""
    
    def __init__(
        self,
        message: str,
        details: Optional[str] = None,
        recoverable: bool = True
    ):
        self.message = message
        self.details = details
        self.recoverable = recoverable
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message


class BrowserError(BrowserAutomationError):
    """Errors related to browser operations."""
    
    def __init__(
        self,
        message: str,
        details: Optional[str] = None,
        long_term_memory: Optional[str] = None,
        short_term_memory: Optional[str] = None,
        recoverable: bool = True
    ):
        super().__init__(message, details, recoverable)
        self.long_term_memory = long_term_memory or message
        self.short_term_memory = short_term_memory


class NavigationError(BrowserError):
    """Errors during page navigation."""
    pass


class ElementNotFoundError(BrowserError):
    """Element could not be found in the DOM."""
    
    def __init__(
        self,
        selector: str,
        message: Optional[str] = None,
        **kwargs
    ):
        self.selector = selector
        msg = message or f"Element not found: {selector}"
        super().__init__(msg, **kwargs)


class ElementNotInteractableError(BrowserError):
    """Element exists but cannot be interacted with."""
    
    def __init__(
        self,
        element_info: str,
        reason: str,
        **kwargs
    ):
        self.element_info = element_info
        self.reason = reason
        msg = f"Element not interactable: {element_info}. Reason: {reason}"
        super().__init__(msg, **kwargs)


class AgentError(BrowserAutomationError):
    """Errors related to agent operations."""
    pass


class MaxStepsReachedError(AgentError):
    """Agent reached maximum allowed steps."""
    
    def __init__(self, max_steps: int, **kwargs):
        self.max_steps = max_steps
        super().__init__(
            f"Agent reached maximum steps limit: {max_steps}",
            recoverable=False,
            **kwargs
        )


class MaxFailuresReachedError(AgentError):
    """Agent reached maximum consecutive failures."""
    
    def __init__(self, max_failures: int, **kwargs):
        self.max_failures = max_failures
        super().__init__(
            f"Agent reached maximum consecutive failures: {max_failures}",
            recoverable=False,
            **kwargs
        )


class ActionError(BrowserAutomationError):
    """Errors related to action execution."""
    
    def __init__(
        self,
        action_name: str,
        message: str,
        params: Optional[dict] = None,
        **kwargs
    ):
        self.action_name = action_name
        self.params = params
        super().__init__(f"Action '{action_name}' failed: {message}", **kwargs)


class ActionNotFoundError(ActionError):
    """Requested action is not registered."""
    
    def __init__(self, action_name: str, **kwargs):
        super().__init__(
            action_name,
            f"Action '{action_name}' not found in registry",
            recoverable=False,
            **kwargs
        )


class ActionValidationError(ActionError):
    """Action parameters failed validation."""
    
    def __init__(
        self,
        action_name: str,
        validation_error: str,
        **kwargs
    ):
        self.validation_error = validation_error
        super().__init__(
            action_name,
            f"Invalid parameters: {validation_error}",
            **kwargs
        )


class DOMError(BrowserAutomationError):
    """Errors related to DOM extraction and manipulation."""
    pass


class DOMExtractionError(DOMError):
    """Failed to extract DOM tree."""
    pass


class DOMSerializationError(DOMError):
    """Failed to serialize DOM for LLM."""
    pass


class LLMError(BrowserAutomationError):
    """Errors related to LLM operations."""
    
    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        **kwargs
    ):
        self.model = model
        super().__init__(message, **kwargs)


class LLMResponseError(LLMError):
    """LLM returned an invalid or unparseable response."""
    
    def __init__(
        self,
        message: str,
        raw_response: Optional[str] = None,
        **kwargs
    ):
        self.raw_response = raw_response
        super().__init__(message, **kwargs)


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        **kwargs
    ):
        self.retry_after = retry_after
        super().__init__(message, recoverable=True, **kwargs)


class LLMTimeoutError(LLMError):
    """LLM request timed out."""
    
    def __init__(
        self,
        timeout: int,
        **kwargs
    ):
        self.timeout = timeout
        super().__init__(
            f"LLM request timed out after {timeout} seconds",
            recoverable=True,
            **kwargs
        )


class TimeoutError(BrowserAutomationError):
    """General timeout error."""
    
    def __init__(
        self,
        operation: str,
        timeout: int,
        **kwargs
    ):
        self.operation = operation
        self.timeout = timeout
        super().__init__(
            f"Operation '{operation}' timed out after {timeout}ms",
            recoverable=True,
            **kwargs
        )


class SessionError(BrowserAutomationError):
    """Errors related to session management."""
    pass


class SessionExpiredError(SessionError):
    """Browser session has expired or been closed."""
    
    def __init__(self, session_id: str, **kwargs):
        self.session_id = session_id
        super().__init__(
            f"Session '{session_id}' has expired or been closed",
            recoverable=False,
            **kwargs
        )

