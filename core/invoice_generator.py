"""
Invoice and Receipt Generator
Generates HTML invoices and receipts based on company location (Thai vs Foreign)
"""

import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from core.pricing import calculate_price


# Company information
COMPANY_NAME = "HTC Global Co., Ltd. (Head Office)"
COMPANY_ADDRESS = "2521/24 Lat Phrao Road, Khlong Chao Khun Singh Wang Thonglang District, Bangkok 10310"
COMPANY_TAX_ID = "0205567053001"
COMPANY_BRANCH = "381/159 Jomtien Second road, Soi 7, The Park Condominium, Apt. 6, Bang Lamung, 20150, Thailand"
COMPANY_SIGNATURE = "Stefan Hermes\nManaging Director\nHTC Global"

# Image paths (relative to project root)
LOGO_PATH = "Logo in blue steel no BG.png"
SIGNATURE_PATH = "Signature.jpg"


def image_to_base64(image_path: str) -> str:
    """Convert image file to base64 data URI for embedding in HTML."""
    try:
        img_path = Path(image_path)
        if img_path.exists():
            with open(img_path, 'rb') as img_file:
                img_data = img_file.read()
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                # Determine MIME type from extension
                ext = img_path.suffix.lower()
                mime_types = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif'
                }
                mime_type = mime_types.get(ext, 'image/png')
                return f"data:{mime_type};base64,{img_base64}"
        return ""
    except Exception:
        return ""

# Bank details
BANK_NAME = "Siam Commercial Bank"
BANK_ACCOUNT = "863-300688-9"
BANK_SWIFT = "SICOTHBKXXX"

# VAT rate for Thai companies
VAT_RATE = 0.07  # 7%


def is_thai_company(
    company_address: Optional[str] = None, 
    company_name: Optional[str] = None,
    country: Optional[str] = None
) -> bool:
    """
    Determine if company is Thai (domestic) or foreign.
    Priority: country field > address > company name
    
    Args:
        company_address: Full address string
        company_name: Company name
        country: Country name (preferred method)
    
    Returns:
        True if Thai company, False if foreign
    """
    # First check: Use country field if available (most reliable)
    if country:
        country_lower = country.lower().strip()
        thai_country_names = ['thailand', 'thai', 'ประเทศไทย', 'th']
        if any(thai_name in country_lower for thai_name in thai_country_names):
            return True
        # If country is explicitly set and not Thailand, it's foreign
        if country_lower and country_lower not in ['', 'thailand', 'thai', 'ประเทศไทย', 'th']:
            return False
    
    # Second check: Address contains Thai indicators
    if company_address:
        address_lower = company_address.lower()
        thai_indicators = ['thailand', 'bangkok', 'thai', 'ประเทศไทย', 'chiang mai', 'phuket', 'pattaya']
        for indicator in thai_indicators:
            if indicator in address_lower:
                return True
    
    # Third check: Company name suggests Thai company
    if company_name:
        name_lower = company_name.lower()
        thai_name_indicators = ['thai', 'thailand', 'bangkok', 'ประเทศไทย']
        for indicator in thai_name_indicators:
            if indicator in name_lower:
                return True
    
    # Default: assume foreign if no Thai indicators found
    return False


def generate_invoice_number() -> str:
    """Generate invoice number in format YYYY-MM-###"""
    now = datetime.now()
    # In production, this should query database for next sequential number
    # For now, use timestamp-based number
    sequence = int(now.timestamp() % 10000)
    return f"{now.year}-{now.month:02d}-{sequence:03d}"


