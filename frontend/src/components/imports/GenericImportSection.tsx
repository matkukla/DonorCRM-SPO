import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { FileUp, Users, DollarSign } from "lucide-react"

export function GenericImportSection() {
  return (
    <div>
      <div className="mb-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <FileUp className="h-5 w-5 text-muted-foreground" />
          Generic CSV Import
        </h2>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="opacity-60">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center justify-between text-base">
              <span className="flex items-center gap-2">
                <Users className="h-4 w-4 text-muted-foreground" />
                Contacts
              </span>
              <Badge variant="secondary">Coming soon</Badge>
            </CardTitle>
            <CardDescription>Import contacts from any CSV format</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-20 flex items-center justify-center border-2 border-dashed border-border rounded-lg">
              <p className="text-sm text-muted-foreground">Available in a future update</p>
            </div>
          </CardContent>
        </Card>

        <Card className="opacity-60">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center justify-between text-base">
              <span className="flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-muted-foreground" />
                Donations
              </span>
              <Badge variant="secondary">Coming soon</Badge>
            </CardTitle>
            <CardDescription>Import donations from any CSV format</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-20 flex items-center justify-center border-2 border-dashed border-border rounded-lg">
              <p className="text-sm text-muted-foreground">Available in a future update</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
