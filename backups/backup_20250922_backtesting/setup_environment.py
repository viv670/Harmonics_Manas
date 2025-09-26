"""
Environment setup to prevent Unicode issues
Run this at the beginning of any script that might have Unicode problems
"""

import sys
import os
import io

def setup_safe_encoding():
    """
    Set up safe encoding for Windows terminals
    This prevents Unicode errors when printing
    """

    # For Windows, force UTF-8 mode if possible
    if sys.platform == 'win32':
        # Try to set UTF-8 mode
        try:
            # Set console code page to UTF-8
            import subprocess
            subprocess.run(['chcp', '65001'], shell=True, capture_output=True)
        except:
            pass

        # Reconfigure stdout to handle encoding errors
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')
            except:
                # Fallback for older Python versions
                sys.stdout = io.TextIOWrapper(
                    sys.stdout.buffer,
                    encoding='utf-8',
                    errors='replace',
                    line_buffering=True
                )
                sys.stderr = io.TextIOWrapper(
                    sys.stderr.buffer,
                    encoding='utf-8',
                    errors='replace',
                    line_buffering=True
                )

    # Set environment variable for Python
    os.environ['PYTHONIOENCODING'] = 'utf-8'

    return True

# Automatically setup when imported
setup_safe_encoding()

def safe_print(*args, **kwargs):
    """
    Safe print function that handles encoding errors
    """
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Convert to ASCII if Unicode fails
        new_args = []
        for arg in args:
            if isinstance(arg, str):
                # Replace non-ASCII characters
                cleaned = ''.join(
                    char if ord(char) < 128 else '?'
                    for char in str(arg)
                )
                new_args.append(cleaned)
            else:
                new_args.append(arg)
        print(*new_args, **kwargs)

# Usage example:
if __name__ == "__main__":
    print("Environment setup complete!")
    print("Testing Unicode: checkmark -> [OK], cross -> [X], arrow -> ->")
    safe_print("Safe print test: Any Unicode will be handled gracefully")