#!/usr/bin/env python3
"""
Custom exceptions for Clutch.co scraper
Provides specific error types for better error handling
"""


class ClutchScraperError(Exception):
    """Base exception for all scraper errors"""
    pass


class NetworkError(ClutchScraperError):
    """Network-related errors (timeouts, connection issues)"""
    def __init__(self, message: str, status_code: int = None, url: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.url = url


class ParsingError(ClutchScraperError):
    """Errors in parsing HTML content"""
    def __init__(self, message: str, element: str = None, url: str = None):
        super().__init__(message)
        self.element = element
        self.url = url


class RateLimitError(ClutchScraperError):
    """Rate limiting or bot detection errors"""
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after


class ConfigurationError(ClutchScraperError):
    """Configuration-related errors"""
    pass


class DataValidationError(ClutchScraperError):
    """Data validation errors"""
    def __init__(self, message: str, field: str = None, value: str = None):
        super().__init__(message)
        self.field = field
        self.value = value


class ExportError(ClutchScraperError):
    """Errors during data export"""
    def __init__(self, message: str, format_type: str = None, filename: str = None):
        super().__init__(message)
        self.format_type = format_type
        self.filename = filename


class ScrapingLimitError(ClutchScraperError):
    """Errors related to scraping limits being reached"""
    def __init__(self, message: str, limit_type: str = None, current_count: int = None):
        super().__init__(message)
        self.limit_type = limit_type
        self.current_count = current_count


# Error context manager for better error tracking
class ErrorContext:
    """Context manager for tracking errors during scraping operations"""

    def __init__(self, operation: str, url: str = None):
        self.operation = operation
        self.url = url
        self.errors = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            error_info = {
                'operation': self.operation,
                'url': self.url,
                'exception_type': exc_type.__name__,
                'message': str(exc_val)
            }
            self.errors.append(error_info)

        # Don't suppress the exception
        return False

    def add_error(self, error: Exception, context: str = None):
        """Manually add an error to the context"""
        error_info = {
            'operation': self.operation,
            'url': self.url,
            'context': context,
            'exception_type': type(error).__name__,
            'message': str(error)
        }
        self.errors.append(error_info)


# Error recovery strategies
class ErrorRecoveryStrategy:
    """Base class for error recovery strategies"""

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if operation should be retried"""
        return False

    def get_retry_delay(self, attempt: int) -> float:
        """Get delay before retry"""
        return 0.0

    def can_recover(self, error: Exception) -> bool:
        """Determine if error is recoverable"""
        return False


class NetworkErrorRecovery(ErrorRecoveryStrategy):
    """Recovery strategy for network errors"""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay

    def should_retry(self, error: Exception, attempt: int) -> bool:
        if attempt >= self.max_retries:
            return False

        if isinstance(error, NetworkError):
            # Retry on certain status codes
            if error.status_code in [429, 500, 502, 503, 504]:
                return True
            # Don't retry on client errors
            if error.status_code and 400 <= error.status_code < 500:
                return False

        return isinstance(error, (NetworkError, ConnectionError, TimeoutError))

    def get_retry_delay(self, attempt: int) -> float:
        # Exponential backoff
        return self.base_delay * (2 ** attempt)

    def can_recover(self, error: Exception) -> bool:
        return isinstance(error, (NetworkError, ConnectionError, TimeoutError))


class ParsingErrorRecovery(ErrorRecoveryStrategy):
    """Recovery strategy for parsing errors"""

    def should_retry(self, error: Exception, attempt: int) -> bool:
        # Generally don't retry parsing errors
        return False

    def can_recover(self, error: Exception) -> bool:
        # Parsing errors usually indicate structural changes
        return False


class RateLimitRecovery(ErrorRecoveryStrategy):
    """Recovery strategy for rate limiting errors"""

    def should_retry(self, error: Exception, attempt: int) -> bool:
        return isinstance(error, RateLimitError) and attempt < 3

    def get_retry_delay(self, attempt: int) -> float:
        if isinstance(error, RateLimitError) and error.retry_after:
            return error.retry_after
        return 30.0 * (attempt + 1)  # Longer delay for rate limits

    def can_recover(self, error: Exception) -> bool:
        return isinstance(error, RateLimitError)


# Error handler that combines different recovery strategies
class ErrorHandler:
    """Centralized error handling with recovery strategies"""

    def __init__(self):
        self.strategies = [
            NetworkErrorRecovery(),
            ParsingErrorRecovery(),
            RateLimitRecovery()
        ]
        self.error_counts = {}

    def handle_error(self, error: Exception, context: str = None) -> dict:
        """
        Handle an error and return recovery information

        Returns:
            dict with keys: can_retry, should_retry, delay, strategy
        """
        error_type = type(error).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

        recovery_info = {
            'can_retry': False,
            'should_retry': False,
            'delay': 0.0,
            'strategy': None,
            'attempt': self.error_counts[error_type]
        }

        # Find appropriate strategy
        for strategy in self.strategies:
            if strategy.can_recover(error):
                recovery_info['can_retry'] = True
                recovery_info['should_retry'] = strategy.should_retry(error, recovery_info['attempt'])
                recovery_info['delay'] = strategy.get_retry_delay(recovery_info['attempt'])
                recovery_info['strategy'] = strategy.__class__.__name__
                break

        return recovery_info

    def reset_error_count(self, error_type: str = None):
        """Reset error count for specific type or all types"""
        if error_type:
            self.error_counts.pop(error_type, None)
        else:
            self.error_counts.clear()

    def get_error_summary(self) -> dict:
        """Get summary of all errors encountered"""
        return dict(self.error_counts)


if __name__ == "__main__":
    # Test error handling
    print("Testing error handling...")

    handler = ErrorHandler()

    # Test different error types
    test_errors = [
        NetworkError("Connection timeout", status_code=504, url="https://example.com"),
        ParsingError("Cannot find element", element="div.company", url="https://example.com"),
        RateLimitError("Rate limit exceeded", retry_after=60),
        ConfigurationError("Invalid configuration"),
    ]

    for error in test_errors:
        print(f"\nTesting {type(error).__name__}: {error}")
        recovery = handler.handle_error(error)
        print(f"  Recovery info: {recovery}")

    print(f"\nError summary: {handler.get_error_summary()}")

    # Test error context
    print("\nTesting error context...")
    with ErrorContext("test_operation", "https://example.com") as ctx:
        try:
            raise NetworkError("Test network error")
        except Exception as e:
            ctx.add_error(e, "test context")

    print(f"Context errors: {ctx.errors}")