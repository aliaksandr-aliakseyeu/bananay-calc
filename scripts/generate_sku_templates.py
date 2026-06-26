"""Generate Excel templates for SKU import."""
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


def create_russian_template():
    """Create Russian SKU import template."""
    wb = Workbook()
    ws = wb.active
    ws.title = "SKU Import"
    
    ws.column_dimensions['A'].width = 5
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 18
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 30
    
    for col in ['G', 'H', 'I', 'J', 'K']:
        ws.column_dimensions[col].width = 12
    
    for col in ['L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T']:
        ws.column_dimensions[col].width = 12
    
    ws['A1'] = 'Шаблон импорта SKU (Единиц товара)'
    ws['A1'].font = Font(size=14, bold=True)
    ws.merge_cells('A1:T1')
    
    ws['A2'] = 'Инструкция: Заполните данные начиная с строки 7. Обязательные поля отмечены *'
    ws['A2'].font = Font(size=10, italic=True)
    ws.merge_cells('A2:T2')
    
    header_fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
    header_font = Font(bold=True, size=10)
    
    ws['A4'] = '№'
    ws['B4'] = 'наименование товара'
    ws['C4'] = 'артикул'
    ws['D4'] = 'Штрих код'
    ws['E4'] = 'ритейл/хорека'
    ws['F4'] = 'категория температурного режима'
    ws['G4'] = 'характеристики индивидуальной паковки'
    ws['L4'] = 'характеристики транспортировочной упаковки на евро паллете (120*80)'
    
    ws.merge_cells('G4:K4')
    ws.merge_cells('L4:T4')
    
    headers_row5 = [
        ('A5', '№'),
        ('B5', 'наименование товара *'),
        ('C5', 'артикул'),
        ('D5', 'Штрих код'),
        ('E5', 'канал'),
        ('F5', 'режим'),
        ('G5', 'длинна см.'),
        ('H5', 'ширина см.'),
        ('I5', 'высота см.'),
        ('J5', 'кол. В упаковке шт.'),
        ('K5', 'вес гр.'),
        ('L5', 'Длинна см.'),
        ('M5', 'Ширина см.'),
        ('N5', 'Высота см.'),
        ('O5', 'вес гр.'),
        ('P5', 'кол. На евро палете'),
        ('Q5', 'кол. В одном ряду'),
        ('R5', 'максимальное число рядов на паллете'),
        ('S5', 'высота, включая паллет'),
        ('T5', 'общий вес полного палета.'),
    ]
    
    for cell, value in headers_row5:
        ws[cell] = value
        ws[cell].fill = header_fill
        ws[cell].font = header_font
        ws[cell].alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'L']:
        cell = ws[f'{col}4']
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    example_data = [
        1,
        'Бананы премиум 1кг',
        'BAN-001',
        '4607034172015',
        'retail',
        '',
        20.5,
        15.3,
        10.8,
        20,
        1000,
        40.0,
        30.0,
        25.0,
        20000,
        480,
        24,
        20,
        165.0,
        500.0,
    ]
    
    for idx, value in enumerate(example_data, start=1):
        cell = ws.cell(row=7, column=idx, value=value)
        cell.font = Font(italic=True, color="808080")
    
    ws.freeze_panes = 'A6'
    
    wb.save('SKU_Import_Template_RU.xlsx')
    print("[OK] Russian template created: SKU_Import_Template_RU.xlsx")


def create_english_template():
    """Create English SKU import template."""
    wb = Workbook()
    ws = wb.active
    ws.title = "SKU Import"
    
    ws.column_dimensions['A'].width = 5
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 18
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 20
    
    for col in ['G', 'H', 'I', 'J', 'K']:
        ws.column_dimensions[col].width = 12
    
    for col in ['L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T']:
        ws.column_dimensions[col].width = 12
    
    ws['A1'] = 'SKU Import Template'
    ws['A1'].font = Font(size=14, bold=True)
    ws.merge_cells('A1:T1')
    
    ws['A2'] = 'Instructions: Fill in data starting from row 7. Required fields are marked with *'
    ws['A2'].font = Font(size=10, italic=True)
    ws.merge_cells('A2:T2')
    
    header_fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
    header_font = Font(bold=True, size=10)
    
    ws['A4'] = 'No.'
    ws['B4'] = 'Product Name'
    ws['C4'] = 'SKU Code'
    ws['D4'] = 'Barcode'
    ws['E4'] = 'Retail/HoReCa'
    ws['F4'] = 'Temperature Mode'
    ws['G4'] = 'Individual Package Characteristics'
    ws['L4'] = 'Transport Box Characteristics on Euro Pallet (120*80)'
    
    ws.merge_cells('G4:K4')
    ws.merge_cells('L4:T4')
    
    headers_row5 = [
        ('A5', 'No.'),
        ('B5', 'Product Name *'),
        ('C5', 'SKU Code'),
        ('D5', 'Barcode'),
        ('E5', 'Channel'),
        ('F5', 'Mode'),
        ('G5', 'Length (cm)'),
        ('H5', 'Width (cm)'),
        ('I5', 'Height (cm)'),
        ('J5', 'Items per Box'),
        ('K5', 'Weight (g)'),
        ('L5', 'Box Length (cm)'),
        ('M5', 'Box Width (cm)'),
        ('N5', 'Box Height (cm)'),
        ('O5', 'Box Weight (g)'),
        ('P5', 'Items per Pallet'),
        ('Q5', 'Items per Row'),
        ('R5', 'Max Rows'),
        ('S5', 'Pallet Height (cm)'),
        ('T5', 'Full Pallet Weight (kg)'),
    ]
    
    for cell, value in headers_row5:
        ws[cell] = value
        ws[cell].fill = header_fill
        ws[cell].font = header_font
        ws[cell].alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'L']:
        cell = ws[f'{col}4']
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    example_data = [
        1,
        'Premium Bananas 1kg',
        'BAN-001',
        '4607034172015',
        'retail',
        '',
        20.5,
        15.3,
        10.8,
        20,
        1000,
        40.0,
        30.0,
        25.0,
        20000,
        480,
        24,
        20,
        165.0,
        500.0,
    ]
    
    for idx, value in enumerate(example_data, start=1):
        cell = ws.cell(row=7, column=idx, value=value)
        cell.font = Font(italic=True, color="808080")
    
    ws.freeze_panes = 'A6'
    
    wb.save('SKU_Import_Template_EN.xlsx')
    print("[OK] English template created: SKU_Import_Template_EN.xlsx")


if __name__ == "__main__":
    create_russian_template()
    create_english_template()
    print("\nTemplates created successfully!")
    print("- SKU_Import_Template_RU.xlsx (Russian)")
    print("- SKU_Import_Template_EN.xlsx (English)")
