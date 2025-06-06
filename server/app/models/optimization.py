"""
Data models for optimization analytics and insights
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class OptimizationRecommendationType(str, Enum):
    """Types of optimization recommendations"""
    CACHING = "caching"
    BATCH_PROCESSING = "batch_processing"
    BUDGET_ALERT = "budget_alert"
    TEMPLATE_OPTIMIZATION = "template_optimization"
    RAG_ENHANCEMENT = "rag_enhancement"
    PROMPT_ENGINEERING = "prompt_engineering"
    GENERAL = "general"

class Priority(str, Enum):
    """Priority levels for recommendations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ImplementationEffort(str, Enum):
    """Implementation effort levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class OptimizationRecommendation(BaseModel):
    """Individual optimization recommendation"""
    type: OptimizationRecommendationType
    priority: Priority
    description: str
    potential_savings: str
    implementation_effort: ImplementationEffort

class TokenUsageRecord(BaseModel):
    """Token usage record for analytics"""
    user_id: str
    timestamp: datetime
    prompt_type: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    cached: bool = False
    optimization_applied: Optional[str] = None

class RAGPerformanceMetrics(BaseModel):
    """RAG system performance metrics"""
    total_queries: int = Field(description="Total number of RAG queries")
    average_retrieval_time: float = Field(description="Average retrieval time in seconds")
    knowledge_sources_used: int = Field(description="Number of knowledge sources accessed")
    compression_ratio: float = Field(description="Average context compression ratio")

class TokenUsageAnalytics(BaseModel):
    """Token usage analytics for a user"""
    user_id: str
    period_days: int
    total_tokens: int
    total_requests: int
    cached_requests: int
    cache_hit_rate: float = Field(ge=0, le=1, description="Cache hit rate as a decimal")
    estimated_cost: float
    daily_breakdown: Dict[str, Dict[str, Any]]
    type_breakdown: Dict[str, Dict[str, Any]]
    analyzed_at: datetime

class OptimizationInsights(BaseModel):
    """Comprehensive optimization insights"""
    user_id: str
    optimization_score: int = Field(ge=0, le=100, description="Overall optimization score")
    potential_savings: Dict[str, Any]
    recommendations: List[OptimizationRecommendation]
    rag_performance: RAGPerformanceMetrics
    generated_at: datetime

class TokenBudgetAlert(BaseModel):
    """Token budget alert configuration"""
    user_id: str
    daily_limit: int
    weekly_limit: int
    monthly_limit: int
    alert_thresholds: List[int] = Field(default=[50, 75, 90], description="Alert at these percentages")
    email_notifications: bool = True
    webhook_url: Optional[str] = None

class CostBreakdown(BaseModel):
    """Detailed cost breakdown"""
    user_id: str
    period_days: int
    total_cost_usd: float
    total_tokens: int
    average_cost_per_request: float
    cost_by_service: Dict[str, Dict[str, Any]]
    daily_costs: Dict[str, Dict[str, float]]
    projected_monthly_cost: float
    optimization_potential: Dict[str, Any]

class OptimizationTestResult(BaseModel):
    """Results from optimization testing"""
    test_type: str
    sample_size: int
    description: str
    results: Dict[str, Any]
    extrapolated_monthly_impact: Dict[str, Any]
    tested_at: str

class RetrievalStrategy(str, Enum):
    """RAG retrieval strategies"""
    SIMPLE = "simple"
    HYBRID = "hybrid"
    CONTEXTUAL = "contextual"
    ADAPTIVE = "adaptive"

class RetrievalContext(BaseModel):
    """Context for RAG retrieval"""
    user_id: str
    conversation_history: List[Dict[str, str]] = []
    current_question: str
    domain_context: Optional[str] = None
    urgency_level: str = "normal"
    max_tokens: int = 2000

class RetrievalResult(BaseModel):
    """Result from RAG retrieval"""
    content: str
    sources: List[str]
    confidence_score: float = Field(ge=0, le=1)
    tokens_used: int
    retrieval_time: float
    strategy_used: RetrievalStrategy
    compression_applied: bool = False

class PromptOptimizationResult(BaseModel):
    """Result from prompt optimization"""
    original_prompt: str
    optimized_prompt: str
    original_tokens: int
    optimized_tokens: int
    tokens_saved: int
    optimization_strategies: List[str]
    quality_preserved: bool = True

class BatchProcessingConfig(BaseModel):
    """Configuration for batch processing"""
    batch_size: int = Field(ge=1, le=100)
    parallel_processes: int = Field(ge=1, le=10)
    timeout_seconds: int = Field(ge=30, le=300)
    retry_attempts: int = Field(ge=1, le=5)

class OptimizationDashboard(BaseModel):
    """Complete optimization dashboard data"""
    user_id: str
    current_usage: TokenUsageAnalytics
    insights: OptimizationInsights
    cost_breakdown: CostBreakdown
    recent_optimizations: List[Dict[str, Any]]
    performance_trends: Dict[str, List[float]]
    generated_at: datetime 