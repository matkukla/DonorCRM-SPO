import { Card, CardContent } from "@/components/ui/card"
import { ExternalLink } from "lucide-react"

const resources = [
  {
    title: "SPO MPD Handbook",
    description:
      "Comprehensive guide to Ministry Partner Development — strategies, scripts, and best practices for building your support team.",
    href: "https://spo.org/mpd",
  },
]

export default function LinksPage() {
  return (
    <div className="max-w-2xl mx-auto space-y-6 p-6">
      <h1 className="text-2xl font-bold">MPD Resources</h1>

      {resources.map((resource) => (
        <Card key={resource.href}>
          <CardContent className="flex items-start justify-between gap-4 pt-6">
            <div className="space-y-1">
              <h2 className="text-base font-semibold">{resource.title}</h2>
              <p className="text-sm text-muted-foreground">
                {resource.description}
              </p>
            </div>
            <a
              href={resource.href}
              target="_blank"
              rel="noopener noreferrer"
              className="shrink-0 inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline cursor-pointer"
            >
              Visit
              <ExternalLink className="h-4 w-4" />
            </a>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
