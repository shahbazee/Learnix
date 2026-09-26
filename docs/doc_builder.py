"""
Learnix PDF Documentation Engine - Styling, Canvas, and Flowable Builders.
"""

import html
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# ==============================================================================
# NUMBERED CANVAS WITH TWO-PASS RUNNING HEADERS AND FOOTERS
# ==============================================================================

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            if self._pageNumber > 1:
                self.saveState()
                # Running Header
                self.setFont('Helvetica-Bold', 7.5)
                self.setFillColor(colors.HexColor('#4F46E5'))
                self.drawString(36, 762, 'LEARNIX E-LEARNING PLATFORM')
                self.setFont('Helvetica', 7.5)
                self.setFillColor(colors.HexColor('#64748B'))
                self.drawString(178, 762, '|   Comprehensive Backend Architecture & Viva Preparation Manual')

                self.setStrokeColor(colors.HexColor('#E2E8F0'))
                self.setLineWidth(0.75)
                self.line(36, 756, 576, 756)

                # Running Footer
                self.line(36, 42, 576, 42)
                self.setFont('Helvetica', 7.5)
                self.setFillColor(colors.HexColor('#64748B'))
                self.drawString(36, 30, 'Learnix Production Architecture  •  Django 5.0 + PostgreSQL 15+  •  Comprehensive Technical Documentation')
                page_str = f'Page {self._pageNumber} of {num_pages}'
                self.drawRightString(576, 30, page_str)
                self.restoreState()
            super().showPage()
        super().save()

# ==============================================================================
# STYLE DEFINITIONS
# ==============================================================================

styles = getSampleStyleSheet()

# Palette definitions
PRIMARY = colors.HexColor('#4F46E5')    # Indigo / Violet
PRIMARY_DARK = colors.HexColor('#3730A3')
ACCENT_CYAN = colors.HexColor('#0891B2') # Cyan 600
DARK_SLATE = colors.HexColor('#0F172A')  # Slate 900
TEXT_MAIN = colors.HexColor('#1E293B')   # Slate 800
TEXT_MUTED = colors.HexColor('#64748B')  # Slate 500
BORDER_LIGHT = colors.HexColor('#E2E8F0')# Slate 200
BG_CODE = colors.HexColor('#F8FAFC')     # Slate 50
BG_CALLOUT_INFO = colors.HexColor('#EEF2FF')
BG_CALLOUT_VIVA = colors.HexColor('#F0FDF4')
BG_CALLOUT_WARN = colors.HexColor('#FFFBEB')
BG_CALLOUT_SEC = colors.HexColor('#FEF2F2')

style_title = ParagraphStyle(
    'DocTitle',
    fontName='Helvetica-Bold',
    fontSize=26,
    leading=32,
    textColor=PRIMARY_DARK,
    alignment=1
)

style_subtitle = ParagraphStyle(
    'DocSubtitle',
    fontName='Helvetica',
    fontSize=13,
    leading=18,
    textColor=ACCENT_CYAN,
    alignment=1
)

style_meta = ParagraphStyle(
    'DocMeta',
    fontName='Helvetica',
    fontSize=8.5,
    leading=12,
    textColor=TEXT_MUTED,
    alignment=1
)

style_h1 = ParagraphStyle(
    'SectionH1',
    fontName='Helvetica-Bold',
    fontSize=16,
    leading=20,
    textColor=PRIMARY_DARK,
    spaceBefore=14,
    spaceAfter=6,
    keepWithNext=True
)

style_h2 = ParagraphStyle(
    'SectionH2',
    fontName='Helvetica-Bold',
    fontSize=12,
    leading=16,
    textColor=DARK_SLATE,
    spaceBefore=10,
    spaceAfter=4,
    keepWithNext=True
)

