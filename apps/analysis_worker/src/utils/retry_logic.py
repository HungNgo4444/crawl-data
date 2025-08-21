"""
Retry Logic and Error Recovery
Exponential backoff and connection failure recovery utilities
Author: James (Dev Agent)  
Date: 2025-08-12
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
from dataclasses import dataclass
from enum import Enum
from functools import wraps
import traceback


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RetryStrategy(Enum):
    """Retry strategy types"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    FIBONACCI_BACKOFF = "fibonacci_backoff"


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    backoff_multiplier: float = 2.0
    jitter: bool = True
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    non_retryable_exceptions: Tuple[Type[Exception], ...] = ()


@dataclass
class RetryAttempt:
    """Single retry attempt information"""
    attempt_number: int
    timestamp: datetime
    delay_seconds: float
    exception: Optional[Exception]
    error_message: str
    success: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "attempt_number": self.attempt_number,
            "timestamp": self.timestamp.isoformat(),
            "delay_seconds": self.delay_seconds,
            "exception_type": type(self.exception).__name__ if self.exception else None,
            "error_message": self.error_message,
            "success": self.success
        }


@dataclass
class RetryResult:
    """Retry operation result"""
    success: bool
    final_result: Any
    total_attempts: int
    total_duration: float
    attempts: List[RetryAttempt]
    final_exception: Optional[Exception]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "total_attempts": self.total_attempts,
            "total_duration": self.total_duration,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "final_exception": str(self.final_exception) if self.final_exception else None
        }


class RetryableError(Exception):
    """Base class for retryable errors"""
    
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        super().__init__(message)
        self.severity = severity


class NonRetryableError(Exception):
    """Base class for non-retryable errors"""
    pass


class ConnectionError(RetryableError):
    """Connection-related error"""
    
    def __init__(self, message: str):
        super().__init__(message, ErrorSeverity.HIGH)


class TimeoutError(RetryableError):
    """Timeout-related error"""
    
    def __init__(self, message: str):
        super().__init__(message, ErrorSeverity.MEDIUM)


class RateLimitError(RetryableError):
    """Rate limit error"""
    
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message, ErrorSeverity.LOW)
        self.retry_after = retry_after


class AuthenticationError(NonRetryableError):
    """Authentication error - should not retry"""
    pass


class ValidationError(NonRetryableError):
    """Validation error - should not retry"""
    pass


