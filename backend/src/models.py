from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text, JSON, Numeric, Float, ForeignKeyConstraint, UniqueConstraint, CheckConstraint, and_, Table
from sqlalchemy.orm import relationship, Session, selectinload
from sqlalchemy.sql import func
from src.database import Base
from typing import Optional, List
from datetime import datetime, timedelta
import random
import time
from src.config.settings import settings

# SQLAlchemy Models
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(20), unique=True, index=True, nullable=True)
    name = Column(String(50), unique=True, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    persona = relationship("UserPersona", back_populates="user", uselist=False, cascade="all, delete-orphan")
    feedbacks = relationship("UserFeedback", back_populates="user", cascade="all, delete-orphan")
    student_profile = relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")


student_tags = Table(
    "student_tags",
    Base.metadata,
    Column("student_id", Integer, ForeignKey("students.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

conversation_tags = Table(
    "conversation_tags",
    Base.metadata,
    Column("conversation_id", Integer, ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)


class Student(Base):
    """
    Student profile data linked to User.
    A student is a user with additional profile information.
    """
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    school = Column(String(100), nullable=False, index=True)
    grade = Column(Integer, nullable=False, index=True)
    section = Column(String(10), nullable=True, index=True)  # Optional: A, B, C, etc.
    roll_number = Column(Integer, nullable=False, index=True)
    first_name = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship back to User
    user = relationship("User", back_populates="student_profile")
    tags = relationship("Tag", secondary=student_tags, back_populates="students")

    # Composite unique constraint: school + grade + section + roll_number uniquely identifies a student
    __table_args__ = (
        UniqueConstraint('school', 'grade', 'section', 'roll_number',
                        name='uq_student_identifier'),
    )

    def __repr__(self):
        return f"<Student(id={self.id}, user_id={self.user_id}, school='{self.school}', grade={self.grade}, section='{self.section}', roll={self.roll_number}, name='{self.first_name}')>"


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    students = relationship("Student", secondary=student_tags, back_populates="tags")
    conversations = relationship("Conversation", secondary=conversation_tags, back_populates="tags")

class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    feedback_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="feedbacks")

    __table_args__ = (
        CheckConstraint(
            'phone_number IS NOT NULL OR name IS NOT NULL', 
            name='check_user_has_identifier'
        ),
    )

class UserPersona(Base):
    __tablename__ = "user_personas"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    persona_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="persona")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=True, default="New Chat")
    prompt_version_id = Column(Integer, ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True)
    core_chat_theme = Column(String, nullable=True, default=None)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.timestamp")
    prompt_version = relationship("PromptVersion")
    memory = relationship("ConversationMemory", back_populates="conversation", uselist=False, cascade="all, delete-orphan")
    visit = relationship("ConversationVisit", back_populates="conversation", uselist=False, cascade="all, delete-orphan")
    evaluation = relationship("ConversationEvaluation", back_populates="conversation", uselist=False, cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=conversation_tags, back_populates="conversations")

class ConversationVisit(Base):
    __tablename__ = "conversation_visits"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    visit_number = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="visit")

    __table_args__ = (
        UniqueConstraint("user_id", "visit_number", name="uq_user_visit"),
    )

    def __repr__(self):
        return f"<ConversationVisit(id={self.id}, user_id={self.user_id}, visit_number={self.visit_number})>"

class ConversationMemory(Base):
    __tablename__ = "conversation_memories"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    memory_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    conversation = relationship("Conversation", back_populates="memory")


class ConversationEvaluation(Base):
    __tablename__ = "conversation_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    metrics = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="ready")
    computed_at = Column(DateTime(timezone=True), nullable=True)
    last_message_hash = Column(String(64), nullable=True)
    prompt_version_id = Column(Integer, ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True)
    attention_span = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    conversation = relationship("Conversation", back_populates="evaluation")
    prompt_version = relationship("PromptVersion")
    jobs = relationship("AnalysisJob", back_populates="conversation_evaluation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    is_user = Column(Boolean, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    responds_to_message_id = Column(Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    curiosity_score = Column(Integer, nullable=True)

    conversation = relationship("Conversation", back_populates="messages")
    pipeline_info = relationship("MessagePipelineData", back_populates="message", uselist=False, cascade="all, delete-orphan")

# New Table for Pipeline Data
class MessagePipelineData(Base):
    __tablename__ = "message_pipeline_data"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    pipeline_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    message = relationship("Message", back_populates="pipeline_info")


class ClassDailyMetrics(Base):
    __tablename__ = "class_daily_metrics"

    id = Column(Integer, primary_key=True, index=True)
    school = Column(String(100), nullable=False, index=True)
    grade = Column(Integer, nullable=False, index=True)
    section = Column(String(10), nullable=True, index=True)
    day = Column(Date, nullable=False, index=True)
    total_students = Column(Integer, nullable=True)
    conversations_started = Column(Integer, nullable=True)
    active_students = Column(Integer, nullable=True)
    conversations_with_messages = Column(Integer, nullable=True)
    total_user_messages = Column(Integer, nullable=True)
    total_ai_messages = Column(Integer, nullable=True)
    total_user_words = Column(Integer, nullable=True)
    total_ai_words = Column(Integer, nullable=True)
    total_minutes = Column(Numeric(12, 2), nullable=True)
    avg_minutes_per_conversation = Column(Numeric(8, 2), nullable=True)
    avg_user_msgs_per_conversation = Column(Numeric(8, 2), nullable=True)
    avg_ai_msgs_per_conversation = Column(Numeric(8, 2), nullable=True)
    user_messages_after_school = Column(Integer, nullable=True)
    total_messages_after_school = Column(Integer, nullable=True)
    after_school_conversations = Column(Integer, nullable=True)
    avg_user_words_per_message = Column(Numeric(8, 2), nullable=True)
    avg_ai_words_per_message = Column(Numeric(8, 2), nullable=True)
    after_school_user_pct = Column(Numeric(5, 2), nullable=True)
    metrics_extra = Column(JSON, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('school', 'grade', 'section', 'day', name='uq_class_daily_metrics'),
    )


class StudentDailyMetrics(Base):
    __tablename__ = "student_daily_metrics"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    day = Column(Date, nullable=False, index=True)
    conversations = Column(Integer, nullable=True)
    user_messages = Column(Integer, nullable=True)
    ai_messages = Column(Integer, nullable=True)
    user_words = Column(Integer, nullable=True)
    ai_words = Column(Integer, nullable=True)
    user_messages_after_school = Column(Integer, nullable=True)
    total_messages_after_school = Column(Integer, nullable=True)
    minutes_spent = Column(Numeric(12, 2), nullable=True)
    avg_user_words_per_message = Column(Numeric(8, 2), nullable=True)
    avg_ai_words_per_message = Column(Numeric(8, 2), nullable=True)
    metrics_extra = Column(JSON, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    student = relationship("Student")

    __table_args__ = (
        UniqueConstraint('student_id', 'day', name='uq_student_daily_metrics'),
    )


class StudentSummaryMetrics(Base):
    __tablename__ = "student_summary_metrics"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    cohort_start = Column(Date, nullable=False)
    cohort_end = Column(Date, nullable=False)
    total_conversations = Column(Integer, nullable=True)
    active_days = Column(Integer, nullable=True)
    total_minutes = Column(Numeric(12, 2), nullable=True)
    total_user_messages = Column(Integer, nullable=True)
    total_ai_messages = Column(Integer, nullable=True)
    total_user_words = Column(Integer, nullable=True)
    total_ai_words = Column(Integer, nullable=True)
    user_messages_after_school = Column(Integer, nullable=True)
    total_messages_after_school = Column(Integer, nullable=True)
    avg_user_words_per_message = Column(Numeric(8, 2), nullable=True)
    avg_ai_words_per_message = Column(Numeric(8, 2), nullable=True)
    after_school_user_pct = Column(Numeric(5, 2), nullable=True)
    metrics_extra = Column(JSON, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    student = relationship("Student")

    __table_args__ = (
        UniqueConstraint('student_id', 'cohort_start', 'cohort_end', name='uq_student_summary_window'),
    )


class ClassSummaryMetrics(Base):
    __tablename__ = "class_summary_metrics"

    id = Column(Integer, primary_key=True, index=True)
    school = Column(String(100), nullable=False, index=True)
    grade = Column(Integer, nullable=False, index=True)
    section = Column(String(10), nullable=True, index=True)
    cohort_start = Column(Date, nullable=False)
    cohort_end = Column(Date, nullable=False)
    total_students = Column(Integer, nullable=True)
    total_conversations = Column(Integer, nullable=True)
    total_user_messages = Column(Integer, nullable=True)
    total_ai_messages = Column(Integer, nullable=True)
    total_user_words = Column(Integer, nullable=True)
    total_ai_words = Column(Integer, nullable=True)
    total_minutes = Column(Numeric(12, 2), nullable=True)
    user_messages_after_school = Column(Integer, nullable=True)
    total_messages_after_school = Column(Integer, nullable=True)
    after_school_conversations = Column(Integer, nullable=True)
    avg_minutes_per_conversation = Column(Numeric(8, 2), nullable=True)
    avg_user_msgs_per_conversation = Column(Numeric(8, 2), nullable=True)
    avg_ai_msgs_per_conversation = Column(Numeric(8, 2), nullable=True)
    avg_user_words_per_conversation = Column(Numeric(8, 2), nullable=True)
    avg_ai_words_per_conversation = Column(Numeric(8, 2), nullable=True)
    avg_user_words_per_message = Column(Numeric(8, 2), nullable=True)
    avg_ai_words_per_message = Column(Numeric(8, 2), nullable=True)
    after_school_user_pct = Column(Numeric(5, 2), nullable=True)
    metrics_extra = Column(JSON, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('school', 'grade', 'section', 'cohort_start', 'cohort_end', name='uq_class_summary_window'),
    )


class HourlyActivityMetrics(Base):
    __tablename__ = "hourly_activity_metrics"

    id = Column(Integer, primary_key=True, index=True)
    school = Column(String(100), nullable=False, index=True)
    grade = Column(Integer, nullable=False, index=True)
    section = Column(String(10), nullable=True, index=True)
    window_start = Column(DateTime(timezone=True), nullable=False, index=True)
    window_end = Column(DateTime(timezone=True), nullable=False)
    user_message_count = Column(Integer, nullable=True)
    ai_message_count = Column(Integer, nullable=True)
    active_users = Column(Integer, nullable=True)
    after_school_user_count = Column(Integer, nullable=True)
    metrics_extra = Column(JSON, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('school', 'grade', 'section', 'window_start', name='uq_hourly_activity_window'),
    )


class LMHomework(Base):
    __tablename__ = "lm_homework"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Conversation where homework was generated
    conversation_id_generated = Column(Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)

    content = Column(Text, nullable=False)

    # Allowed: 'Complete', 'Incomplete', 'Active'
    status = Column(String(20), nullable=False, index=True, server_default="Active")

    remark = Column(Text, nullable=True)
    response_of_kid = Column(Text, nullable=True)

    # Conversation where the homework was discussed later
    conversation_id_discussed = Column(Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    conversation_generated = relationship("Conversation", foreign_keys=[conversation_id_generated])
    conversation_discussed = relationship("Conversation", foreign_keys=[conversation_id_discussed])

    __table_args__ = (
        CheckConstraint(
            "status IN ('Complete','Incomplete','Active')",
            name="ck_lm_homework_status_valid"
        ),
    )


class LMUserKnowledge(Base):
    __tablename__ = "lm_user_knowledge"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    remark = Column(Text, nullable=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User")
    conversation = relationship("Conversation")
    
    __table_args__ = (
        UniqueConstraint("user_id", "conversation_id", name="uq_user_conversation"),
    )


class ClassAnalysis(Base):
    __tablename__ = "class_analyses"

    id = Column(Integer, primary_key=True, index=True)
    school = Column(String(100), nullable=False, index=True)
    grade = Column(Integer, nullable=False, index=True)
    section = Column(String(10), nullable=True, index=True)
    analysis_text = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="ready")
    computed_at = Column(DateTime(timezone=True), nullable=True)
    last_message_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    jobs = relationship("AnalysisJob", back_populates="class_analysis", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("school", "grade", "section", name="uq_class_analysis_identifier"),
    )


class StudentAnalysis(Base):
    __tablename__ = "student_analyses"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    analysis_text = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="ready")
    computed_at = Column(DateTime(timezone=True), nullable=True)
    last_message_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    student = relationship("Student")
    jobs = relationship("AnalysisJob", back_populates="student_analysis", cascade="all, delete-orphan")


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), nullable=False, unique=True, index=True)
    analysis_kind = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="queued")
    error_message = Column(Text, nullable=True)
    class_analysis_id = Column(Integer, ForeignKey("class_analyses.id", ondelete="CASCADE"), nullable=True, index=True)
    student_analysis_id = Column(Integer, ForeignKey("student_analyses.id", ondelete="CASCADE"), nullable=True, index=True)
    conversation_evaluation_id = Column(Integer, ForeignKey("conversation_evaluations.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    class_analysis = relationship("ClassAnalysis", back_populates="jobs")
    student_analysis = relationship("StudentAnalysis", back_populates="jobs")
    conversation_evaluation = relationship("ConversationEvaluation", back_populates="jobs")


# --- Prompt Versioning Models ---

class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    prompt_purpose = Column(String(50), nullable=True, index=True)  # visit_1, visit_2, visit_3, steady_state, general
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    versions = relationship("PromptVersion", back_populates="prompt", cascade="all, delete-orphan")
    
    active_prompt_version = relationship(
        "PromptVersion",
        primaryjoin="and_(Prompt.id == PromptVersion.prompt_id, PromptVersion.is_active == True)",
        uselist=False,
        viewonly=True
    )

    def __repr__(self):
        return f"<Prompt(id={self.id}, name='{self.name}', purpose='{self.prompt_purpose}')>"

class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    version_number = Column(Integer, nullable=False)
    prompt_text = Column(Text, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False, index=True)
    is_production = Column(Boolean, default=False, nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    prompt = relationship("Prompt", back_populates="versions")
    user = relationship("User")

    __table_args__ = (
        # Ensure version_number is unique per prompt_id
        ForeignKeyConstraint(["prompt_id"], ["prompts.id"], name="fk_prompt_version_prompt_id"),
        UniqueConstraint("prompt_id", "version_number", name="uq_prompt_id_version_number"),
        # Note: The constraint for a single active version (is_active=True per prompt_id)
        # will be handled by a partial unique index created via Alembic.
    )

    def __repr__(self):
        return f"<PromptVersion(id={self.id}, prompt_id={self.prompt_id}, version={self.version_number}, active={self.is_active}, production={self.is_production}, user_id={self.user_id})>"

# --- CRUD Helper Functions ---

# DEPRECATED: No longer using unique name suffixes
# Names are now treated like phone numbers - consistent identifiers
# def generate_unique_name(db: Session, base_name: str) -> str:
#     """Generate a unique name by appending 3 random digits to the base name."""
#     base_name = base_name.strip().title()  # "surya" -> "Surya"
#     
#     # Try 5 times to find a unique name
#     for _ in range(5):
#         suffix = random.randint(100, 999)  # 3 digits: 100-999
#         candidate_name = f"{base_name}{suffix}"
#         if not db.query(User).filter(User.name == candidate_name).first():
#             return candidate_name
#     
#     # Fallback to timestamp if all attempts fail
#     timestamp = int(time.time()) % 1000
#     return f"{base_name}{timestamp}"

def get_or_create_user_by_phone(db: Session, phone_number: str) -> User:
    """Get a user by phone number or create if not exists."""
    user = db.query(User).filter(User.phone_number == phone_number).first()
    if not user:
        user = User(phone_number=phone_number)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def get_or_create_user_by_name(db: Session, name: str) -> User:
    """Get a user by name or create if not exists."""
    user = db.query(User).filter(User.name == name).first()
    if not user:
        user = User(name=name)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def determine_identifier_type(identifier: str) -> str:
    """Determine if identifier is a phone number or name."""
    # If it's all digits and 10-15 characters, treat as phone
    if identifier.isdigit() and 10 <= len(identifier) <= 15:
        return "phone"
    return "name"

def get_or_create_user_by_identifier(db: Session, identifier: str) -> tuple[User, Optional[str]]:
    """
    Get or create user by identifier (phone or name).
    Returns tuple of (user, generated_name) where generated_name is None for phone logins.
    """
    identifier_type = determine_identifier_type(identifier)
    
    if identifier_type == "phone":
        user = get_or_create_user_by_phone(db, identifier)
        return user, None
    else:
        # Use name directly without suffix (consistent like phone numbers)
        normalized_name = identifier.strip().title()  # "surya" -> "Surya"
        user = get_or_create_user_by_name(db, normalized_name)
        return user, None  # No generated name, use original identifier

# Keep old function for backward compatibility
def get_or_create_user(db: Session, phone_number: str) -> User:
    """Get a user by phone number or create if not exists. (Backward compatibility)"""
    return get_or_create_user_by_phone(db, phone_number)

def create_conversation(db: Session, user_id: int, title: Optional[str] = "New Chat", prompt_version_id: Optional[int] = None, core_chat_theme: Optional[str] = None) -> Conversation:
    """Creates a new conversation for a user."""
    conversation = Conversation(user_id=user_id, title=title, prompt_version_id=prompt_version_id, core_chat_theme=core_chat_theme)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

def get_conversation(db: Session, conversation_id: int) -> Optional[Conversation]:
    """Gets a specific conversation by its ID."""
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()

def update_conversation_title(db: Session, conversation_id: int, new_title: str, user_id: int) -> Optional[Conversation]:
    """Updates the title of a specific conversation for a user."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()

    if not conversation:
        return None # Or raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.user_id != user_id:
        # Or raise HTTPException(status_code=403, detail="Not authorized to update this conversation")
        return None # Indicate authorization failure or handle in router

    if not new_title.strip():
        # Or raise HTTPException(status_code=400, detail="Title cannot be empty")
        return None # Indicate validation failure or handle in router

    conversation.title = new_title.strip()
    # conversation.updated_at = func.now() # This is handled by onupdate=func.now() in the model
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

def list_user_conversations(
    db: Session,
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    tags: Optional[List[str]] = None,
    tag_mode: str = "any",
) -> List[Conversation]:
    """Lists conversations for a given user, most recent first."""
    query = (
        db.query(Conversation)
        .options(selectinload(Conversation.tags))
        .filter(Conversation.user_id == user_id)
    )
    if tags:
        if tag_mode == "all":
            query = (
                query.join(Conversation.tags)
                .filter(Tag.name.in_(tags))
                .group_by(Conversation.id)
                .having(func.count(func.distinct(Tag.id)) == len(tags))
            )
        else:
            query = query.join(Conversation.tags).filter(Tag.name.in_(tags)).distinct()
    return (
        query.order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

def delete_conversation(db: Session, conversation_id: int, user_id: int) -> bool:
    """Deletes a conversation by its ID, ensuring user ownership."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id
    ).first()

    if not conversation:
        # Conversation not found or user does not have permission
        return False

    db.delete(conversation)
    db.commit()
    return True

def save_message(
    db: Session,
    conversation_id: int,
    content: str,
    is_user: bool,
    responds_to_message_id: Optional[int] = None,
    curiosity_score: Optional[int] = None
) -> Message:
    """Save a message to a specific conversation."""
    conversation = get_conversation(db, conversation_id)
    if not conversation:
        raise ValueError(f"Conversation with ID {conversation_id} not found.")

    message = Message(
        conversation_id=conversation_id,
        content=content,
        is_user=is_user,
        responds_to_message_id=responds_to_message_id,
        curiosity_score=curiosity_score
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    conversation.updated_at = func.now()
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return message

def get_message_count_for_user(db: Session, user_id: int) -> int:
    """Get the total count of messages sent *by the user* across all their conversations."""
    count = db.query(func.count(Message.id))\
              .join(Conversation)\
              .filter(Conversation.user_id == user_id, Message.is_user == True)\
              .scalar()
    return count if count is not None else 0

def get_conversation_history(db: Session, conversation_id: int, limit: int = 100) -> List[Message]:
    """Get message history for a specific conversation, ordered chronologically."""
    messages = db.query(Message)\
                 .filter(Message.conversation_id == conversation_id)\
                 .order_by(Message.timestamp.asc())\
                 .limit(limit)\
                 .all()
    return messages

def get_ai_response_for_user_message(db: Session, user_message_id: int) -> Optional[Message]:
    """Get the AI response message that corresponds to a specific user message ID."""
    ai_response = db.query(Message).filter(
        Message.responds_to_message_id == user_message_id,
        Message.is_user == False
    ).first()
    return ai_response

def get_memory_for_conversation(db: Session, conversation_id: int) -> Optional[ConversationMemory]:
    """Get the memory for a specific conversation by its ID."""
    return db.query(ConversationMemory).filter(ConversationMemory.conversation_id == conversation_id).first()

def get_conversations_needing_memory(db: Session) -> List[int]:
    """
    Get IDs of conversations that have been inactive for a certain period
    and either don't have a memory or their memory is older than their last update.
    """
    inactivity_threshold = datetime.utcnow() - timedelta(hours=settings.MEMORY_INACTIVITY_THRESHOLD_HOURS)

    # Find conversations that were updated before the threshold
    # and either have no memory or the memory is older than the last conversation update.
    conversations_to_process = (
        db.query(Conversation)
        .outerjoin(ConversationMemory, Conversation.id == ConversationMemory.conversation_id)
        .filter(
            Conversation.updated_at < inactivity_threshold,
            and_(Conversation.updated_at > Conversation.created_at), # Exclude new, empty conversations
            (ConversationMemory.id == None) | (ConversationMemory.updated_at < Conversation.updated_at)
        )
        .all()
    )
    
    return [c.id for c in conversations_to_process]

def get_conversations_needing_memory_for_user(
    db: Session,
    user_id: int,
    only_needing: bool = True,
    include_empty: bool = False,
) -> List[int]:
    """
    Returns conversation IDs for a user based on filters.
    - only_needing: if True, include only conversations that either don't have a memory
      or whose memory is older than the conversation update, and that are inactive beyond threshold
      (mirrors get_conversations_needing_memory logic).
    - include_empty: if False, exclude conversations with zero messages (heuristic: updated_at > created_at).
    """
    inactivity_threshold = datetime.utcnow() - timedelta(hours=settings.MEMORY_INACTIVITY_THRESHOLD_HOURS)

    query = (
        db.query(Conversation)
        .outerjoin(ConversationMemory, Conversation.id == ConversationMemory.conversation_id)
        .filter(Conversation.user_id == user_id)
    )

    if only_needing:
        query = query.filter(
            Conversation.updated_at < inactivity_threshold,
            (ConversationMemory.id == None) | (ConversationMemory.updated_at < Conversation.updated_at),
        )
        if not include_empty:
            query = query.filter(Conversation.updated_at > Conversation.created_at)
    else:
        if not include_empty:
            query = query.filter(Conversation.updated_at > Conversation.created_at)

    conversations = query.all()
    return [c.id for c in conversations]

def get_users_needing_persona_generation(db: Session) -> List[int]:
    """
    Returns a list of user IDs who need their persona generated or updated.
    
    Simplified: Returns all users with at least 3 conversations.
    Persona generation requires minimum 3 conversations for meaningful analysis.
    """
    # TODO: Later, add smarter logic to check if persona needs updating
    # (e.g., based on new conversations since last persona update)
    
    # OLD LOGIC (commented out - was based on ConversationMemory which we're not using):
    # # 1. Users with an existing persona but newer memories
    # users_to_update = (
    #     db.query(User.id)
    #     .join(UserPersona)
    #     .join(Conversation, User.id == Conversation.user_id)
    #     .join(ConversationMemory, Conversation.id == ConversationMemory.conversation_id)
    #     .group_by(User.id, UserPersona.updated_at)
    #     .having(func.max(ConversationMemory.created_at) > UserPersona.updated_at)
    #     .all()
    # )
    # # 2. Users with memories but no persona
    # users_to_create = (
    #     db.query(User.id)
    #     .join(Conversation, User.id == Conversation.user_id)
    #     .join(ConversationMemory, Conversation.id == ConversationMemory.conversation_id)
    #     .outerjoin(UserPersona, User.id == UserPersona.user_id)
    #     .filter(UserPersona.id == None)
    #     .group_by(User.id)
    #     .all()
    # )
    # user_ids_to_update = {u[0] for u in users_to_update}
    # user_ids_to_create = {u[0] for u in users_to_create}
    # return list(user_ids_to_update.union(user_ids_to_create))
    
    # NEW LOGIC: All users with >= 3 conversations
    users_with_enough_conversations = (
        db.query(User.id)
        .join(Conversation, User.id == Conversation.user_id)
        .group_by(User.id)
        .having(func.count(Conversation.id) >= 3)
        .all()
    )
    
    return [u[0] for u in users_with_enough_conversations]

def save_message_pipeline_data(db: Session, message_id: int, pipeline_data_dict: dict) -> MessagePipelineData:
    """Saves pipeline data for a specific message."""
    db_pipeline_data = MessagePipelineData(message_id=message_id, pipeline_data=pipeline_data_dict)
    db.add(db_pipeline_data)
    db.commit()
    db.refresh(db_pipeline_data)
    return db_pipeline_data

# --- Onboarding System Helper Functions ---

def count_user_conversations(db: Session, user_id: int) -> int:
    """Count the number of conversations for a user."""
    return db.query(Conversation).filter(Conversation.user_id == user_id).count()

def select_prompt_purpose_for_visit(visit_number: int) -> str:
    """
    Returns the prompt PURPOSE to query by based on visit number.
    Visit 1 = 'visit_1', Visit 2 = 'visit_2', Visit 3 = 'visit_3', Visit 4+ = 'steady_state'
    """
    if visit_number == 1:
        return "visit_1"
    elif visit_number == 2:
        return "visit_2"
    elif visit_number == 3:
        return "visit_3"
    else:
        return "steady_state"

def get_production_prompt_by_purpose(db: Session, prompt_purpose: str) -> Optional['PromptVersion']:
    """
    Get production prompt version by purpose.
    Falls back to simplified_conversation if purpose-specific prompt not found.
    """
    from src.models import Prompt, PromptVersion
    import logging
    logger = logging.getLogger(__name__)
    
    prompt = db.query(Prompt).filter(Prompt.prompt_purpose == prompt_purpose).first()
    
    if not prompt:
        logger.warning(f"No prompt found for purpose {prompt_purpose}, falling back to simplified_conversation")
        prompt = db.query(Prompt).filter(Prompt.name == "simplified_conversation").first()
        if not prompt:
            logger.error("No valid prompt found (including fallback)")
            return None
    
    # Get production version
    production_version = db.query(PromptVersion).filter(
        PromptVersion.prompt_id == prompt.id,
        PromptVersion.is_production == True
    ).first()
    
    if not production_version:
        # Fallback to latest version if no production version set
        production_version = db.query(PromptVersion).filter(
            PromptVersion.prompt_id == prompt.id
        ).order_by(PromptVersion.version_number.desc()).first()
    
    return production_version

def has_messages(db: Session, conversation_id: int) -> bool:
    """
    Check if a conversation has any messages.
    """
    message_count = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).count()
    return message_count > 0

def record_conversation_visit(db: Session, conversation_id: int, user_id: int, visit_number: int) -> ConversationVisit:
    """
    Record visit number for a conversation.
    Raises IntegrityError if (user_id, visit_number) already exists (race condition).
    Note: Don't commit here - let caller handle transaction.
    """
    visit_record = ConversationVisit(
        conversation_id=conversation_id,
        user_id=user_id,
        visit_number=visit_number
    )
    db.add(visit_record)
    # Note: Caller should handle commit and IntegrityError for race conditions
    return visit_record

def get_conversation_visit(db: Session, conversation_id: int) -> Optional[ConversationVisit]:
    """Get visit information for a conversation."""
    return db.query(ConversationVisit).filter(
        ConversationVisit.conversation_id == conversation_id
    ).first()

def get_user_conversations_list(db: Session, user_id: int) -> List[Conversation]:
    """
    Get all conversations for a user, ordered chronologically.
    Used for memory generation across multiple conversations.
    """
    return db.query(Conversation).filter(
        Conversation.user_id == user_id
    ).order_by(Conversation.created_at.asc()).all()

def get_conversation_with_visit(db: Session, conversation_id: int) -> Optional[dict]:
    """
    Get conversation with visit number included.
    Returns a dictionary with conversation data and visit_number.
    """
    conversation = (
        db.query(Conversation)
        .options(selectinload(Conversation.tags))
        .filter(Conversation.id == conversation_id)
        .first()
    )
    if not conversation:
        return None
    
    visit_record = db.query(ConversationVisit).filter(
        ConversationVisit.conversation_id == conversation_id
    ).first()
    
    # Convert to dict and add visit_number
    conv_dict = {
        "id": conversation.id,
        "user_id": conversation.user_id,
        "title": conversation.title,
        "visit_number": visit_record.visit_number if visit_record else None,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "core_chat_theme": conversation.core_chat_theme,
        "tags": [tag.name for tag in conversation.tags],
    }
    
    return conv_dict

def get_user_conversations_with_visits(
    db: Session,
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    tags: Optional[List[str]] = None,
    tag_mode: str = "any",
) -> List[dict]:
    """
    Get conversations with visit numbers for a user.
    Returns list of dictionaries with conversation data and visit_number.
    """
    conversations = list_user_conversations(db, user_id, limit, offset, tags=tags, tag_mode=tag_mode)
    
    result = []
    for conv in conversations:
        visit_record = db.query(ConversationVisit).filter(
            ConversationVisit.conversation_id == conv.id
        ).first()
        
        conv_dict = {
            "id": conv.id,
            "title": conv.title,
            "visit_number": visit_record.visit_number if visit_record else None,
            "updated_at": conv.updated_at,
            "core_chat_theme": conv.core_chat_theme,
            "tags": [tag.name for tag in conv.tags],
        }
        result.append(conv_dict)
    
    return result


def update_conversation_core_chat_theme(db: Session, conversation_id: int, new_core_chat_theme: Optional[str], user_id: int) -> Optional[Conversation]:
    """Updates the core_chat_theme of a specific conversation for a user."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()

    if not conversation:
        return None # Conversation not found

    if conversation.user_id != user_id:
        return None # Not authorized to update this conversation

    conversation.core_chat_theme = new_core_chat_theme
    # conversation.updated_at = func.now() # This is handled by onupdate=func.now() in the model
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

# --- Student CRUD Functions ---

def get_or_create_student(
    db: Session,
    school: str,
    grade: int,
    section: Optional[str],
    roll_number: int,
    first_name: str
) -> User:
    """
    Get or create a student by their unique identifier (school, grade, section, roll_number).
    Returns the associated User object.
    """
    # Normalize inputs
    school = school.strip()
    first_name = first_name.strip().title()
    section = section.strip().upper() if section else None

    # Check if student already exists
    student = db.query(Student).filter(
        Student.school == school,
        Student.grade == grade,
        Student.section == section,
        Student.roll_number == roll_number
    ).first()

    if student:
        # Student exists, return the associated user
        return student.user

    # Student doesn't exist, create new user and student profile
    # Create a unique name for the user table (composite identifier)
    section_part = f"_{section}" if section else ""
    # Replace spaces in school name with underscores for cleaner username
    school_normalized = school.replace(" ", "_")
    user_name = f"{first_name}_{school_normalized}_{grade}{section_part}_{roll_number}"

    user = User(name=user_name)
    db.add(user)
    db.flush()  # Get user.id without committing

    student = Student(
        user_id=user.id,
        school=school,
        grade=grade,
        section=section,
        roll_number=roll_number,
        first_name=first_name
    )
    db.add(student)
    db.commit()
    db.refresh(user)

    return user

def get_student_by_user_id(db: Session, user_id: int) -> Optional[Student]:
    """Get student profile by user_id."""
    return db.query(Student).filter(Student.user_id == user_id).first()