style_h3 = ParagraphStyle(
    'SectionH3',
    fontName='Helvetica-Bold',
    fontSize=9.5,
    leading=13,
    textColor=PRIMARY,
    spaceBefore=6,
    spaceAfter=3,
    keepWithNext=True
)

style_body = ParagraphStyle(
    'BodyTextCustom',
    fontName='Helvetica',
    fontSize=8.5,
    leading=12,
    textColor=TEXT_MAIN,
    spaceAfter=5
)

style_body_bold = ParagraphStyle(
    'BodyBoldCustom',
    fontName='Helvetica-Bold',
    fontSize=8.5,
    leading=12,
    textColor=TEXT_MAIN,
    spaceAfter=5
)

style_bullet = ParagraphStyle(
    'BulletCustom',
    fontName='Helvetica',
    fontSize=8.5,
    leading=12,
    textColor=TEXT_MAIN,
    leftIndent=12,
    firstLineIndent=-8,
    spaceAfter=3
)

style_code = ParagraphStyle(
    'CodeSnippetCustom',
    fontName='Courier',
    fontSize=7.2,
    leading=9.2,
    textColor=colors.HexColor('#0F172A')
)

style_callout_title = ParagraphStyle(
    'CalloutTitle',
    fontName='Helvetica-Bold',
    fontSize=8.5,
    leading=11
)

style_callout_body = ParagraphStyle(
    'CalloutBody',
    fontName='Helvetica',
    fontSize=8,
    leading=11,
    textColor=TEXT_MAIN
)

style_th = ParagraphStyle(
    'TableHeaderCustom',
    fontName='Helvetica-Bold',
    fontSize=7.5,
    leading=9.5,
    textColor=colors.white,
    alignment=0
)

style_td = ParagraphStyle(
    'TableCellCustom',
    fontName='Helvetica',
    fontSize=7.5,
    leading=9.5,
    textColor=TEXT_MAIN
)

style_td_bold = ParagraphStyle(
    'TableCellBoldCustom',
    fontName='Helvetica-Bold',
    fontSize=7.5,
    leading=9.5,
    textColor=DARK_SLATE
)

style_td_code = ParagraphStyle(
    'TableCellCodeCustom',
    fontName='Courier',
    fontSize=7,
    leading=9,
    textColor=PRIMARY_DARK
)

# ==============================================================================
# HELPER BUILDER FUNCTIONS
# ==============================================================================

def p(text, bold=False):
    st = style_body_bold if bold else style_body
    return Paragraph(text, st)

def bullet(text):
    return Paragraph(f"• &nbsp;{text}", style_bullet)

def h1(text):
    return Paragraph(text, style_h1)

def h2(text):
    return Paragraph(text, style_h2)

def h3(text):
    return Paragraph(text, style_h3)

def spacer(height=8):
    return Spacer(1, height)

def hr():
    return HRFlowable(width="100%", thickness=0.5, color=BORDER_LIGHT, spaceBefore=6, spaceAfter=8)

def code_box(code_text, caption=None):
    """
    Renders a clean syntax-styled code box with Courier font and subtle border.
    """
    # Clean lines and escape html
    lines = code_text.strip().split('\n')
    escaped_lines = []
    for line in lines:
        escaped_lines.append(html.escape(line).replace(' ', '&nbsp;'))
    code_html = "<br/>".join(escaped_lines)
    
    flowables = []
    if caption:
        caption_para = Paragraph(f"<b>Snippet:</b> {html.escape(caption)}", ParagraphStyle(
            'CodeCaption', fontName='Helvetica-Bold', fontSize=7.5, leading=10, textColor=PRIMARY
        ))
        flowables.append(caption_para)
        flowables.append(Spacer(1, 3))
    
    code_para = Paragraph(code_html, style_code)
    flowables.append(code_para)
    
    table = Table([[flowables]], colWidths=[540])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_CODE),
        ('BOX', (0,0), (-1,-1), 0.75, BORDER_LIGHT),
        ('LINELEFT', (0,0), (0,-1), 3.5, PRIMARY),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    return table

