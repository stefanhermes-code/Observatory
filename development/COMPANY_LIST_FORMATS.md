# Company List Text File Formats

You can provide a text file with your company list, and it will be automatically converted to JSON format.

## Supported Formats

### Format 1: Simple List (One Company Per Line)

```
BASF
Covestro
Dow Chemical
Huntsman
Wanhua Chemical
```

**Pros:** Quick and easy  
**Cons:** You'll need to manually add value chain positions and regions later

### Format 2: Structured Format (Key-Value Pairs)

```
BASF
Aliases: BASF SE, BASF Corporation
Position: MDI Producer, TDI Producer, Polyols Producer, Systems
Regions: EMEA, North America, China, SEA
Notes: Major MDI and polyols producer
---
Covestro
Aliases: Covestro AG, Covestro LLC
Position: MDI Producer, TDI Producer, Polyols Producer, Systems
Regions: EMEA, North America, China, SEA
Notes: Major MDI and TDI producer, spun off from Bayer
---
```

**Pros:** Complete information  
**Cons:** More typing

### Format 3: Pipe-Separated (CSV-like)

```
Company Name | Aliases | Position | Regions | Notes
BASF | BASF SE, BASF Corporation | MDI Producer, TDI Producer | EMEA, North America | Major producer
Covestro | Covestro AG | MDI Producer, TDI Producer | EMEA, North America | Spun off from Bayer
```

**Pros:** Easy to edit in Excel/Google Sheets  
**Cons:** Less readable

### Format 4: Mixed Format

You can mix formats in the same file. The converter will try to parse each line appropriately.

## Usage

1. **Create your text file** (e.g., `companies.txt`) using any of the formats above
2. **Run the converter:**
   ```bash
   convert_company_list.bat companies.txt
   ```
   Or:
   ```bash
   python development/convert_company_list_txt.py companies.txt
   ```
3. **Review the generated JSON** (`company_list.json`)
4. **Manually edit** if needed (add missing positions, regions, etc.)
5. **Upload to Assistant:**
   ```bash
   upload_company_list.bat
   ```

## Value Chain Positions

Common positions to use:
- MDI Producer
- TDI Producer
- Polyols Producer
- Systems
- Foam Manufacturer
- Additives Producer
- Equipment Manufacturer

## Regions

Common regions:
- EMEA
- Middle East
- China
- NE Asia
- SEA
- India
- North America
- South America

## Tips

1. **Start simple:** Use Format 1 to get started quickly, then manually add details
2. **Use aliases:** Include all common names/legal entities for better matching
3. **Be consistent:** Use the same position/region names throughout
4. **Check status:** Mark inactive companies with `Status: inactive`

## Example: Complete Text File

```
# PU Industry Company List
# Last Updated: 2025-01-18

BASF
Aliases: BASF SE, BASF Corporation
Position: MDI Producer, TDI Producer, Polyols Producer, Systems
Regions: EMEA, North America, China, SEA
Notes: Major MDI and polyols producer
Status: active
---
Covestro
Aliases: Covestro AG, Covestro LLC
Position: MDI Producer, TDI Producer, Polyols Producer, Systems
Regions: EMEA, North America, China, SEA
Notes: Major MDI and TDI producer, spun off from Bayer
Status: active
---
```

Save this as `companies.txt` and run the converter!

