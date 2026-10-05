from io import BytesIO
import logging

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from xhtml2pdf import pisa

logger = logging.getLogger(__name__)


def generate_certificate_pdf(certificate) -> bytes:
    context = {
        'certificate': certificate,
        'user': certificate.user,
        'course': certificate.course,
        'site_name': settings.SITE_NAME,
        'support_email': settings.DEFAULT_FROM_EMAIL,
    }
    html_string = render_to_string('courses/certificate_pdf.html', context)
    result_buffer = BytesIO()
    pdf = pisa.pisaDocument(
        BytesIO(html_string.encode('utf-8')),
        result_buffer,
        encoding='utf-8'
    )
    if pdf.err:
        logger.error(
            f"xhtml2pdf error generating certificate PDF "
            f"{certificate.certificate_id}: {pdf.err}"
        )
        return None

    pdf_bytes = result_buffer.getvalue()

    if not certificate.pdf_file:
        try:
            certificate.pdf_file.save(
                f"certificate_{certificate.certificate_id}.pdf",
                ContentFile(pdf_bytes),
                save=True
            )
        except Exception as e:
            logger.warning(
                f"Could not persist certificate PDF file for "
                f"{certificate.id}: {e}"
            )

    return pdf_bytes