def callout(title, text, callout_type='info'):
    """
    Renders an eye-catching callout box for notes, tips, warnings, or security alerts.
    """
    if callout_type == 'viva':
        bg = BG_CALLOUT_VIVA
        border_col = colors.HexColor('#16A34A')
        text_col = colors.HexColor('#15803D')
        prefix = "★ VIVA EVALUATION INSIGHT"
    elif callout_type == 'warning':
        bg = BG_CALLOUT_WARN
        border_col = colors.HexColor('#D97706')
        text_col = colors.HexColor('#B45309')
        prefix = "⚠ IMPORTANT WARNING / CONSTRAINT"
    elif callout_type == 'security':
        bg = BG_CALLOUT_SEC
        border_col = colors.HexColor('#DC2626')
        text_col = colors.HexColor('#B91C1C')
        prefix = "🔒 SECURITY ARCHITECTURE NOTE"
    else: # info
        bg = BG_CALLOUT_INFO
        border_col = PRIMARY
        text_col = PRIMARY_DARK
        prefix = "ℹ SYSTEM ARCHITECTURE CONTEXT"

    full_title = f"{prefix}: {title}" if title else prefix
    t_para = Paragraph(f"<b>{html.escape(full_title)}</b>", ParagraphStyle(
        'CalloutT', fontName='Helvetica-Bold', fontSize=8, leading=10.5, textColor=text_col
    ))
    b_para = Paragraph(text, style_callout_body)

    table = Table([[t_para], [b_para]], colWidths=[540])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg),
        ('LINELEFT', (0,0), (0,-1), 3.5, border_col),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    return table

def viva_qa(q_num, topic, question, answer, code_ref=None):
    """
    Renders a structured viva question and answer pair for exam preparation.
    """
    header = Paragraph(f"<b>Q{q_num} [{topic}]:</b> {html.escape(question)}", ParagraphStyle(
        'VQ', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=DARK_SLATE
    ))
    ans_text = f"<b>Model Answer:</b> {answer}"
    if code_ref:
        ans_text += f"<br/><font color='#4F46E5'><b>Implemented at:</b> {html.escape(code_ref)}</font>"
    ans_para = Paragraph(ans_text, ParagraphStyle(
        'VA', fontName='Helvetica', fontSize=8, leading=11, textColor=TEXT_MAIN
    ))

    table = Table([[header], [ans_para]], colWidths=[540])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('LINELEFT', (0,0), (0,-1), 3.5, colors.HexColor('#0891B2')), # Cyan
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    return table

def create_table(data_rows, col_widths, has_header=True):
    """
    Builds a wrapped ReportLab Table from rows of strings or Paragraphs.
    """
    formatted_rows = []
    for r_idx, row in enumerate(data_rows):
        formatted_row = []
        for c_idx, cell in enumerate(row):
            if isinstance(cell, Paragraph):
                formatted_row.append(cell)
            else:
                cell_str = str(cell)
                if r_idx == 0 and has_header:
                    formatted_row.append(Paragraph(cell_str, style_th))
                elif c_idx == 0:
                    formatted_row.append(Paragraph(cell_str, style_td_bold))
                else:
                    formatted_row.append(Paragraph(cell_str, style_td))
        formatted_rows.append(formatted_row)

    table = Table(formatted_rows, colWidths=col_widths)
    t_style = [
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_LIGHT),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]
    if has_header:
        t_style.append(('BACKGROUND', (0,0), (-1,0), PRIMARY))
        t_style.append(('BOTTOMPADDING', (0,0), (-1,0), 4.5))
        # Alternating row colors
        for i in range(1, len(data_rows)):
            if i % 2 == 0:
                t_style.append(('BACKGROUND', (0,i), (-1,i), colors.HexColor('#F8FAFC')))
    table.setStyle(TableStyle(t_style))
    return table