def generate_commercial_invoice_html(
    invoice_number: str,
    customer_name: str,
    customer_address: str,
    customer_contact: str,
    item_description: str,
    amount: float,
    is_thai: bool = False,
    date: Optional[datetime] = None,
    contact_person: Optional[str] = None,
    vat_number: Optional[str] = None
) -> str:
    """
    Generate HTML commercial invoice.
    
    Args:
        invoice_number: Invoice number (format: YYYY-MM-###)
        customer_name: Customer company name
        customer_address: Customer address
        customer_contact: Customer contact email/phone
        item_description: Description of service/item
        amount: Base amount (before VAT if applicable)
        is_thai: Whether company is Thai (affects VAT)
        date: Invoice date (defaults to today)
    """
    if date is None:
        date = datetime.now()
    
    # Calculate VAT and total
    if is_thai:
        vat_amount = amount * VAT_RATE
        total_amount = amount + vat_amount
        show_vat = True
    else:
        vat_amount = 0
        total_amount = amount
        show_vat = False
    
    # Format currency
    def format_currency(value):
        return f"{value:,.2f}"
    
    # Get base64 encoded images
    logo_base64 = image_to_base64(LOGO_PATH)
    signature_base64 = image_to_base64(SIGNATURE_PATH)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Commercial Invoice - {invoice_number}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                color: #333;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                border-bottom: 2px solid #333;
                padding-bottom: 20px;
            }}
            .header-logo {{
                max-width: 150px;
                height: auto;
            }}
            .header-title {{
                flex: 1;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: bold;
            }}
            .company-info {{
                margin-bottom: 30px;
            }}
            .company-info h2 {{
                margin: 0 0 10px 0;
                font-size: 18px;
            }}
            .invoice-details {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 30px;
            }}
            .customer-info {{
                background-color: #f5f5f5;
                padding: 15px;
                border-radius: 5px;
            }}
            .invoice-info {{
                text-align: right;
            }}
            .invoice-info p {{
                margin: 5px 0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 30px;
            }}
            table th {{
                background-color: #333;
                color: white;
                padding: 12px;
                text-align: left;
            }}
            table td {{
                padding: 10px;
                border-bottom: 1px solid #ddd;
            }}
            table tr:last-child td {{
                border-bottom: 2px solid #333;
                font-weight: bold;
            }}
            .text-right {{
                text-align: right;
            }}
            .payment-info {{
                background-color: #f9f9f9;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 30px;
            }}
            .payment-info h3 {{
                margin-top: 0;
            }}
            .signature {{
                margin-top: 50px;
                text-align: right;
            }}
            .signature p {{
                margin: 5px 0;
                white-space: pre-line;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            {f'<img src="{logo_base64}" alt="HTC Global Logo" class="header-logo">' if logo_base64 else ''}
            <div class="header-title">
                <h1>Commercial Invoice</h1>
            </div>
            <div style="width: 150px;"></div> <!-- Spacer for balance -->
        </div>
        
        <div class="invoice-details">
            <div class="customer-info">
                <h2>Bill To:</h2>
                <p><strong>{customer_name}</strong></p>
                {f'<p><strong>Attn:</strong> {contact_person}</p>' if contact_person else ''}
                <p>{customer_address.replace(chr(10), '<br>') if customer_address else ''}</p>
                {f'<p><strong>VAT Number:</strong> {vat_number}</p>' if vat_number else ''}
                <p>{customer_contact}</p>
            </div>
            
            <div class="invoice-info">
                <p><strong>Date:</strong> {date.strftime('%d/%m/%Y')}</p>
                <p><strong>Invoice Number:</strong> {invoice_number}</p>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Item</th>
                    <th class="text-right">Amount</th>
                    {f'<th class="text-right">VAT (7%)</th>' if show_vat else ''}
                    <th class="text-right">Total</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>{item_description}</td>
                    <td class="text-right">{format_currency(amount)} USD</td>
                    {f'<td class="text-right">{format_currency(vat_amount)} USD</td>' if show_vat else ''}
                    <td class="text-right">{format_currency(total_amount)} USD</td>
                </tr>
                <tr>
                    <td><strong>Sum</strong></td>
                    <td class="text-right"><strong>{format_currency(amount)} USD</strong></td>
                    {f'<td class="text-right"><strong>{format_currency(vat_amount)} USD</strong></td>' if show_vat else ''}
                    <td class="text-right"><strong>{format_currency(total_amount)} USD</strong></td>
                </tr>
            </tbody>
        </table>
        
        <div class="payment-info">
            <h3>COMMENTS</h3>
            <p>Payment within 15 days to the following account number</p>
            <p><strong>{COMPANY_NAME}</strong><br>
            {COMPANY_ADDRESS}<br>
            Tax Identification Number VAT nr. {COMPANY_TAX_ID}</p>
            <p><strong>{BANK_NAME}</strong><br>
            Account number: {BANK_ACCOUNT}<br>
            SWIFT: {BANK_SWIFT}</p>
        </div>
        
        <div class="signature">
            <p>Kind regards<br>
            -------------------------<br>
            {COMPANY_SIGNATURE}</p>
        </div>
        
        <div class="footer">
            <p><strong>Head Office:</strong> {COMPANY_ADDRESS}</p>
            <p><strong>Branch Office:</strong> {COMPANY_BRANCH}</p>
        </div>
    </body>
    </html>
    """
    return html


def generate_receipt_html(
    receipt_number: str,
    invoice_number: str,
    invoice_date: str,
    customer_name: str,
    customer_address: str,
    customer_contact: str,
    item_description: str,
    amount: float,
    vat_amount: float,
    total_amount: float,
    date: Optional[datetime] = None,
    contact_person: Optional[str] = None,
    vat_number: Optional[str] = None
) -> str:
    """
    Generate HTML tax invoice/receipt (for Thai companies only).
    
    Args:
        receipt_number: Receipt number
        invoice_number: Reference invoice number
        invoice_date: Reference invoice date
        customer_name: Customer company name
        customer_address: Customer address
        customer_contact: Customer contact email/phone
        item_description: Description of service/item
        amount: Base amount
        vat_amount: VAT amount (7%)
        total_amount: Total amount including VAT
        date: Receipt date (defaults to today)
    """
    if date is None:
        date = datetime.now()
    
    def format_currency(value):
        return f"{value:,.2f}"
    
    # Get base64 encoded images
    logo_base64 = image_to_base64(LOGO_PATH)
    signature_base64 = image_to_base64(SIGNATURE_PATH)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Tax Invoice/Receipt - {receipt_number}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                color: #333;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
            }}
            .header-logo {{
                max-width: 150px;
                height: auto;
            }}
            .header-title {{
                flex: 1;
                text-align: center;
            }}
            .header h1 {{
                margin: 0 0 10px 0;
                font-size: 24px;
                font-weight: bold;
            }}
            .company-info {{
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid #333;
            }}
            .company-info h2 {{
                margin: 0 0 10px 0;
                font-size: 18px;
            }}
            .invoice-details {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 30px;
            }}
            .customer-info {{
                background-color: #f5f5f5;
                padding: 15px;
                border-radius: 5px;
            }}
            .receipt-info {{
                text-align: right;
            }}
            .receipt-info p {{
                margin: 5px 0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 30px;
            }}
            table th {{
                background-color: #333;
                color: white;
                padding: 12px;
                text-align: left;
            }}
            table td {{
                padding: 10px;
                border-bottom: 1px solid #ddd;
            }}
            table tr:last-child td {{
                border-bottom: 2px solid #333;
                font-weight: bold;
            }}
            .text-right {{
                text-align: right;
            }}
            .payment-received {{
                background-color: #f9f9f9;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 30px;
            }}
            .payment-received h3 {{
                margin-top: 0;
            }}
            .signature {{
                margin-top: 50px;
                text-align: right;
            }}
            .signature-content {{
                display: inline-block;
                text-align: left;
            }}
            .signature-image {{
                max-width: 200px;
                height: auto;
                margin-top: 10px;
            }}
            .signature p {{
                margin: 5px 0;
                white-space: pre-line;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            {f'<img src="{logo_base64}" alt="HTC Global Logo" class="header-logo">' if logo_base64 else ''}
            <div class="header-title">
                <h1>Tax Invoice/Receipt</h1>
            </div>
            <div style="width: 150px;"></div> <!-- Spacer for balance -->
        </div>
        
        <div class="company-info">
            <h2>{COMPANY_NAME}</h2>
            <p>{COMPANY_ADDRESS}<br>
            Tax Identification Number VAT nr. {COMPANY_TAX_ID}</p>
        </div>
        
        <div class="invoice-details">
            <div class="customer-info">
                <h2>Bill To:</h2>
                <p><strong>{customer_name}</strong></p>
                <p>{customer_address.replace(chr(10), '<br>') if customer_address else ''}</p>
                <p>{customer_contact}</p>
            </div>
            
            <div class="receipt-info">
                <p><strong>Date:</strong> {date.strftime('%d/%m/%Y')}</p>
                <p><strong>Ref Invoice Number:</strong> {invoice_number}</p>
                <p><strong>Ref Invoice Date:</strong> {invoice_date}</p>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Item</th>
                    <th class="text-right">Amount</th>
                    <th class="text-right">VAT (7%)</th>
                    <th class="text-right">Total</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>{item_description}</td>
                    <td class="text-right">{format_currency(amount)} USD</td>
                    <td class="text-right">{format_currency(vat_amount)} USD</td>
                    <td class="text-right">{format_currency(total_amount)} USD</td>
                </tr>
                <tr>
                    <td><strong>Sum</strong></td>
                    <td class="text-right"><strong>{format_currency(amount)} USD</strong></td>
                    <td class="text-right"><strong>{format_currency(vat_amount)} USD</strong></td>
                    <td class="text-right"><strong>{format_currency(total_amount)} USD</strong></td>
                </tr>
            </tbody>
        </table>
        
        <div class="payment-received">
            <h3>Payment received by:</h3>
            <p>☐ Bank  ☐ Cash  ☐ Cheque</p>
        </div>
        
        <div class="signature">
            <div class="signature-content">
                <p>Kind regards<br>
                -------------------------<br>
                {COMPANY_SIGNATURE}</p>
                {f'<img src="{signature_base64}" alt="Signature" class="signature-image">' if signature_base64 else ''}
            </div>
        </div>
        
        <div class="footer">
            <p><strong>Head Office:</strong> {COMPANY_ADDRESS}</p>
            <p><strong>Branch Office:</strong> {COMPANY_BRANCH}</p>
        </div>
    </body>
    </html>
    """
    return html


def generate_invoice_documents(
    request_data: Dict,
    workspace_data: Optional[Dict] = None
) -> Dict[str, str]:
    """
    Generate invoice and/or receipt documents based on company location.
    
    Args:
        request_data: Specification request data
        workspace_data: Optional workspace data (for company address)
    
    Returns:
        Dictionary with 'invoice_html' and optionally 'receipt_html'
    
    Raises:
        ValueError: If request_data is invalid or missing required fields
    """
    if not request_data or not isinstance(request_data, dict):
        raise ValueError("request_data must be a non-empty dictionary")
    
    # Determine if Thai company
    company_name = request_data.get('company_name', '')
    if not company_name:
        raise ValueError("company_name is required in request_data")
    
    # Build company address from request data
    address_parts = []
    if request_data.get('street'):
        street = request_data.get('street')
        if request_data.get('house_number'):
            street += f" {request_data.get('house_number')}"
        address_parts.append(street)
    if request_data.get('city'):
        city = request_data.get('city')
        if request_data.get('zip_code'):
            city += f" {request_data.get('zip_code')}"
        address_parts.append(city)
    if request_data.get('country'):
        address_parts.append(request_data.get('country'))
    
    # Use workspace address as fallback if request doesn't have address
    company_address = '\n'.join(address_parts) if address_parts else ''
    if not company_address and workspace_data and isinstance(workspace_data, dict):
        company_address = workspace_data.get('company_address', '')
    if not company_address:
        company_address = company_name  # Final fallback
    
    customer_contact = request_data.get('contact_email', '')
    
    # Build contact person name
    first_name = request_data.get('first_name', '')
    last_name = request_data.get('last_name', '')
    contact_person = f"{first_name} {last_name}".strip() if (first_name or last_name) else None
    
    # Get VAT number
    vat_number = request_data.get('vat_number', '')
    
    # Get country for Thai company determination
    country = request_data.get('country', '')
    
    # Determine if Thai company (use country field if available, otherwise fall back to address/name)
    is_thai = is_thai_company(company_address, company_name, country)
    
    # Calculate pricing (annual amount)
    price_info = calculate_price(
        request_data.get('categories', []),
        request_data.get('regions', []),
        request_data.get('frequency', 'monthly'),
        num_users=1
    )
    
    # Use annual price (total_price is the annual amount)
    amount = price_info['total_price']
    if is_thai:
        vat_amount = amount * VAT_RATE
        total_amount = amount + vat_amount
    else:
        vat_amount = 0
        total_amount = amount
    
    # Generate invoice number
    invoice_number = generate_invoice_number()
    invoice_date = datetime.now()
    
    # Item description
    item_description = f"PU Observatory Intelligence Source - {request_data.get('newsletter_name', 'Intelligence Service')}"
    
    # Ensure customer_address is a string (never None)
    safe_customer_address = str(company_address) if company_address else str(company_name)
    
    # Generate invoice
    invoice_html = generate_commercial_invoice_html(
        invoice_number=invoice_number,
        customer_name=company_name,
        customer_address=safe_customer_address,
        customer_contact=customer_contact,
        item_description=item_description,
        amount=amount,
        is_thai=is_thai,
        date=invoice_date,
        contact_person=contact_person,
        vat_number=vat_number if vat_number else None
    )
    
    result = {
        'invoice_html': invoice_html,
        'invoice_number': invoice_number,
        'invoice_date': invoice_date.strftime('%d/%m/%Y'),
        'amount': amount,
        'vat_amount': vat_amount,
        'total_amount': total_amount,
        'is_thai': is_thai
    }
    
    # Generate receipt for Thai companies
    if is_thai:
        receipt_number = generate_invoice_number().replace('-', '-R-')
        receipt_html = generate_receipt_html(
            receipt_number=receipt_number,
            invoice_number=invoice_number,
            invoice_date=invoice_date.strftime('%d/%m/%Y'),
            customer_name=company_name,
            customer_address=safe_customer_address,
            customer_contact=customer_contact,
            item_description=item_description,
            amount=amount,
            vat_amount=vat_amount,
            total_amount=total_amount,
            date=invoice_date,
            contact_person=contact_person,
            vat_number=vat_number if vat_number else None
        )
        result['receipt_html'] = receipt_html
        result['receipt_number'] = receipt_number
    
    return result

