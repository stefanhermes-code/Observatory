-- Migration: Add address and VAT fields to specification_requests
-- Date: 2025-01-XX
-- Description: Adds street, house_number, city, zip_code, country, and vat_number fields for proper invoicing

ALTER TABLE specification_requests 
ADD COLUMN IF NOT EXISTS street VARCHAR(255),
ADD COLUMN IF NOT EXISTS house_number VARCHAR(50),
ADD COLUMN IF NOT EXISTS city VARCHAR(255),
ADD COLUMN IF NOT EXISTS zip_code VARCHAR(50),
ADD COLUMN IF NOT EXISTS country VARCHAR(255),
ADD COLUMN IF NOT EXISTS vat_number VARCHAR(100);

-- Verify the columns were added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'specification_requests'
AND column_name IN ('street', 'house_number', 'city', 'zip_code', 'country', 'vat_number');

