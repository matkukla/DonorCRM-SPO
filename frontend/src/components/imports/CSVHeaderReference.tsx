import type { REImportType } from "@/api/imports"

interface HeaderConfig {
  required: string[]
  optional: string[]
  reAliases: Record<string, string>
}

const RE_IMPORT_HEADERS: Record<REImportType, HeaderConfig> = {
  constituent: {
    required: ["first_name OR last_name OR organization_name"],
    optional: [
      "constituent_id",
      "email",
      "phone",
      "street_address",
      "city",
      "state",
      "postal_code",
      "country",
    ],
    reAliases: {
      constituent_id: "CnBio_ID",
      first_name: "CnBio_First_Name",
      last_name: "CnBio_Last_Name",
      organization_name: "CnBio_Org_Name",
      email: "CnAdrPrf_Email",
      phone: "CnPh_1_01_Phone_Number",
    },
  },
  solicitor: {
    required: ["raw_name (solicitor name)"],
    optional: ["external_solicitor_id"],
    reAliases: {
      raw_name: "CnSol_1_01_Name",
      external_solicitor_id: "CnSol_1_01_Solicit_ID",
    },
  },
  gift: {
    required: ["gift_id", "constituent_id", "amount"],
    optional: [
      "gift_date",
      "fund",
      "description",
      "solicitor_name",
      "credit_amount",
      "prayer_description",
    ],
    reAliases: {
      gift_id: "Gf_System_ID or Gf_ID",
      constituent_id: "Gf_CnBio_ID",
      amount: "Gf_Amount",
      gift_date: "Gf_Date",
      fund: "Gf_Fund",
      solicitor_name: "Gf_CnSol_1_01_Name",
      credit_amount: "Gf_CnSol_1_01_Amount",
    },
  },
  recurring_gift: {
    required: ["gift_id", "constituent_id", "amount"],
    optional: [
      "frequency",
      "start_date",
      "end_date",
      "status",
      "fund",
      "solicitor_name",
      "credit_amount",
    ],
    reAliases: {
      gift_id: "RG_ID or Gf_ID",
      constituent_id: "Gf_CnBio_ID",
      amount: "Gf_Amount",
      frequency: "Gf_Installment_Frequency",
      start_date: "Gf_Date",
      status: "Gf_Status",
      solicitor_name: "CnSol_1_01_Name",
    },
  },
} as const

interface CSVHeaderReferenceProps {
  importType: REImportType
}

export function CSVHeaderReference({ importType }: CSVHeaderReferenceProps) {
  const headers = RE_IMPORT_HEADERS[importType]

  return (
    <div className="bg-muted/50 rounded-lg p-3">
      <p className="text-xs font-medium text-muted-foreground mb-2">
        CSV Column Reference
      </p>
      <div className="space-y-2">
        {/* Required columns */}
        <div>
          <p className="text-xs font-medium mb-1">Required</p>
          <div className="space-y-0.5">
            {headers.required.map((col) => {
              const alias = headers.reAliases[col]
              return (
                <div key={col} className="flex items-center gap-1.5 text-xs">
                  <span className="h-1.5 w-1.5 rounded-full bg-green-500 shrink-0" />
                  <span className="text-foreground">{col}</span>
                  {alias && (
                    <span className="text-muted-foreground">({alias})</span>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Optional columns */}
        <div>
          <p className="text-xs font-medium mb-1">Optional</p>
          <div className="space-y-0.5">
            {headers.optional.map((col) => {
              const alias = headers.reAliases[col]
              return (
                <div key={col} className="flex items-center gap-1.5 text-xs">
                  <span className="h-1.5 w-1.5 rounded-full bg-gray-400 dark:bg-gray-500 shrink-0" />
                  <span className="text-foreground">{col}</span>
                  {alias && (
                    <span className="text-muted-foreground">({alias})</span>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
