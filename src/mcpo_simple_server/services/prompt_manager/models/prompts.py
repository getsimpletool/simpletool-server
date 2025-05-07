"""
Models for the prompt system.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal, Union

# Define the role types for messages
LLMRoles = Literal["system", "user", "assistant"]


class PromptArgument(BaseModel):
    """An argument for a prompt template."""
    name: str
    description: Optional[str] = None
    required: bool = False
    default_value: Optional[str] = None

    class Config:
        extra = "allow"


class TextContent(BaseModel):
    """Text content for a message."""
    type: Literal["text"] = "text"
    text: str

    class Config:
        extra = "allow"


class PromptMessage(BaseModel):
    """A message in a prompt template."""
    role: LLMRoles
    content: Union[TextContent, Dict[str, Any]]

    class Config:
        extra = "allow"


class PromptTemplate(BaseModel):
    """A prompt template definition."""
    name: str
    description: Optional[str] = None
    arguments: Optional[List[PromptArgument]] = None
    messages: List[PromptMessage]

    # Fields for shared prompts
    id: Optional[str] = None  # UUID for shared prompts
    owner: Optional[str] = None  # Username of the owner for shared prompts

    class Config:
        extra = "allow"


class PromptSource(BaseModel):
    """Source information for a prompt."""
    type: Literal["public", "private", "shared"]
    path: str


class PromptInfo(BaseModel):
    """Basic information about a prompt for listing."""
    name: str
    description: Optional[str] = None
    arguments: Optional[List[PromptArgument]] = None
    source: PromptSource
    id: Optional[str] = None  # UUID for shared prompts
    owner: Optional[str] = None  # Username of the owner for shared prompts


class PromptExecuteRequest(BaseModel):
    """Request model for executing a prompt."""
    arguments: Dict[str, Any] = Field(default_factory=dict)


class PromptExecuteResponse(BaseModel):
    """Response model for executing a prompt."""
    messages: List[PromptMessage]


class PromptCreateRequest(BaseModel):
    """Request model for creating a prompt."""
    name: str
    description: Optional[str] = None
    arguments: Optional[List[PromptArgument]] = None
    messages: List[PromptMessage]

    class Config:
        extra = "allow"