class RetryManager:
    """
    Comprehensive retry manager with exponential backoff
    Handles connection failures, timeouts, and error categorization
    """
    
    def __init__(self):
        """Initialize retry manager"""
        self.logger = logging.getLogger(__name__)
        
        # Default configurations for different operation types
        self.default_configs = {
            "http_request": RetryConfig(
                max_attempts=3,
                base_delay=1.0,
                max_delay=30.0,
                backoff_multiplier=2.0,
                retryable_exceptions=(
                    ConnectionError, TimeoutError, RateLimitError,
                    # Standard library exceptions
                    OSError, IOError,
                    # aiohttp exceptions
                    Exception  # Catch-all for now, will be refined
                ),
                non_retryable_exceptions=(
                    AuthenticationError, ValidationError,
                    ValueError, TypeError
                )
            ),
            "database_operation": RetryConfig(
                max_attempts=5,
                base_delay=0.5,
                max_delay=10.0,
                backoff_multiplier=1.5,
                retryable_exceptions=(
                    ConnectionError, TimeoutError,
                    # SQLAlchemy exceptions would go here
                    Exception
                ),
                non_retryable_exceptions=(
                    ValidationError, ValueError
                )
            ),
            "gwen3_analysis": RetryConfig(
                max_attempts=3,
                base_delay=2.0,
                max_delay=60.0,
                backoff_multiplier=2.0,
                retryable_exceptions=(
                    ConnectionError, TimeoutError, RateLimitError,
                    Exception
                ),
                non_retryable_exceptions=(
                    ValidationError, AuthenticationError
                )
            ),
            "redis_operation": RetryConfig(
                max_attempts=3,
                base_delay=0.1,
                max_delay=5.0,
                backoff_multiplier=2.0,
                retryable_exceptions=(
                    ConnectionError, TimeoutError,
                    Exception
                ),
                non_retryable_exceptions=(
                    ValidationError,
                )
            )
        }
    
    def calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """
        Calculate delay for retry attempt based on strategy
        
        Args:
            attempt: Attempt number (1-based)
            config: Retry configuration
            
        Returns:
            Delay in seconds
        """
        if config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = config.base_delay * (config.backoff_multiplier ** (attempt - 1))
        elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = config.base_delay * attempt
        elif config.strategy == RetryStrategy.FIXED_DELAY:
            delay = config.base_delay
        elif config.strategy == RetryStrategy.FIBONACCI_BACKOFF:
            # Fibonacci sequence for delays
            if attempt <= 2:
                delay = config.base_delay
            else:
                fib_a, fib_b = 1, 1
                for _ in range(attempt - 2):
                    fib_a, fib_b = fib_b, fib_a + fib_b
                delay = config.base_delay * fib_b
        else:
            delay = config.base_delay
        
        # Apply max delay limit
        delay = min(delay, config.max_delay)
        
        # Add jitter to avoid thundering herd
        if config.jitter:
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)  # Ensure non-negative
        
        return delay
    
    def is_retryable_exception(self, exception: Exception, config: RetryConfig) -> bool:
        """
        Check if exception is retryable based on configuration
        
        Args:
            exception: Exception to check
            config: Retry configuration
            
        Returns:
            True if exception is retryable
        """
        # Check non-retryable exceptions first
        if isinstance(exception, config.non_retryable_exceptions):
            return False
        
        # Check retryable exceptions
        if isinstance(exception, config.retryable_exceptions):
            return True
        
        # Check specific error patterns
        error_message = str(exception).lower()
        
        # Connection-related errors
        connection_keywords = [
            "connection", "connect", "network", "socket", "timeout",
            "unreachable", "refused", "reset", "broken pipe"
        ]
        
        if any(keyword in error_message for keyword in connection_keywords):
            return True
        
        # Temporary service issues
        temporary_keywords = [
            "service unavailable", "server error", "internal error",
            "temporary", "retry", "rate limit", "throttl"
        ]
        
        if any(keyword in error_message for keyword in temporary_keywords):
            return True
        
        # Default to non-retryable for safety
        return False
    
    async def retry_async(self, 
                         func: Callable,
                         config: Optional[RetryConfig] = None,
                         operation_type: str = "default",
                         *args, **kwargs) -> RetryResult:
        """
        Retry async function with exponential backoff
        
        Args:
            func: Async function to retry
            config: Retry configuration (optional)
            operation_type: Type of operation for default config
            *args, **kwargs: Arguments for function
            
        Returns:
            RetryResult with operation results
        """
        if config is None:
            config = self.default_configs.get(operation_type, RetryConfig())
        
        attempts = []
        start_time = time.time()
        final_exception = None
        
        for attempt_num in range(1, config.max_attempts + 1):
            attempt_start = time.time()
            
            try:
                # Call the function
                result = await func(*args, **kwargs)
                
                # Success
                attempt = RetryAttempt(
                    attempt_number=attempt_num,
                    timestamp=datetime.now(),
                    delay_seconds=0.0,
                    exception=None,
                    error_message="",
                    success=True
                )
                attempts.append(attempt)
                
                total_duration = time.time() - start_time
                
                self.logger.info(f"Operation succeeded on attempt {attempt_num}/{config.max_attempts}")
                
                return RetryResult(
                    success=True,
                    final_result=result,
                    total_attempts=attempt_num,
                    total_duration=total_duration,
                    attempts=attempts,
                    final_exception=None
                )
                
            except Exception as e:
                final_exception = e
                error_message = str(e)
                
                # Check if exception is retryable
                is_retryable = self.is_retryable_exception(e, config)
                
                # Calculate delay for next attempt
                delay = 0.0
                if attempt_num < config.max_attempts and is_retryable:
                    delay = self.calculate_delay(attempt_num + 1, config)
                
                # Record attempt
                attempt = RetryAttempt(
                    attempt_number=attempt_num,
                    timestamp=datetime.now(),
                    delay_seconds=delay,
                    exception=e,
                    error_message=error_message,
                    success=False
                )
                attempts.append(attempt)
                
                # Log attempt
                if is_retryable and attempt_num < config.max_attempts:
                    self.logger.warning(f"Attempt {attempt_num}/{config.max_attempts} failed: {error_message}. Retrying in {delay:.2f}s")
                    
                    # Wait before retry
                    if delay > 0:
                        await asyncio.sleep(delay)
                else:
                    if not is_retryable:
                        self.logger.error(f"Non-retryable error on attempt {attempt_num}: {error_message}")
                    else:
                        self.logger.error(f"All {config.max_attempts} attempts failed. Final error: {error_message}")
                    break
        
        # All attempts failed
        total_duration = time.time() - start_time
        
        return RetryResult(
            success=False,
            final_result=None,
            total_attempts=len(attempts),
            total_duration=total_duration,
            attempts=attempts,
            final_exception=final_exception
        )
    
    def retry_sync(self,
                   func: Callable,
                   config: Optional[RetryConfig] = None,
                   operation_type: str = "default",
                   *args, **kwargs) -> RetryResult:
        """
        Retry sync function with exponential backoff
        
        Args:
            func: Sync function to retry
            config: Retry configuration (optional)
            operation_type: Type of operation for default config
            *args, **kwargs: Arguments for function
            
        Returns:
            RetryResult with operation results
        """
        if config is None:
            config = self.default_configs.get(operation_type, RetryConfig())
        
        attempts = []
        start_time = time.time()
        final_exception = None
        
        for attempt_num in range(1, config.max_attempts + 1):
            try:
                # Call the function
                result = func(*args, **kwargs)
                
                # Success
                attempt = RetryAttempt(
                    attempt_number=attempt_num,
                    timestamp=datetime.now(),
                    delay_seconds=0.0,
                    exception=None,
                    error_message="",
                    success=True
                )
                attempts.append(attempt)
                
                total_duration = time.time() - start_time
                
                self.logger.info(f"Operation succeeded on attempt {attempt_num}/{config.max_attempts}")
                
                return RetryResult(
                    success=True,
                    final_result=result,
                    total_attempts=attempt_num,
                    total_duration=total_duration,
                    attempts=attempts,
                    final_exception=None
                )
                
            except Exception as e:
                final_exception = e
                error_message = str(e)
                
                # Check if exception is retryable
                is_retryable = self.is_retryable_exception(e, config)
                
                # Calculate delay for next attempt
                delay = 0.0
                if attempt_num < config.max_attempts and is_retryable:
                    delay = self.calculate_delay(attempt_num + 1, config)
                
                # Record attempt
                attempt = RetryAttempt(
                    attempt_number=attempt_num,
                    timestamp=datetime.now(),
                    delay_seconds=delay,
                    exception=e,
                    error_message=error_message,
                    success=False
                )
                attempts.append(attempt)
                
                # Log attempt
                if is_retryable and attempt_num < config.max_attempts:
                    self.logger.warning(f"Attempt {attempt_num}/{config.max_attempts} failed: {error_message}. Retrying in {delay:.2f}s")
                    
                    # Wait before retry
                    if delay > 0:
                        time.sleep(delay)
                else:
                    if not is_retryable:
                        self.logger.error(f"Non-retryable error on attempt {attempt_num}: {error_message}")
                    else:
                        self.logger.error(f"All {config.max_attempts} attempts failed. Final error: {error_message}")
                    break
        
        # All attempts failed
        total_duration = time.time() - start_time
        
        return RetryResult(
            success=False,
            final_result=None,
            total_attempts=len(attempts),
            total_duration=total_duration,
            attempts=attempts,
            final_exception=final_exception
        )


