 Revamp the CSV import system for DonorCRM with two import layers:                                 

                                                                                                                          

  1. **Generic CSV Import** - For donations and contacts, with user-scoped processing                                     

  2. **Raiser's Edge Import** - For constituents, solicitors, gifts, and recurring gifts with SHA256 deduplication        

                                                                                                                          

  ---                                                                                                                     

                                                                                                                          

  ## DATABASE SCHEMA                                                                                                      

                                                                                                                          

  Add these Prisma models and enums:                                                                                      

                                                                                                                          

  ### Enums                                                                                                               

  - `ImportStatus`: PENDING, STARTED, PROCESSING, COMPLETE, SUCCEEDED, SUCCEEDED_WITH_ERRORS, FAILED                      

  - `ImportType`: CONSTITUENT, SOLICITOR, GIFT, RECURRING_GIFT                                                            

                                                                                                                          

  ### ImportBatch Model                                                                                                   

  Track import jobs with deduplication:                                                                                   

  - id (UUID), userId (optional FK to User), filename, sha256 (VARCHAR 64)                                                

  - type (ImportType), rowCount, rowsTotal, rowsImported, rowsSkipped                                                     

  - status (ImportStatus), errorLog (Text), summaryJson (Json)                                                            

  - UNIQUE constraint on (type, sha256) - prevents duplicate file imports                                                 

                                                                                                                          

  ### Solicitor Model                                                                                                     

  Fundraisers who receive gift credit:                                                                                    

  - id (UUID), externalSolicitorId (unique, optional), name, normalizedName (unique, lowercase for matching)              

  - Relations to GiftCredit and RecurringGiftCredit                                                                       

                                                                                                                          

  ### Gift Model                                                                                                          

  One-time gifts from Raiser's Edge:                                                                                      

  - externalGiftId (unique required), externalConstituentId, donorContactId (FK to Contact)                               

  - giftDate, lastChangedAt, giftType, fundId, fundSplitAmountCents (integer cents)                                       

  - isAnonymous, paymentType, paymentMethod, description (for prayer requests)                                            

  - importBatchId (FK), relations to GiftCredit[]                                                                         

                                                                                                                          

  ### GiftCredit Model                                                                                                    

  Junction table for Gift-to-Solicitor (many-to-many):                                                                    

  - giftId (FK), solicitorId (optional FK), solicitorName (original from CSV)                                             

  - solicitorAmountCents (integer cents)                                                                                  

  - Index on (giftId, solicitorName) for upsert lookups                                                                   

                                                                                                                          

  ### RecurringGift Model                                                                                                 

  Same as Gift but with installment fields:                                                                               

  - installmentAmountCents, installmentFrequency, installmentsScheduled                                                   

  - firstInstallmentDue, lastInstallmentDue, status, statusDate                                                           

                                                                                                                          

  ### RecurringGiftCredit Model                                                                                           

  Same as GiftCredit but FK to RecurringGift                                                                              

                                                                                                                          

  ### Contact Model Updates                                                                                               

  Add: externalConstituentId (unique), organizationName, addressLine1, addressLine2, lastChangedAt                        

                                                                                                                          

  ---                                                                                                                     

                                                                                                                          

  ## BACKEND API MODULE (src/modules/import-export/)                                                                      

                                                                                                                          

  ### Shared Utilities (raisers-edge/shared.ts)                                                                           

  Create these helper functions:                                                                                          

  - `computeSha256(buffer)` - SHA256 hash for file deduplication                                                          

  - `parseCSV<T>(buffer)` - Stream-based csv-parse with relaxQuotes for messy RE exports                                  

  - `parseDate(str)` - Handle MM/DD/YYYY, M/D/YYYY, YYYY-MM-DD formats                                                    

  - `parseAmount(str)` - Strip $, commas, handle negatives in parentheses                                                 

  - `parseCurrencyToCents(str)` - Convert "$1,234.56" to 123456 integer                                                   

  - `parseBoolean(str)` - Handle yes/no/true/false/1/0                                                                    

  - `normalizePhone(phone)` - Format as (NNN) NNN-NNNN                                                                    

  - `normalizeName(name)` - Lowercase, trim, collapse spaces (for solicitor matching)                                     

  - `cleanString(value)` - Trim, return null if empty                                                                     

  - `normalizeEmail(email)` - Lowercase + trim                                                                            

  - `validateHeaders(actual, required)` - Return { valid, missing[], extra[] }                                            

                                                                                                                          

  Define ImportResult interface:                                                                                          

  ```typescript                                                                                                           

  {                                                                                                                       

    batchId: string;                                                                                                      

    type: string;                                                                                                         

    filename: string;                                                                                                     

    sha256: string;                                                                                                       

    status: 'SUCCEEDED' | 'SUCCEEDED_WITH_ERRORS' | 'FAILED';                                                             

    totals: { rows, created, updated, skipped, errors, warnings };                                                        

    warnings: Array<{ message, detail? }>;                                                                                

    errors: Array<{ rowNumber, reason, field?, value? }>;                                                                 

    alreadyProcessed?: boolean;                                                                                           

  }                                                                                                                       

                                                                                                                          

  Import Batch Service (raisers-edge/importBatch.ts)                                                                      

                                                                                                                          

  Centralized batch lifecycle with idempotency:                                                                           

  - checkExistingBatch(type, sha256) - Return existing result if file already processed                                   

  - createBatch(type, filename, buffer, rowCount, userId?) - Create with status STARTED                                   

  - completeBatch(batchId, result) - Set status SUCCEEDED/SUCCEEDED_WITH_ERRORS, store summaryJson                        

  - failBatch(batchId, error) - Set status FAILED                                                                         

                                                                                                                          

  Constituent Importer (raisers-edge/constituent.import.ts)                                                               

                                                                                                                          

  Required headers: Constituent ID, First Name, Last Name                                                                 

  Optional: Date Last Changed, Organization Name, Address Line 1/2, City, State, ZIP, Country, Phone, Email               

                                                                                                                          

  Matching logic (priority order):                                                                                        

  1. Match by externalConstituentId                                                                                       

  2. If not found, try email OR phone (if exactly 1 match)                                                                

  3. If still no match and userId provided, create new Contact as PROSPECT                                                

                                                                                                                          

  Update behavior: Merge-only - never overwrite existing data with null                                                   

                                                                                                                          

  Solicitor Importer (raisers-edge/solicitor.import.ts)                                                                   

                                                                                                                          

  Required headers: Name OR Solicitor Name                                                                                

  Optional: Solicitor System ID                                                                                           

                                                                                                                          

  - Track processedNames Set to skip duplicates within file                                                               

  - Match by normalizedName first, then externalSolicitorId                                                               

  - Create or update Solicitor record                                                                                     

                                                                                                                          

  Gift Importer (raisers-edge/gift.import.ts)                                                                             

                                                                                                                          

  Required headers: Gift ID, Gift Date, Constituent ID                                                                    

  Optional: Fund ID, Fund Split Amount, Gift Type, Solicitor Name, Solicitor Amount, Prayer Requests Description, etc.    

                                                                                                                          

  CRITICAL: RE exports multiple rows per gift when there are multiple solicitors.                                         

  Group all CSV rows by Gift ID, then process each group:                                                                 

  1. Find Contact by externalConstituentId                                                                                

  2. Upsert Gift record                                                                                                   

  3. For each solicitor row, upsert GiftCredit (match by giftId + solicitorName)                                          

                                                                                                                          

  Recurring Gift Importer (raisers-edge/recurring-gift.import.ts)                                                         

                                                                                                                          

  Same architecture as Gift importer for RecurringGift and RecurringGiftCredit                                            

                                                                                                                          

  Generic Import Service (import.service.ts)                                                                              

                                                                                                                          

  For donations and contacts CSV import with Zod validation:                                                              

                                                                                                                          

  importDonations(userId, buffer, filename, options):                                                                     

  - Parse CSV, validate each row with Zod schema                                                                          

  - Find/create Contact, create Donation record                                                                           

  - Auto-upgrade PROSPECT to DONOR when donation received                                                                 

  - Recalculate contact stats (lastGiftDate, lastGiftAmount, totalGiven)                                                  

  - Create audit Event record                                                                                             

                                                                                                                          

  Options: skipDuplicates, createContacts, matchByExternalId, matchByName                                                 

                                                                                                                          

  importContacts(userId, buffer, filename, options):                                                                      

  - Parse CSV, validate with Zod                                                                                          

  - Match by externalId or name, then skip/update/create based on options                                                 

                                                                                                                          

  Options: skipDuplicates, matchByExternalId, matchByName, updateExisting                                                 

                                                                                                                          

  Import Validator (import.validator.ts)                                                                                  

                                                                                                                          

  Zod schemas for:                                                                                                        

  - importRowSchema (donation row): externalId, firstName, lastName, email, phone, amount, date, type                     

  - contactImportRowSchema: all fields including contactType and full address                                             

                                                                                                                          

  Controllers                                                                                                             

                                                                                                                          

  Generic (import.controller.ts): importDonations, importContacts, getImportBatches, getImportBatch, download templates   

  RE (raisers-edge.controller.ts): Factory pattern handler for each import type                                           

                                                                                                                          

  HTTP status logic:                                                                                                      

  - 200: success or already-processed                                                                                     

  - 207: succeeded with errors                                                                                            

  - 500: full failure                                                                                                     

                                                                                                                          

  Export Controller (export.controller.ts)                                                                                

                                                                                                                          

  Three CSV export endpoints using csv-stringify:                                                                         

  - exportContacts - all user's contacts                                                                                  

  - exportDonations - with optional date/contact filters                                                                  

  - exportPledges - with optional active filter                                                                           

                                                                                                                          

  Routes (import-export.routes.ts)                                                                                        

                                                                                                                          

  Use multer with memoryStorage (10MB limit, CSV only filter).                                                            

                                                                                                                          

  Routes:                                                                                                                 

  - POST /import/donations (ADMIN, FUNDRAISER, FINANCE)                                                                   

  - POST /import/contacts (ADMIN, FUNDRAISER)                                                                             

  - POST /import/raisers-edge/constituents (ADMIN only)                                                                   

  - POST /import/raisers-edge/solicitors (ADMIN only)                                                                     

  - POST /import/raisers-edge/gifts (ADMIN only)                                                                          

  - POST /import/raisers-edge/recurring-gifts (ADMIN only)                                                                

  - GET /import/batches, GET /import/batches/:id                                                                          

  - GET /import/template/donations, GET /import/template/contacts                                                         

  - GET /export/contacts, GET /export/donations, GET /export/pledges                                                      

                                                                                                                          

  Also add aliases: /import/constituent, /import/solicitor, /import/gift, /import/recurring-gift                          

                                                                                                                          

  ---                                                                                                                     

  FRONTEND                                                                                                                

                                                                                                                          

  API Client (src/api/endpoints/import.ts)                                                                                

                                                                                                                          

  Create IMPORT_TYPE_CONFIG constant - single source of truth for UI:                                                     

  {                                                                                                                       

    constituent: {                                                                                                        

      label: 'Constituents',                                                                                              

      description: 'Import contacts from RE',                                                                             

      endpoint: '/import/constituent',                                                                                    

      requiredHeaders: ['Constituent ID', 'First Name', 'Last Name'],                                                     

      optionalHeaders: ['Organization Name', 'Email', 'Phone', 'Address Line 1', 'City', 'State', 'ZIP']                  

    },                                                                                                                    

    solicitor: {                                                                                                          

      label: 'Solicitors',                                                                                                

      description: 'Import fundraiser records',                                                                           

      endpoint: '/import/solicitor',                                                                                      

      requiredHeaders: ['Solicitor Name'],                                                                                

      optionalHeaders: ['Solicitor System ID']                                                                            

    },                                                                                                                    

    gift: {                                                                                                               

      label: 'Gifts',                                                                                                     

      description: 'Import one-time gifts',                                                                               

      endpoint: '/import/gift',                                                                                           

      requiredHeaders: ['Gift ID', 'Gift Date', 'Constituent ID'],                                                        

      optionalHeaders: ['Fund ID', 'Fund Split Amount', 'Solicitor Name', 'Solicitor Amount', 'Gift Type']                

    },                                                                                                                    

    'recurring-gift': {                                                                                                   

      label: 'Recurring Gifts',                                                                                           

      description: 'Import recurring/pledge gifts',                                                                       

      endpoint: '/import/recurring-gift',                                                                                 

      requiredHeaders: ['Gift ID', 'Constituent ID'],                                                                     

      optionalHeaders: ['Installment Amount', 'Installment Frequency', 'Status', 'Solicitor Name']                        

    }                                                                                                                     

  }                                                                                                                       

                                                                                                                          

  API methods:                                                                                                            

  - importByType(type, file) - dispatch to correct endpoint                                                               

  - getBatches(), getBatch(id)                                                                                            

  - downloadDonationsTemplate(), downloadContactsTemplate()                                                               

                                                                                                                          

  Import Page (src/pages/admin/ImportPage.tsx)                                                                            

                                                                                                                          

  Create a tab-based admin import UI:                                                                                     

                                                                                                                          

  1. Tab bar - Four tabs for constituent, solicitor, gift, recurring-gift                                                 

  2. Upload zone - Drag-and-drop file upload                                                                              

    - Accept only .csv files                                                                                              

    - Show file name/size when staged                                                                                     

    - "Remove" and "Import" buttons                                                                                       

  3. Result display after import:                                                                                         

    - Yellow banner if alreadyProcessed: "File Already Imported"                                                          

    - Green banner if SUCCEEDED: "Import Successful" with counts                                                          

    - Amber banner if SUCCEEDED_WITH_ERRORS: Show totals (created/updated/skipped/errors)                                 

    - Expandable error list showing row number, reason, and field                                                         

  4. CSV header reference - Show required (highlighted) and optional headers from config                                  

    - Warning note for Gifts: "Import Constituents first so contacts can be linked"                                       

  5. Import history - List of past ImportBatch records with status icons                                                  

                                                                                                                          

  Use TanStack Query for data fetching and cache invalidation after successful imports.                                   

                                                                                                                          

  ---                                                                                                                     

  IMPORT ORDER REQUIREMENT                                                                                                

                                                                                                                          

  Display in the UI that imports must happen in this order:                                                               

  1. Constituents (creates Contact records)                                                                               

  2. Solicitors (creates Solicitor records)                                                                               

  3. Gifts (links to existing Contacts and Solicitors)                                                                    

  4. Recurring Gifts (same as Gifts)                                                                                      

                                                                                                                          

  Gift imports will skip rows where the Constituent ID doesn't match an existing contact.                                 

                                                                                                                          

  ---                                                                                                                     

  KEY DESIGN PATTERNS                                                                                                     

                                                                                                                          

  1. SHA256 Idempotency - Same file can never be imported twice for same type                                             

  2. Row Grouping - Gift imports group by Gift ID since RE exports multiple rows per gift                                 

  3. Cents Storage - All amounts stored as integers (cents) to avoid floating point issues                                

  4. Merge-Only Updates - Never overwrite existing data with null values                                                  

  5. Normalized Matching - Solicitors matched by lowercase/trimmed name                                                   

  6. Factory Controller - Single handler factory for all four RE import types             

