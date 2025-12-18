# Company List Integration Guide

## Overview

The PU Observatory Generator now includes a company list feature that allows the OpenAI Assistant to search for news about specific companies in the polyurethane industry. The company list is stored in the Assistant's vector store and automatically referenced during report generation.

## Files Created

1. **`development/company_list.json`** - The company list data file (JSON format)
2. **`core/company_list_manager.py`** - Functions to manage and upload the company list
3. **`development/upload_company_list.py`** - Script to upload the company list to OpenAI
4. **`development/upload_company_list.bat`** - Windows batch file for easy execution

## Company List Structure

The `company_list.json` file contains:

- **Companies**: List of companies with:
  - Name (official name)
  - Aliases (alternative names/legal entities)
  - Value Chain Position (MDI Producer, TDI Producer, Polyols Producer, Systems, Foam Manufacturer, etc.)
  - Regions (where they operate)
  - Status (active, acquired, merged, etc.)
  - Notes (additional context)

- **Categories**: Auto-generated mapping of value chain positions to companies

## Initial Setup

### Step 1: Upload the Company List

Run the upload script to attach the company list to your OpenAI Assistant:

**Windows:**
```bash
upload_company_list.bat
```

**Or manually:**
```bash
python development/upload_company_list.py
```

This will:
1. Load the company list from `development/company_list.json`
2. Format it for the Assistant
3. Upload it to OpenAI
4. Create/update a vector store
5. Attach it to your Assistant

### Step 2: Verify Integration

After uploading, the Assistant will automatically:
- Reference the company list when generating reports
- Search for news about listed companies
- Filter by value chain position and regions
- Exclude inactive/acquired companies

## Updating the Company List

### Method 1: Edit JSON File

1. Edit `development/company_list.json`
2. Add/remove/update companies as needed
3. Run `upload_company_list.bat` again to upload changes

### Method 2: Programmatic Update

Use the `update_company_list_file()` function in `core/company_list_manager.py`:

```python
from core.company_list_manager import update_company_list_file

companies = [
    {
        "name": "New Company",
        "aliases": ["New Company Inc."],
        "value_chain_position": ["MDI Producer"],
        "regions": ["EMEA"],
        "status": "active",
        "notes": "New MDI producer"
    }
]

update_company_list_file(companies=companies)
```

Then run the upload script again.

## How It Works

1. **During Report Generation:**
   - The Assistant receives instructions to check the company list
   - It searches for news about companies relevant to the selected deliverables and regions
   - It prioritizes companies from the list
   - It verifies company status (excludes inactive/acquired companies)

2. **Vector Store:**
   - The company list is stored in OpenAI's vector store
   - The Assistant can retrieve and reference it during runs
   - Updates require re-uploading the file

3. **Filtering:**
   - Companies are filtered by:
     - Value chain position (matches selected deliverables)
     - Regions (matches selected regions)
     - Status (only active companies)

## Example Company Entry

```json
{
  "name": "BASF",
  "aliases": ["BASF SE", "BASF Corporation"],
  "value_chain_position": ["MDI Producer", "TDI Producer", "Polyols Producer", "Systems"],
  "regions": ["EMEA", "North America", "China", "SEA"],
  "status": "active",
  "notes": "Major MDI and polyols producer"
}
```

## Troubleshooting

### Error: "Assistant ID not found"
- Check that `OPENAI_ASSISTANT_ID` is set in your `.env` file

### Error: "OpenAI client not available"
- Check that `OPENAI_API_KEY` is set in your `.env` file

### Company list not being used
- Verify the upload was successful (check the output)
- Check that the Assistant has file_search enabled
- Ensure the vector store is attached to the Assistant

### Need to remove a company
- Set `"status": "inactive"` in the JSON file
- Or remove the company entry entirely
- Re-upload the list

## Best Practices

1. **Keep the list current**: Update regularly as companies merge, acquire, or change status
2. **Use aliases**: Include all common names/legal entities for better matching
3. **Categorize correctly**: Assign accurate value chain positions for proper filtering
4. **Document changes**: Update `last_updated` date when modifying the list
5. **Test after updates**: Generate a test report after updating the company list

## Next Steps

- Add more companies to the list as needed
- Consider adding company websites/domains for better source verification
- Add industry segments (automotive, construction, etc.) for more granular filtering
- Create an Admin UI to manage the company list (future enhancement)

