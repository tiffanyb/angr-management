from __future__ import annotations

import re

from ..models import Warning


class WarningParser:
    """Parse warnings from Docker console output."""

    # Pattern to extract address from brackets: [cpu1: 0x8005C3E]
    ADDRESS_PATTERN = re.compile(r'\[([^:]+):\s*([^\]]+)\]')

    # Pattern to extract message from last colon onward
    MESSAGE_PATTERN = re.compile(r':\s*([^:]+)$')

    @staticmethod
    def parse(console_output: str) -> list[Warning]:
        """Extract warning messages from Docker console output.

        Parses multi-line warning messages and extracts:
        - CPU address from the first line (second element in brackets)
        - Warning message from the second line

        Example input:
            WARNING:swab.engine: Engine renode: renode:rcc: [cpu1: 0x8005C3E] writing value 0x0 to offset 0x1C
            WARNING:swab.engine: Engine renode: renode:rcc: Unhandled write to offset 0x1C, value 0x0.

        Args:
            console_output: Full console output text

        Returns:
            List of Warning objects with address and message.
        """
        warnings = []
        lines = console_output.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check if this is a WARNING line with an address
            if line.startswith('WARNING:') and '[' in line and ']' in line:
                # Extract the address (second element in brackets)
                bracket_match = WarningParser.ADDRESS_PATTERN.search(line)

                if bracket_match:
                    address = bracket_match.group(2).strip()  # Get the second element (the address)

                    # Look for the next line which should contain the warning message
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()

                        # Check if next line is also a WARNING line
                        if next_line.startswith('WARNING:'):
                            # Extract the message after the last colon
                            message_match = WarningParser.MESSAGE_PATTERN.search(next_line)
                            if message_match:
                                message = message_match.group(1).strip()

                                try:
                                    warnings.append(Warning.from_hex_string(address, message))
                                except (ValueError, TypeError):
                                    # Skip invalid addresses
                                    pass

                                # Skip the next line since we've already processed it
                                i += 1

            i += 1

        return warnings
