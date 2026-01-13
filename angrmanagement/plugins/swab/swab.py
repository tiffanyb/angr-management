from __future__ import annotations

from typing import TYPE_CHECKING

from angrmanagement.plugins import BasePlugin

from .models import Warning
from .ui import QWarningAnnotation
from .ui.swab_view import SWABView

if TYPE_CHECKING:
    from angrmanagement.ui.workspace import Workspace


class SWABPlugin(BasePlugin):
    """SWAB Plugin - Docker-based simulation warning analyzer.

    Provides:
    - Docker container execution with project mounting
    - Warning extraction and visualization
    - Disassembly view annotations
    - Interactive console with warning navigation
    """

    DISPLAY_NAME = "SWAB"

    def __init__(self, workspace: Workspace) -> None:
        super().__init__(workspace)

        self.swab_view = None

        # Create and add the SWAB view to the workspace
        if workspace is not None:
            self._create_swab_view()

    def _create_swab_view(self) -> None:
        """Create and register the SWAB view."""
        self.swab_view = SWABView(
            self.workspace,
            "center",
            self.workspace.main_instance,
        )
        self.workspace.add_view(self.swab_view)
        self.workspace.raise_view(self.swab_view)

    def build_qblock_annotations(self, qblock):
        """Add warning annotations to the disassembly view.

        For each warning address, check if any instruction matches.
        Uses Warning.matches_address() which checks both exact address
        and address+1 (since warning address might be 1 byte off).

        The annotation uses the instruction's actual address (which may have
        the Thumb bit set in ARM Thumb mode) rather than the warning's address,
        ensuring proper positioning in the disassembly view.

        Args:
            qblock: QBlock to annotate

        Returns:
            List of QWarningAnnotation objects
        """
        if not self.swab_view or not self.swab_view.warnings:
            return []

        qinsns = qblock.addr_to_insns.values()
        items = []

        for qinsn in qinsns:
            insn_addr = qinsn.addr

            # Check if this instruction matches any warning
            for warning in self.swab_view.warnings:
                if warning.matches_address(insn_addr):
                    # Pass the instruction address to ensure proper positioning
                    # (handles ARM Thumb mode where insn_addr has bit 0 set)
                    items.append(QWarningAnnotation(warning, insn_addr))
                    break  # Only add one annotation per instruction

        return items

    def teardown(self) -> None:
        """Clean up the plugin."""
        super().teardown()
