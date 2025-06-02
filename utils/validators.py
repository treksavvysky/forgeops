"""
Input Validators - Handles user input validation and interaction
"""

import sys


class InputValidator:
    def get_user_input(self, prompt, required=True, validator=None):
        """Get user input with validation and Ctrl+C handling."""
        while True:
            try:
                user_input = input(prompt).strip()
                
                # Check if required field is empty
                if required and not user_input:
                    print("This field is required. Please enter a value.")
                    continue
                
                # Run custom validator if provided
                if validator and user_input:
                    is_valid, error_msg = validator(user_input)
                    if not is_valid:
                        print(f"Invalid input: {error_msg}")
                        continue
                
                return user_input
                
            except KeyboardInterrupt:
                print("\n\nOperation cancelled by user.")
                sys.exit(0)
