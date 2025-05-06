"""
데이터베이스 모델 정의 모듈

SQLAlchemy 기반 모델 클래스들을 정의합니다.
"""
import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Task(Base):
    """분석 작업 모델"""
    __tablename__ = "tasks"
    
    id = Column(String(50), primary_key=True)
    url = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False)
    progress = Column(Integer, nullable=False, default=0)
    message = Column(Text)
    error = Column(Text)
    result_id = Column(String(50))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # 관계 정의
    steps = relationship("TaskStep", back_populates="task", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Task(id='{self.id}', url='{self.url}', status='{self.status}')>"


class TaskStep(Base):
    """작업 단계 모델"""
    __tablename__ = "task_steps"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(50), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    step_index = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # 관계 정의
    task = relationship("Task", back_populates="steps")
    
    def __repr__(self):
        return f"<TaskStep(task_id='{self.task_id}', index={self.step_index}, status='{self.status}')>"


class WebsiteData(Base):
    """웹사이트 분석 데이터 모델"""
    __tablename__ = "website_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(50), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255))
    description = Column(Text)
    main_url = Column(String(255), nullable=False)
    pages_count = Column(Integer, default=0)
    components_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<WebsiteData(task_id='{self.task_id}', title='{self.title}')>"


class AnalysisResult(Base):
    """분석 결과 모델"""
    __tablename__ = "analysis_results"
    
    id = Column(String(50), primary_key=True)
    task_id = Column(String(50), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    url = Column(String(255), nullable=False)
    title = Column(String(255))
    description = Column(Text)
    plan_text = Column(Text)
    design_analysis = Column(Text)
    components_json = Column(Text)  # JSON 형식 문자열
    pages_json = Column(Text)  # JSON 형식 문자열
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    exported = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<AnalysisResult(id='{self.id}', task_id='{self.task_id}')>"


class ExportHistory(Base):
    """내보내기 기록 모델"""
    __tablename__ = "export_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    result_id = Column(String(50), ForeignKey("analysis_results.id", ondelete="CASCADE"), nullable=False)
    format_type = Column(String(20), nullable=False)  # markdown, pdf, html, json 등
    file_path = Column(String(255))
    external_url = Column(String(255))  # Notion, Google Drive 등 외부 URL
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<ExportHistory(result_id='{self.result_id}', format_type='{self.format_type}')>"


class APIUsage(Base):
    """API 사용량 모델"""
    __tablename__ = "api_usage"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    api_type = Column(String(20), nullable=False)  # openai, deepseek, claude 등
    endpoint = Column(String(50), nullable=False)  # chat, embedding 등
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    task_id = Column(String(50))
    
    def __repr__(self):
        return f"<APIUsage(date='{self.date}', api_type='{self.api_type}', endpoint='{self.endpoint}')>" 