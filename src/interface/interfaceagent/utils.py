import json
import re
from typing import Any, Optional

from loguru import logger


def extract_code_snippet(code_string):
    # Extract code snippet using regex
    cleaned_snippet = re.search(r'```(?:\w+)?\s*([\s\S]*?)\s*```', code_string)

    if cleaned_snippet:
        cleaned_snippet = cleaned_snippet.group(1)
    else:
        cleaned_snippet = code_string

    # remove non-printable characters
    # cleaned_snippet = re.sub(r'[\x00-\x1F]+', ' ', cleaned_snippet)

    return cleaned_snippet


def parse_json(response: str) -> Optional[Any]:
    """
    Parse a JSON string into a Python object.

    Args:
        response (str): The JSON string to parse.

    Returns:
        Optional[Any]: The parsed Python object, or None if parsing fails.
    """
    try:
        return json.loads(extract_code_snippet(response))
    except json.JSONDecodeError:
        logger.error(f"Error parsing JSON: {response}")
        return None
