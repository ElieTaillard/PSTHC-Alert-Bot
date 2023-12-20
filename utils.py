def limit_string_length(input_string: str, max_length: int) -> str:
    """
    Limit the length of a string.

    Parameters:
        input_string (str): The input string.
        max_length (int): The maximum length.

    Returns:
        str: The limited string.
    """
    if len(input_string) > max_length:
        input_string = input_string[: max_length - 3] + "..."
    return input_string
