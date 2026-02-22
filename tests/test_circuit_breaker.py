"""
Tests for circuit breaker functionality.
"""

import pytest

from app.services.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitState


@pytest.mark.asyncio
async def test_circuit_breaker_closed_state():
    """Test circuit breaker in closed state"""
    breaker = CircuitBreaker(name="test", failure_threshold=3)
    
    async def success_func():
        return "success"
    
    result = await breaker.call(success_func)
    assert result == "success"
    assert breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures():
    """Test circuit breaker opens after threshold failures"""
    breaker = CircuitBreaker(name="test", failure_threshold=3)
    
    async def failing_func():
        raise Exception("Test error")
    
    # Fail 3 times to open circuit
    for _ in range(3):
        with pytest.raises(Exception):
            await breaker.call(failing_func)
    
    assert breaker.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_blocks_when_open():
    """Test circuit breaker blocks requests when open"""
    breaker = CircuitBreaker(name="test", failure_threshold=2)
    
    async def failing_func():
        raise Exception("Test error")
    
    # Open the circuit
    for _ in range(2):
        with pytest.raises(Exception):
            await breaker.call(failing_func)
    
    # Should raise CircuitBreakerOpenError
    with pytest.raises(CircuitBreakerOpenError):
        await breaker.call(failing_func)


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_recovery():
    """Test circuit breaker recovery through half-open state"""
    breaker = CircuitBreaker(
        name="test",
        failure_threshold=2,
        timeout=0,  # Immediate transition to half-open
        success_threshold=2,
    )
    
    async def failing_func():
        raise Exception("Test error")
    
    async def success_func():
        return "success"
    
    # Open the circuit
    for _ in range(2):
        with pytest.raises(Exception):
            await breaker.call(failing_func)
    
    assert breaker.state == CircuitState.OPEN
    
    # Force transition to half-open
    breaker._last_failure_time = None
    
    # Two successful calls should close the circuit
    await breaker.call(success_func)
    await breaker.call(success_func)
    
    assert breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_reset():
    """Test manual circuit breaker reset"""
    breaker = CircuitBreaker(name="test", failure_threshold=2)
    
    async def failing_func():
        raise Exception("Test error")
    
    # Open the circuit
    for _ in range(2):
        with pytest.raises(Exception):
            await breaker.call(failing_func)
    
    assert breaker.state == CircuitState.OPEN
    
    # Manual reset
    breaker.reset()
    
    assert breaker.state == CircuitState.CLOSED
    assert breaker._failure_count == 0


def test_circuit_breaker_stats():
    """Test circuit breaker statistics"""
    breaker = CircuitBreaker(name="test", failure_threshold=3)
    
    stats = breaker.get_stats()
    
    assert stats["name"] == "test"
    assert stats["state"] == CircuitState.CLOSED.value
    assert stats["failure_count"] == 0
    assert stats["success_count"] == 0
