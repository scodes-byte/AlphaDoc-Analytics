import os
import subprocess
import sys

# Ensure reportlab is installed
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
except ImportError:
    print("[Sample Generator] Installing reportlab library...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

def create_financial_pdf(filename, company_name, kpi_data, risks, ceo_text):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1e1b4b'),
        spaceAfter=12
    )
    
    section_style = ParagraphStyle(
        'DocSection',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#4338ca'),
        spaceBefore=14,
        spaceAfter=8
    )
    
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#374151'),
        spaceAfter=8
    )
    
    story = []
    
    # 1. Header
    story.append(Paragraph(f"{company_name} - Q4 2025 Financial Statement", title_style))
    story.append(Paragraph("Published: January 2026 | Regulatory Filing Report", body_style))
    story.append(Spacer(1, 15))
    
    # 2. Executive Summary
    story.append(Paragraph("Executive Financial Summary", section_style))
    summary_text = (f"This report outlines the financial performance metrics of {company_name} "
                    f"for the fourth quarter of the fiscal year 2025. Over the last four quarters, "
                    f"operational scale has adjusted to shifting macroeconomic indices. Under strict fiscal "
                    f"governance, capital deployment was balanced across target product segments.")
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 10))
    
    # 3. Tabular KPIs
    story.append(Paragraph("Quarterly Financial Metrics", section_style))
    
    # Prepare table data
    table_data = [['Period', 'Revenue ($M)', 'Operating Margin (%)', 'Net Income ($M)', 'EPS ($)']]
    for row in kpi_data:
        table_data.append([
            row['period'],
            f"{row['revenue']}",
            f"{row['operating_margin']}",
            f"{row['net_income']}",
            f"{row['eps']}"
        ])
        
    t = Table(table_data, colWidths=[100, 100, 120, 100, 80])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4338ca')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f3f4f6')),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#e5e7eb')),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('TOPPADDING', (0,1), (-1,-1), 6),
        ('BOTTOMPADDING', (0,1), (-1,-1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))
    
    # 4. Narrative Risks
    story.append(Paragraph("Risk Management and Headwinds", section_style))
    for idx, risk in enumerate(risks):
        story.append(Paragraph(f"<b>Risk Factor {idx+1}:</b> {risk}", body_style))
    story.append(Spacer(1, 10))
    
    # 5. CEO perspective
    story.append(Paragraph("Strategic Outlook & CEO Statement", section_style))
    story.append(Paragraph(f"<i>\"{ceo_text}\"</i>", body_style))
    
    doc.build(story)
    print(f"[Sample Generator] Created PDF: {filename}")

if __name__ == "__main__":
    # Create samples directory
    samples_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples")
    os.makedirs(samples_dir, exist_ok=True)
    
    # 1. Apple Dataset
    apple_kpis = [
        {"period": "Q1 2025", "revenue": 119580.0, "operating_margin": 30.7, "net_income": 33920.0, "eps": 2.18},
        {"period": "Q2 2025", "revenue": 90750.0, "operating_margin": 28.4, "net_income": 23640.0, "eps": 1.53},
        {"period": "Q3 2025", "revenue": 85780.0, "operating_margin": 27.8, "net_income": 21450.0, "eps": 1.40},
        {"period": "Q4 2025", "revenue": 94930.0, "operating_margin": 29.1, "net_income": 22960.0, "eps": 1.50}
    ]
    apple_risks = [
        "Component cost supply fluctuations, specifically around logic memory modules and OLED screens.",
        "Regulatory constraints regarding app-store fee distributions inside the European Union.",
        "Foreign exchange rate variations resulting in minor gross margin compression in APAC regions."
    ]
    apple_ceo = "We reported record-breaking revenue scaling across services, offsetting cyclical hardware declines. Our strategic investments in advanced machine learning integrations at the operating system level are driving strong customer interest and loyalty."
    
    create_financial_pdf(
        os.path.join(samples_dir, "Apple_Q4_2025_Report.pdf"),
        "Apple",
        apple_kpis,
        apple_risks,
        apple_ceo
    )

    # 2. Tesla Dataset
    tesla_kpis = [
        {"period": "Q1 2025", "revenue": 21300.0, "operating_margin": 5.5, "net_income": 1130.0, "eps": 0.34},
        {"period": "Q2 2025", "revenue": 25500.0, "operating_margin": 6.3, "net_income": 1480.0, "eps": 0.42},
        {"period": "Q3 2025", "revenue": 25180.0, "operating_margin": 6.2, "net_income": 1670.0, "eps": 0.48},
        {"period": "Q4 2025", "revenue": 27850.0, "operating_margin": 7.1, "net_income": 2010.0, "eps": 0.58}
    ]
    tesla_risks = [
        "Highly volatile electric vehicle pricing environments globally, compressing margin baselines.",
        "Logistical shipping disruptions slowing output capacity expansions at Giga Berlin.",
        "Capital-intensive infrastructure build-outs for autonomous computing networks."
    ]
    tesla_ceo = "We achieved strong vehicle delivery volumes despite operational friction. Our focus on optimizing production costs per vehicle, combined with energy storage growth, is driving improved margins and cash flow."
    
    create_financial_pdf(
        os.path.join(samples_dir, "Tesla_Q4_2025_Report.pdf"),
        "Tesla",
        tesla_kpis,
        tesla_risks,
        tesla_ceo
    )

    # 3. Microsoft Dataset
    msft_kpis = [
        {"period": "Q1 2025", "revenue": 61860.0, "operating_margin": 43.2, "net_income": 21940.0, "eps": 2.94},
        {"period": "Q2 2025", "revenue": 64730.0, "operating_margin": 42.8, "net_income": 22000.0, "eps": 2.95},
        {"period": "Q3 2025", "revenue": 65590.0, "operating_margin": 41.5, "net_income": 21850.0, "eps": 2.93},
        {"period": "Q4 2025", "revenue": 69120.0, "operating_margin": 43.6, "net_income": 24200.0, "eps": 3.24}
    ]
    msft_risks = [
        "Intense pricing competitions across enterprise multi-tenant cloud platforms.",
        "Significant hardware capital expenses required to scale generative AI GPU clusters.",
        "Sovereign data governance rules restricting cross-border cloud processing agreements."
    ]
    msft_ceo = "Our Cloud division continues to outpace the market, driven by secular demand for AI integration. By embedding AI capabilities directly into our widely used productivity suite, we are expanding our competitive advantages globally."
    
    create_financial_pdf(
        os.path.join(samples_dir, "Microsoft_Q4_2025_Report.pdf"),
        "Microsoft",
        msft_kpis,
        msft_risks,
        msft_ceo
    )
    
    print("\n[Success] All three sample reports generated in the 'samples/' directory.")
