import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Database } from "lucide-react"
import { REImportTab } from "./REImportTab"

export function REImportSection() {
  return (
    <div>
      <div className="mb-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Database className="h-5 w-5 text-muted-foreground" />
          Raiser's Edge Imports
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Import data exported from Raiser's Edge. Follow the recommended order for best results.
        </p>
      </div>

      <Tabs defaultValue="constituent">
        <TabsList className="w-full justify-start">
          <TabsTrigger value="constituent">1. Constituents</TabsTrigger>
          <TabsTrigger value="solicitor">2. Solicitors</TabsTrigger>
          <TabsTrigger value="gift">3. Gifts</TabsTrigger>
          <TabsTrigger value="recurring_gift">4. Recurring Gifts</TabsTrigger>
        </TabsList>

        <TabsContent value="constituent" className="mt-4">
          <REImportTab
            importType="constituent"
            stepNumber={1}
            totalSteps={4}
            title="Constituents"
            description="Import or update donor contact records"
          />
        </TabsContent>

        <TabsContent value="solicitor" className="mt-4">
          <REImportTab
            importType="solicitor"
            stepNumber={2}
            totalSteps={4}
            title="Solicitors"
            description="Import fundraiser/solicitor records and auto-link to users"
          />
        </TabsContent>

        <TabsContent value="gift" className="mt-4">
          <REImportTab
            importType="gift"
            stepNumber={3}
            totalSteps={4}
            title="Gifts"
            description="Import one-time gift records with solicitor credits"
          />
        </TabsContent>

        <TabsContent value="recurring_gift" className="mt-4">
          <REImportTab
            importType="recurring_gift"
            stepNumber={4}
            totalSteps={4}
            title="Recurring Gifts"
            description="Import recurring gift/pledge records"
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}
