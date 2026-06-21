from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "qa"

class UserRead(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    is_active: bool
    model_config = {"from_attributes": True}

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    username: str
    password: str

class EnvironmentBase(BaseModel):
    name: str
    base_url: str
    auth_type: str = "none"
    auth_config: dict = Field(default_factory=dict)
    variables: dict = Field(default_factory=dict)
    is_active: bool = True

class EnvironmentRead(EnvironmentBase):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}

class TestCaseBase(BaseModel):
    name: str
    product: str
    module: str | None = None
    tags: list = Field(default_factory=list)
    status: str = "active"
    steps: list = Field(default_factory=list)
    assertions: list = Field(default_factory=list)

class TestCaseRead(TestCaseBase):
    id: int
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class TestSuiteBase(BaseModel):
    name: str
    product: str
    suite_type: str = "smoke"
    test_case_order: list[int] = Field(default_factory=list)
    environment_id: int | None = None
    cron_schedule: str | None = None
    is_active: bool = True

class TestSuiteRead(TestSuiteBase):
    id: int
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class RunCreate(BaseModel):
    suite_id: int | None = None
    test_case_ids: list[int] = Field(default_factory=list)
    environment_id: int | None = None
    triggered_by: str = "manual"
    trigger_detail: dict = Field(default_factory=dict)

class RunRead(RunCreate):
    id: int
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    total_tests: int
    total_suites: int
    total_runs: int
    pass_rate: float
    avg_duration_ms: int
    last_run: RunRead | None = None

class UserUpdate(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    role: str | None = None
    is_active: bool | None = None


class ReportRead(BaseModel):
    id: int
    run_id: int
    summary: dict = Field(default_factory=dict)
    pdf_path: str | None = None
    html_path: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class SeedTemplateRead(BaseModel):
    name: str
    description: str | None = None
    parameters: dict = Field(default_factory=dict)


class SeedRunRequest(BaseModel):
    template_name: str
    params: dict = Field(default_factory=dict)
    run_id: str


class SeedCleanupRequest(BaseModel):
    run_id: str
    method: str = "prefix"


class RunStepRead(BaseModel):
    id: int
    run_id: int
    test_case_id: int | None = None
    step_index: int
    action_description: str
    status: str
    duration_ms: int | None = None
    error_message: str | None = None
    screenshot_path: str | None = None
    video_path: str | None = None
    console_log: list = Field(default_factory=list)
    dom_snapshot_path: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class WebhookRunRequest(BaseModel):
    suite_id: int | None = None
    test_case_ids: list[int] = Field(default_factory=list)
    environment_id: int | None = None
    trigger_detail: dict = Field(default_factory=dict)