# Global retry manager instance
_retry_manager: Optional[RetryManager] = None


def get_retry_manager() -> RetryManager:
    """Get global retry manager instance"""
    global _retry_manager
    if _retry_manager is None:
        _retry_manager = RetryManager()
    return _retry_manager


def with_retry(config: Optional[RetryConfig] = None, 
              operation_type: str = "default"):
    """
    Decorator for automatic retry functionality
    
    Args:
        config: Retry configuration
        operation_type: Type of operation for default config
    """
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                retry_manager = get_retry_manager()
                result = await retry_manager.retry_async(
                    func, config, operation_type, *args, **kwargs
                )
                
                if result.success:
                    return result.final_result
                else:
                    raise result.final_exception
            
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                retry_manager = get_retry_manager()
                result = retry_manager.retry_sync(
                    func, config, operation_type, *args, **kwargs
                )
                
                if result.success:
                    return result.final_result
                else:
                    raise result.final_exception
            
            return sync_wrapper
    
    return decorator


# Convenient decorators for common operations
def with_http_retry(max_attempts: int = 3, base_delay: float = 1.0):
    """Decorator for HTTP operations with retry"""
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=30.0
    )
    return with_retry(config, "http_request")


def with_db_retry(max_attempts: int = 5, base_delay: float = 0.5):
    """Decorator for database operations with retry"""
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=10.0,
        backoff_multiplier=1.5
    )
    return with_retry(config, "database_operation")


def with_gwen3_retry(max_attempts: int = 3, base_delay: float = 2.0):
    """Decorator for GWEN-3 operations with retry"""
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=60.0
    )
    return with_retry(config, "gwen3_analysis")


class CircuitBreaker:
    """
    Circuit breaker pattern implementation
    Prevents cascading failures by temporarily stopping calls to failing services
    """
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: float = 60.0,
                 expected_exception: Type[Exception] = Exception):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
            expected_exception: Exception type that triggers circuit breaker
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
        self.logger = logging.getLogger(f"{__name__}.CircuitBreaker")
    
    def __call__(self, func):
        """Decorator implementation"""
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self._call_async(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self._call_sync(func, *args, **kwargs)
            return sync_wrapper
    
    async def _call_async(self, func, *args, **kwargs):
        """Async call with circuit breaker"""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                self.logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _call_sync(self, func, *args, **kwargs):
        """Sync call with circuit breaker"""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                self.logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        if self.last_failure_time is None:
            return True
        
        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state"""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "recovery_timeout": self.recovery_timeout
        }