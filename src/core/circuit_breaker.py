from tenacity import RetryCallState, retry, retry_if_exception_type, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self, max_attempts=3, timeout=60):
        self.max_attempts = max_attempts
        self.timeout = timeout
        self._state = "closed"
        
    def __call__(self, retry_state: RetryCallState):
        if retry_state.attempt_number >= self.max_attempts:
            self._state = "open"
            logger.error("Circuit breaker tripped! Stopping retries.")
            return False
        return True

# Usage in LLM Client
class LLMClient:
    @retry(
        stop=CircuitBreaker(max_attempts=3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((APIError, TimeoutError))
    )
    def generate_content(self, prompt):
        # API call implementation