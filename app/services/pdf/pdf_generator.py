"""Draw PDF Rendering Service for TourneyPro.

Renders static HTML/Jinja2 bracket templates into validated, high-quality
PDF documents using xhtml2pdf in memory.
"""

import io
import logging
from flask import render_template
from xhtml2pdf import pisa
from pypdf import PdfReader

logger = logging.getLogger(__name__)


class DrawPdfService:
    """PDF generation service for single elimination tournament brackets."""

    @staticmethod
    def render_draw_pdf(draw_data: dict) -> io.BytesIO:
        """
        Populate the static Jinja2 bracket template with draw data and compile to PDF.

        Args:
            draw_data: Normalized dictionary produced by DrawExportAdapter.

        Returns:
            io.BytesIO: In-memory binary buffer containing the valid PDF file.

        Raises:
            RuntimeError: If template rendering or PDF compilation fails.
        """
        try:
            rendered_html = render_template("export/draw_pdf.html", draw_data=draw_data)
        except Exception as e:
            logger.error(f"Template rendering failed for draw PDF: {e}", exc_info=True)
            raise RuntimeError(f"Failed to render draw bracket template: {e}") from e

        pdf_buffer = io.BytesIO()
        try:
            pisa_status = pisa.CreatePDF(src=rendered_html, dest=pdf_buffer, encoding="utf-8")
        except Exception as e:
            logger.error(f"xhtml2pdf compiler exception during draw PDF export: {e}", exc_info=True)
            raise RuntimeError(f"xhtml2pdf compilation failure: {e}") from e

        if pisa_status.err:
            logger.error(f"xhtml2pdf returned error code {pisa_status.err} during draw export")
            raise RuntimeError(f"PDF rendering engine returned error status: {pisa_status.err}")

        # Validate generated PDF integrity
        pdf_buffer.seek(0)
        try:
            reader = PdfReader(pdf_buffer)
            if len(reader.pages) == 0:
                raise RuntimeError("Generated PDF document contains no pages.")
            # Verify first page can be accessed
            _ = reader.pages[0].mediabox
        except Exception as e:
            logger.error(f"pypdf integrity check failed on generated draw PDF: {e}", exc_info=True)
            raise RuntimeError(f"Generated draw PDF failed integrity verification: {e}") from e

        pdf_buffer.seek(0)
        return pdf_buffer

    @staticmethod
    def render_order_of_play_pdf(oop_data: dict) -> io.BytesIO:
        """
        Populate the static Jinja2 Order of Play template with schedule data and compile to PDF.

        Args:
            oop_data: Normalized dictionary produced by OrderOfPlayExportAdapter.

        Returns:
            io.BytesIO: In-memory binary buffer containing the valid PDF file.

        Raises:
            RuntimeError: If template rendering or PDF compilation fails.
        """
        try:
            rendered_html = render_template("export/order_of_play_pdf.html", oop_data=oop_data)
        except Exception as e:
            logger.error(f"Template rendering failed for Order of Play PDF: {e}", exc_info=True)
            raise RuntimeError(f"Failed to render Order of Play template: {e}") from e

        pdf_buffer = io.BytesIO()
        try:
            pisa_status = pisa.CreatePDF(src=rendered_html, dest=pdf_buffer, encoding="utf-8")
        except Exception as e:
            logger.error(
                f"xhtml2pdf compiler exception during Order of Play PDF export: {e}", exc_info=True
            )
            raise RuntimeError(f"xhtml2pdf compilation failure: {e}") from e

        if pisa_status.err:
            logger.error(
                f"xhtml2pdf returned error code {pisa_status.err} during Order of Play export"
            )
            raise RuntimeError(f"PDF rendering engine returned error status: {pisa_status.err}")

        # Validate generated PDF integrity
        pdf_buffer.seek(0)
        try:
            reader = PdfReader(pdf_buffer)
            if len(reader.pages) == 0:
                raise RuntimeError("Generated Order of Play PDF document contains no pages.")
            _ = reader.pages[0].mediabox
        except Exception as e:
            logger.error(
                f"pypdf integrity check failed on generated Order of Play PDF: {e}", exc_info=True
            )
            raise RuntimeError(
                f"Generated Order of Play PDF failed integrity verification: {e}"
            ) from e

        pdf_buffer.seek(0)
        return pdf_buffer
