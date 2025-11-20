from __future__ import annotations

from typing import TYPE_CHECKING

from angrmanagement.plugins import BasePlugin

from .swab_view import QWarningAnnotation, SWABView

if TYPE_CHECKING:
    from angrmanagement.ui.workspace import Workspace


class SWABPlugin(BasePlugin):
    """
    SWAB Plugin - provides a split-panel view with non-editable text and editable code.
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
        """
        Add warning annotations to the disassembly view.

        For each warning address, check both the exact address and address+1
        (since the warning address might be 1 byte off).
        """
        if not self.swab_view or not self.swab_view.warnings:
            return []

        qinsns = qblock.addr_to_insns.values()
        items = []

        for qinsn in qinsns:
            insn_addr = qinsn.addr

            # Check if this instruction matches any warning address
            for warning in self.swab_view.warnings:
                try:
                    # Parse the warning address (might be hex string like '0x8005C3E')
                    warning_addr = int(warning['address'], 16) if isinstance(warning['address'], str) else warning['address']

                    # Check if instruction address matches warning address or warning address + 1
                    if insn_addr == warning_addr or insn_addr == warning_addr + 1:
                        items.append(QWarningAnnotation(insn_addr, warning['message']))
                        break  # Only add one annotation per instruction

                except (ValueError, KeyError):
                    # Skip invalid warning entries
                    continue

        return items

    def teardown(self) -> None:
        """Clean up the plugin."""
        super().teardown()
