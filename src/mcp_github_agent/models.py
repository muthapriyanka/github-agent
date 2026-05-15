from __future__ import annotations
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class GitHubOAuthConfig(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: str


class MCPRequest(BaseModel):
    tool: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None


class MCPResponse(BaseModel):
    status: str
    output: Any
    tool_output: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
