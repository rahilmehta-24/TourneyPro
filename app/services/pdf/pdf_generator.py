"""Draw PDF Rendering Service for TourneyPro.

Renders static HTML/Jinja2 bracket templates into validated, high-quality
PDF documents using xhtml2pdf in memory.
"""

import io
import logging
from typing import Dict, Optional
from flask import render_template
from xhtml2pdf import pisa
from pypdf import PdfReader

logger = logging.getLogger(__name__)


class DrawPdfService:
    """PDF generation service for single elimination tournament brackets and reports."""

    _cache: Dict[str, bytes] = {}
    _cache_limit: int = 100

    @classmethod
    def get_cached_pdf(cls, cache_key: Optional[str]) -> Optional[bytes]:
        """Retrieve pre-compiled PDF bytes from memory cache if available."""
        if cache_key and cache_key in cls._cache:
            return cls._cache[cache_key]
        return None

    @classmethod
    def set_cached_pdf(cls, cache_key: Optional[str], pdf_bytes: bytes) -> None:
        """Store compiled PDF bytes into bounded memory cache."""
        if not cache_key:
            return
        if len(cls._cache) >= cls._cache_limit:
            oldest_key = next(iter(cls._cache))
            cls._cache.pop(oldest_key, None)
        cls._cache[cache_key] = pdf_bytes

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached PDF binaries."""
        cls._cache.clear()

    @classmethod
    def render_draw_pdf(cls, draw_data: dict, cache_key: Optional[str] = None) -> io.BytesIO:
        """
        Populate the static Jinja2 bracket template with draw data and compile to PDF.

        Args:
            draw_data: Normalized dictionary produced by DrawExportAdapter.
            cache_key: Optional unique fingerprint string to look up / store precompiled PDF.

        Returns:
            io.BytesIO: In-memory binary buffer containing the valid PDF file.

        Raises:
            RuntimeError: If template rendering or PDF compilation fails.
        """
        if cache_key:
            cached_bytes = cls.get_cached_pdf(cache_key)
            if cached_bytes:
                return io.BytesIO(cached_bytes)
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

        if cache_key:
            cls.set_cached_pdf(cache_key, pdf_buffer.getvalue())

        pdf_buffer.seek(0)
        return pdf_buffer

    @classmethod
    def render_order_of_play_pdf(
        cls, oop_data: dict, cache_key: Optional[str] = None
    ) -> io.BytesIO:
        """
        Populate the static Jinja2 Order of Play template with schedule data and compile to PDF.

        Args:
            oop_data: Normalized dictionary produced by OrderOfPlayExportAdapter.
            cache_key: Optional unique fingerprint string to look up / store precompiled PDF.

        Returns:
            io.BytesIO: In-memory binary buffer containing the valid PDF file.

        Raises:
            RuntimeError: If template rendering or PDF compilation fails.
        """
        if cache_key:
            cached_bytes = cls.get_cached_pdf(cache_key)
            if cached_bytes:
                return io.BytesIO(cached_bytes)

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

        if cache_key:
            cls.set_cached_pdf(cache_key, pdf_buffer.getvalue())

        pdf_buffer.seek(0)
        return pdf_buffer

    @classmethod
    def render_participants_pdf(
        cls, participants_data: dict, cache_key: Optional[str] = None
    ) -> io.BytesIO:
        """
        Populate the static Jinja2 participants template with tournament roster data
        and compile to PDF.

        Args:
            participants_data: Normalized dictionary produced by ParticipantsExportAdapter.
            cache_key: Optional unique fingerprint string to look up / store precompiled PDF.

        Returns:
            io.BytesIO: In-memory binary buffer containing the valid PDF file.

        Raises:
            RuntimeError: If template rendering or PDF compilation fails.
        """
        if cache_key:
            cached_bytes = cls.get_cached_pdf(cache_key)
            if cached_bytes:
                return io.BytesIO(cached_bytes)

        try:
            rendered_html = render_template(
                "export/participants_pdf.html", participants_data=participants_data
            )
        except Exception as e:
            logger.error(f"Template rendering failed for participants PDF: {e}", exc_info=True)
            raise RuntimeError(f"Failed to render participants template: {e}") from e

        pdf_buffer = io.BytesIO()
        try:
            pisa_status = pisa.CreatePDF(src=rendered_html, dest=pdf_buffer, encoding="utf-8")
        except Exception as e:
            logger.error(
                f"xhtml2pdf compiler exception during participants PDF export: {e}", exc_info=True
            )
            raise RuntimeError(f"xhtml2pdf compilation failure: {e}") from e

        if pisa_status.err:
            logger.error(
                f"xhtml2pdf returned error code {pisa_status.err} during participants export"
            )
            raise RuntimeError(f"PDF rendering engine returned error status: {pisa_status.err}")

        # Validate generated PDF integrity
        pdf_buffer.seek(0)
        try:
            reader = PdfReader(pdf_buffer)
            if len(reader.pages) == 0:
                raise RuntimeError("Generated participants PDF document contains no pages.")
            _ = reader.pages[0].mediabox
        except Exception as e:
            logger.error(
                f"pypdf integrity check failed on generated participants PDF: {e}", exc_info=True
            )
            raise RuntimeError(
                f"Generated participants PDF failed integrity verification: {e}"
            ) from e

        if cache_key:
            cls.set_cached_pdf(cache_key, pdf_buffer.getvalue())

        pdf_buffer.seek(0)
        return pdf_buffer
