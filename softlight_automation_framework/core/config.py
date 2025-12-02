"""Configuration management for the browser automation framework."""

import os
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class BrowserConfig(BaseModel):
    """Browser-specific configuration."""
    
    headless: bool = Field(
        default=False,
        description="Run browser in headless mode"
    )
    timeout: int = Field(
        default=30000,
        description="Default timeout in milliseconds"
    )
    viewport_width: int = Field(
        default=1280,
        description="Browser viewport width"
    )
    viewport_height: int = Field(
        default=720,
        description="Browser viewport height"
    )
    user_agent: Optional[str] = Field(
        default=None,
        description="Custom user agent string"
    )
    ignore_https_errors: bool = Field(
        default=True,
        description="Ignore HTTPS certificate errors"
    )
    slow_mo: int = Field(
        default=0,
        description="Slow down operations by specified milliseconds"
    )
    downloads_path: Optional[str] = Field(
        default=None,
        description="Directory for browser downloads"
    )
    
    @classmethod
    def from_env(cls) -> "BrowserConfig":
        """Create config from environment variables."""
        return cls(
            headless=os.getenv("BROWSER_HEADLESS", "false").lower() == "true",
            timeout=int(os.getenv("BROWSER_TIMEOUT", "30000")),
            viewport_width=int(os.getenv("BROWSER_VIEWPORT_WIDTH", "1280")),
            viewport_height=int(os.getenv("BROWSER_VIEWPORT_HEIGHT", "720")),
            user_agent=os.getenv("BROWSER_USER_AGENT"),
            ignore_https_errors=os.getenv("BROWSER_IGNORE_HTTPS_ERRORS", "true").lower() == "true",
            slow_mo=int(os.getenv("BROWSER_SLOW_MO", "0")),
            downloads_path=os.getenv("BROWSER_DOWNLOADS_PATH"),
        )


class LLMConfig(BaseModel):
    """LLM-specific configuration."""
    
    api_key: str = Field(
        default="",
        description="OpenAI API key"
    )
    model: str = Field(
        default="gpt-4o",
        description="Model name to use"
    )
    temperature: float = Field(
        default=0.0,
        description="Sampling temperature"
    )
    max_tokens: int = Field(
        default=4096,
        description="Maximum tokens in response"
    )
    timeout: int = Field(
        default=60,
        description="Request timeout in seconds"
    )
    
    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Create config from environment variables."""
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.0")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "4096")),
            timeout=int(os.getenv("OPENAI_TIMEOUT", "60")),
        )


class AgentConfig(BaseModel):
    """Agent-specific configuration."""
    
    max_steps: int = Field(
        default=100,
        description="Maximum steps the agent can take"
    )
    max_actions_per_step: int = Field(
        default=4,
        description="Maximum actions per step"
    )
    max_failures: int = Field(
        default=3,
        description="Maximum consecutive failures before stopping"
    )
    use_vision: bool = Field(
        default=True,
        description="Include screenshots in prompts"
    )
    step_timeout: int = Field(
        default=120,
        description="Timeout for each step in seconds"
    )
    
    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Create config from environment variables."""
        return cls(
            max_steps=int(os.getenv("AGENT_MAX_STEPS", "100")),
            max_actions_per_step=int(os.getenv("AGENT_MAX_ACTIONS_PER_STEP", "4")),
            max_failures=int(os.getenv("AGENT_MAX_FAILURES", "3")),
            use_vision=os.getenv("AGENT_USE_VISION", "true").lower() == "true",
            step_timeout=int(os.getenv("AGENT_STEP_TIMEOUT", "120")),
        )


class Config(BaseModel):
    """Main configuration container."""
    
    browser: BrowserConfig = Field(default_factory=BrowserConfig.from_env)
    llm: LLMConfig = Field(default_factory=LLMConfig.from_env)
    agent: AgentConfig = Field(default_factory=AgentConfig.from_env)
    
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    log_file: Optional[str] = Field(
        default=None,
        description="Log file path"
    )
    save_screenshots: bool = Field(
        default=False,
        description="Save screenshots to disk"
    )
    screenshots_dir: str = Field(
        default="./screenshots",
        description="Directory for saved screenshots"
    )
    save_traces: bool = Field(
        default=False,
        description="Save execution traces"
    )
    traces_dir: str = Field(
        default="./traces",
        description="Directory for saved traces"
    )
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create complete config from environment variables."""
        return cls(
            browser=BrowserConfig.from_env(),
            llm=LLMConfig.from_env(),
            agent=AgentConfig.from_env(),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE"),
            save_screenshots=os.getenv("SAVE_SCREENSHOTS", "false").lower() == "true",
            screenshots_dir=os.getenv("SCREENSHOTS_DIR", "./screenshots"),
            save_traces=os.getenv("SAVE_TRACES", "false").lower() == "true",
            traces_dir=os.getenv("TRACES_DIR", "./traces"),
        )
    
    def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        if self.save_screenshots:
            Path(self.screenshots_dir).mkdir(parents=True, exist_ok=True)
        if self.save_traces:
            Path(self.traces_dir).mkdir(parents=True, exist_ok=True)
        if self.browser.downloads_path:
            Path(self.browser.downloads_path).mkdir(parents=True, exist_ok=True)


# Global configuration instance
CONFIG = Config.from_env()

