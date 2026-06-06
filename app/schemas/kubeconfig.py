from pydantic import BaseModel


class KubeconfigCreate(BaseModel):
    name: str
    content: str


class KubeconfigRead(BaseModel):
    name: str
    path: str
    contexts: list[str]
    current_context: str | None
    created_at: str


class KubeconfigTestResult(BaseModel):
    ok: bool
    message: str | None
    namespaces: list[str] | None
