def fibonacci_sequence(n):
    """
    Generate the first n Fibonacci numbers.
    
    The Fibonacci sequence starts with 0 and 1, where each subsequent number
    is the sum of the two preceding ones: 0, 1, 1, 2, 3, 5, 8, 13, 21, ...
    
    Args:
        n (int): Number of Fibonacci numbers to generate. Must be non-negative.
        
    Returns:
        list: List containing the first n Fibonacci numbers.
        
    Raises:
        ValueError: If n is negative.
        TypeError: If n is not an integer.
        
    Examples:
        >>> fibonacci_sequence(5)
        [0, 1, 1, 2, 3]
        
        >>> fibonacci_sequence(0)
        []
        
        >>> fibonacci_sequence(1)
        [0]
    """
    if not isinstance(n, int):
        raise TypeError(f"Expected integer, got {type(n).__name__}")
    
    if n < 0:
        raise ValueError("Number of Fibonacci numbers must be non-negative")
    
    if n == 0:
        return []
    
    if n == 1:
        return [0]
    
    fibonacci_sequence = [0, 1]
    
    for i in range(2, n):
        next_fib = fibonacci_sequence[i-1] + fibonacci_sequence[i-2]
        fibonacci_sequence.append(next_fib)
    
    return fibonacci_sequence


def fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n - 1) + fibonacci(n - 2)


if __name__ == "__main__":
    try:
        result = fibonacci_sequence(10)
        print(f"First 10 Fibonacci numbers: {result}")
    except (ValueError, TypeError) as e:
        print(f"Error: {e}")
    
    # Test the fibonacci function
    fib_result = fibonacci(10)
    print(f"fibonacci(10) = {fib_result}")