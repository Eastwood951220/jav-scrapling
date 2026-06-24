from pydantic import BaseModel, Field


class JavdbCookie(BaseModel):
    """A single cookie entry matching the browser-export format."""
    domain: str
    expirationDate: float | None = None
    hostOnly: bool = True
    httpOnly: bool = False
    name: str
    path: str = "/"
    sameSite: str | None = "lax"
    secure: bool = False
    session: bool = False
    storeId: str | None = None
    value: str


class CookiesConfig(BaseModel):
    """Wrapper for the cookie array stored in the JSON file."""
    cookies: list[JavdbCookie] = Field(default_factory=list)
