from pydantic import BaseModel, Field, field_validator
from enum import Enum
from typing import List, Optional
from datetime import datetime

class Language(str, Enum):
    PYTHON = "Python"
    JAVASCRIPT = "JavaScript"
    TYPESCRIPT = "TypeScript"
    JAVA = "Java"
    CSHARP = "C#"
    CPP = "C++"
    GO = "Go"
    RUST = "Rust"
    RUBY = "Ruby"
    PHP = "PHP"

class SortCriteria(str, Enum):
    STARS = "stars"
    FORKS = "forks"
    UPDATED = "updated"

class SortOrder(str, Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"

class RepoConfig(BaseModel):
    min_language_percentage: float = Field(default=70.0, ge=0.0, le=100.0)
    max_contributors: int = Field(default=2, ge=1)
    max_stars: int = Field(default=100, ge=0)
    max_repos: int = Field(default=100, ge=1)
    recent_days: int = Field(default=5, ge=1)

    @field_validator('min_language_percentage')
    @classmethod
    def check_percentage(cls, v):
        if v < 0 or v > 100:
            raise ValueError('Percentage must be between 0 and 100')
        return v

class SearchConfig(BaseModel):
    repo_config: RepoConfig = RepoConfig()
    github_token: str = Field(..., min_length=1)
    excluded_repos: List[str] = Field(default_factory=list)
    included_languages: List[Language] = Field(default_factory=lambda: [Language.PYTHON])
    sort_by: SortCriteria = Field(default=SortCriteria.STARS)
    sort_order: SortOrder = Field(default=SortOrder.DESCENDING)
    min_repo_size: Optional[int] = Field(default=None, description="Minimum repository size in KB")
    max_repo_size: Optional[int] = Field(default=None, description="Maximum repository size in KB")
    include_forks: bool = Field(default=False, description="Include forked repositories")
    created_after: Optional[datetime] = Field(default=None, description="Filter repos created after this date")
    pushed_after: Optional[datetime] = Field(default=None, description="Filter repos pushed after this date")
    topics: List[str] = Field(default_factory=list, description="List of topics to filter by")
    license: Optional[str] = Field(default=None, description="License type to filter by")
    is_public: Optional[bool] = Field(default=None, description="Filter by public/private status")

    @field_validator('github_token')
    @classmethod
    def check_github_token(cls, v):
        if not v:
            raise ValueError('GitHub token must not be empty')
        return v