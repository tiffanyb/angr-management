from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Warning:
    """Represents a warning extracted from Docker console output."""

    address: int  # Instruction address (stored as integer)
    message: str  # Warning message

    @classmethod
    def from_hex_string(cls, address_str: str, message: str) -> Warning:
        """Create Warning from hex address string.

        Args:
            address_str: Address as hex string (e.g., '0x8005C3E')
            message: Warning message text

        Returns:
            Warning instance with parsed address
        """
        addr = int(address_str, 16) if isinstance(address_str, str) else address_str
        return cls(address=addr, message=message)

    def matches_address(self, addr: int) -> bool:
        """Check if this warning matches the given address.

        Checks both exact address and address+1, since warning address
        might be 1 byte off from instruction address.

        Args:
            addr: Address to check

        Returns:
            True if address matches (exact or +1)
        """
        return addr == self.address or addr == self.address + 1

    def to_hex(self) -> str:
        """Return address as hex string."""
        return hex(self.address)
