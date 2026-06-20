from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .database import Base


def utcnow():
    return datetime.utcnow()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="qa")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Environment(Base):
    __tablename__ = "environments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    base_url: Mapped[str] = mapped_column(String(500))
    auth_type: Mapped[str] = mapped_column(String(30), default="none")
    auth_config: Mapped[dict] = mapped_column(JSON, default=dict)
    variables: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class TestCase(Base, TimestampMixin):
    __tablename__ = "test_cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    product: Mapped[str] = mapped_column(String(50), index=True)
    module: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="active")
    steps: Mapped[list] = mapped_column(JSON, default=list)
    assertions: Mapped[list] = mapped_column(JSON, default=list)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class TestSuite(Base, TimestampMixin):
    __tablename__ = "test_suites"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    product: Mapped[str] = mapped_column(String(50))
    suite_type: Mapped[str] = mapped_column(String(50), default="smoke")
    test_case_order: Mapped[list] = mapped_column(JSON, default=list)
    environment_id: Mapped[int | None] = mapped_column(ForeignKey("environments.id"), nullable=True)
    cron_schedule: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class TestRun(Base):
    __tablename__ = "test_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    suite_id: Mapped[int | None] = mapped_column(ForeignKey("test_suites.id"), nullable=True)
    test_case_ids: Mapped[list] = mapped_column(JSON, default=list)
    environment_id: Mapped[int | None] = mapped_column(ForeignKey("environments.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    triggered_by: Mapped[str] = mapped_column(String(30), default="manual")
    trigger_detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RunStep(Base):
    __tablename__ = "run_steps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("test_runs.id"))
    test_case_id: Mapped[int | None] = mapped_column(ForeignKey("test_cases.id"), nullable=True)
    step_index: Mapped[int] = mapped_column(Integer)
    action_description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    console_log: Mapped[list] = mapped_column(JSON, default=list)
    dom_snapshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class StepAssertion(Base):
    __tablename__ = "step_assertions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_step_id: Mapped[int] = mapped_column(ForeignKey("run_steps.id"))
    assertion_type: Mapped[str] = mapped_column(String(50))
    expected: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual: Mapped[str | None] = mapped_column(Text, nullable=True)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    tolerance: Mapped[str | None] = mapped_column(String(50), nullable=True)
    diff_percentage: Mapped[str | None] = mapped_column(String(50), nullable=True)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("test_runs.id"))
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    html_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("test_runs.id"), nullable=True)
    channel: Mapped[str] = mapped_column(String(50))
    event: Mapped[str] = mapped_column(String(50))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
