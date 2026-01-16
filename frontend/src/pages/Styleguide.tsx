import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Hero } from "@/components/marketing/Hero"
import { FeatureGrid } from "@/components/marketing/FeatureGrid"
import { CTASection } from "@/components/marketing/CTASection"

/**
 * Styleguide Page
 *
 * Displays all design system components for validation.
 * This is the Definition of Done for Phases 1-8.
 *
 * Must display:
 * - Typography samples (H1-H3, body, muted)
 * - Buttons (all variants + sizes + disabled + hover states)
 * - Inputs + error state
 * - Cards
 * - Section + Container examples
 * - DonateHero example
 */
export default function Styleguide() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border">
        <Container>
          <div className="flex h-16 items-center justify-between">
            <h1 className="text-xl font-semibold">DonorCRM Styleguide</h1>
            <Button size="sm">Primary CTA</Button>
          </div>
        </Container>
      </header>

      {/* Typography Section */}
      <Section>
        <Container>
          <div className="space-y-8">
            <div>
              <h2 className="text-2xl font-semibold mb-6 pb-2 border-b border-border">
                Typography
              </h2>
              <div className="space-y-6">
                <div>
                  <p className="text-sm text-muted-foreground mb-2">
                    H1: text-4xl md:text-5xl font-semibold tracking-tight
                  </p>
                  <h1 className="text-4xl md:text-5xl font-semibold tracking-tight">
                    Headline One
                  </h1>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-2">
                    H2: text-3xl md:text-4xl font-semibold tracking-tight
                  </p>
                  <h2 className="text-3xl md:text-4xl font-semibold tracking-tight">
                    Headline Two
                  </h2>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-2">
                    H3: text-2xl font-semibold
                  </p>
                  <h3 className="text-2xl font-semibold">Headline Three</h3>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-2">
                    Body: text-base leading-7
                  </p>
                  <p className="text-base leading-7 max-w-prose">
                    This is body text with comfortable line height. The quick
                    brown fox jumps over the lazy dog. Lorem ipsum dolor sit
                    amet, consectetur adipiscing elit. Sed do eiusmod tempor
                    incididunt ut labore et dolore magna aliqua.
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-2">
                    Large Body: text-lg leading-8
                  </p>
                  <p className="text-lg leading-8 max-w-prose">
                    This is large body text for marketing content. The quick
                    brown fox jumps over the lazy dog. Lorem ipsum dolor sit
                    amet, consectetur adipiscing elit.
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-2">
                    Muted: text-sm text-muted-foreground
                  </p>
                  <p className="text-sm text-muted-foreground">
                    This is muted helper text for secondary information.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </Container>
      </Section>

      {/* Button Section */}
      <Section muted>
        <Container>
          <div className="space-y-8">
            <h2 className="text-2xl font-semibold mb-6 pb-2 border-b border-border">
              Buttons
            </h2>

            {/* Button Variants */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium">Variants</h3>
              <div className="flex flex-wrap gap-4 items-center">
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Default (Outline)</p>
                  <Button>Primary CTA</Button>
                </div>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Secondary</p>
                  <Button variant="secondary">Secondary</Button>
                </div>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Outline</p>
                  <Button variant="outline">Outline</Button>
                </div>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Ghost</p>
                  <Button variant="ghost">Ghost</Button>
                </div>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Link</p>
                  <Button variant="link">Link</Button>
                </div>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Destructive</p>
                  <Button variant="destructive">Destructive</Button>
                </div>
              </div>
            </div>

            {/* Button Sizes */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium">Sizes</h3>
              <div className="flex flex-wrap gap-4 items-end">
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Small (h-9)</p>
                  <Button size="sm">Small</Button>
                </div>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Default (h-10)</p>
                  <Button size="default">Default</Button>
                </div>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Large (h-12)</p>
                  <Button size="lg">Large CTA</Button>
                </div>
              </div>
            </div>

            {/* Button States */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium">States</h3>
              <div className="flex flex-wrap gap-4 items-center">
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Normal</p>
                  <Button>Normal</Button>
                </div>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Hover (demo)</p>
                  <Button className="bg-primary text-white">Hover State</Button>
                </div>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Disabled</p>
                  <Button disabled>Disabled</Button>
                </div>
              </div>
            </div>
          </div>
        </Container>
      </Section>

      {/* Form Elements Section */}
      <Section>
        <Container>
          <div className="space-y-8">
            <h2 className="text-2xl font-semibold mb-6 pb-2 border-b border-border">
              Form Elements
            </h2>

            <div className="grid gap-8 md:grid-cols-2">
              {/* Input States */}
              <div className="space-y-4">
                <h3 className="text-lg font-medium">Input</h3>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="normal">Normal Input</Label>
                    <Input id="normal" placeholder="Enter text..." />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="filled">Filled Input</Label>
                    <Input id="filled" defaultValue="john@example.com" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="disabled">Disabled Input</Label>
                    <Input id="disabled" disabled placeholder="Disabled..." />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="error" className="text-destructive">
                      Error State
                    </Label>
                    <Input
                      id="error"
                      className="border-destructive focus-visible:ring-destructive"
                      defaultValue="invalid-email"
                    />
                    <p className="text-sm text-destructive">
                      Please enter a valid email address.
                    </p>
                  </div>
                </div>
              </div>

              {/* Labels */}
              <div className="space-y-4">
                <h3 className="text-lg font-medium">Labels</h3>
                <div className="space-y-4">
                  <div>
                    <Label>Default Label</Label>
                  </div>
                  <div>
                    <Label className="text-destructive">Error Label</Label>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Muted Label</Label>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Container>
      </Section>

      {/* Cards Section */}
      <Section muted>
        <Container>
          <div className="space-y-8">
            <h2 className="text-2xl font-semibold mb-6 pb-2 border-b border-border">
              Cards
            </h2>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              <Card>
                <CardHeader>
                  <CardTitle>Card Title</CardTitle>
                  <CardDescription>
                    Card description goes here with supporting text.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm">
                    This is the card content area. Cards use subtle borders
                    instead of heavy shadows.
                  </p>
                </CardContent>
                <CardFooter>
                  <Button size="sm">Action</Button>
                </CardFooter>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Donation Summary</CardTitle>
                  <CardDescription>January 2024</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-semibold">$12,450</div>
                  <p className="text-sm text-muted-foreground">
                    +12% from last month
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Contact Card</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <p className="font-medium">John Doe</p>
                  <p className="text-sm text-muted-foreground">
                    john.doe@example.com
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Total Given: $5,000
                  </p>
                </CardContent>
                <CardFooter className="gap-2">
                  <Button size="sm">View</Button>
                  <Button size="sm" variant="secondary">
                    Edit
                  </Button>
                </CardFooter>
              </Card>
            </div>
          </div>
        </Container>
      </Section>

      {/* Layout Primitives Section */}
      <Section>
        <Container>
          <div className="space-y-8">
            <h2 className="text-2xl font-semibold mb-6 pb-2 border-b border-border">
              Layout Primitives
            </h2>

            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium mb-4">Container</h3>
                <div className="border border-dashed border-border rounded-lg p-4">
                  <p className="text-sm text-muted-foreground">
                    Container: mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8
                  </p>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-medium mb-4">Section Variants</h3>
                <div className="space-y-4">
                  <div className="border border-dashed border-border rounded-lg">
                    <div className="py-12 md:py-16 px-4 text-center">
                      <p className="text-sm text-muted-foreground">
                        Section (default): py-12 md:py-16
                      </p>
                    </div>
                  </div>
                  <div className="border border-dashed border-border rounded-lg">
                    <div className="py-16 md:py-20 px-4 text-center bg-muted rounded-lg">
                      <p className="text-sm text-muted-foreground">
                        Section (large, muted): py-16 md:py-20 bg-muted
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Container>
      </Section>

      {/* Marketing Components Section */}
      <Section muted>
        <Container>
          <h2 className="text-2xl font-semibold mb-6 pb-2 border-b border-border">
            Marketing Components
          </h2>
        </Container>
      </Section>

      {/* Hero Example */}
      <Hero
        headline="Support Our Mission"
        description="Join thousands of donors making a difference in the lives of those we serve. Your contribution helps us continue our important work in the community."
        primaryCTA={{
          text: "Donate Now",
          onClick: () => console.log("Donate clicked"),
        }}
        secondaryCTA={{
          text: "Learn More",
          onClick: () => console.log("Learn more clicked"),
        }}
        imageUrl="https://images.unsplash.com/photo-1559027615-cd4628902d4a?w=800&h=600&fit=crop"
        imageAlt="People helping in community"
        imageOverlayText="Making a Difference Together"
      />

      {/* Feature Grid Example */}
      <FeatureGrid
        headline="Why Choose DonorCRM"
        description="Everything you need to manage donor relationships effectively"
        features={[
          {
            title: "Contact Management",
            description:
              "Keep track of all your donors, prospects, and supporters in one central place.",
          },
          {
            title: "Donation Tracking",
            description:
              "Record and analyze donations with detailed reporting and insights.",
          },
          {
            title: "Pledge Management",
            description:
              "Monitor recurring pledges and get alerts for late payments.",
          },
          {
            title: "Task Reminders",
            description:
              "Never miss a follow-up with built-in task management and reminders.",
          },
          {
            title: "Email Notifications",
            description:
              "Stay informed with automated alerts for important events.",
          },
          {
            title: "Reports & Analytics",
            description:
              "Gain insights with comprehensive reporting and dashboard views.",
          },
        ]}
      />

      {/* CTA Section Example */}
      <CTASection
        headline="Ready to Get Started?"
        description="Join hundreds of organizations using DonorCRM to manage their donor relationships."
        ctaText="Start Free Trial"
        onCTAClick={() => console.log("CTA clicked")}
      />

      {/* Color Tokens Section */}
      <Section>
        <Container>
          <div className="space-y-8">
            <h2 className="text-2xl font-semibold mb-6 pb-2 border-b border-border">
              Color Tokens
            </h2>

            <div className="grid gap-4 md:grid-cols-4">
              <div className="space-y-2">
                <div className="h-16 rounded-lg bg-primary"></div>
                <p className="text-sm font-medium">Primary</p>
                <p className="text-xs text-muted-foreground">#D11F3A</p>
              </div>
              <div className="space-y-2">
                <div className="h-16 rounded-lg bg-secondary border"></div>
                <p className="text-sm font-medium">Secondary</p>
                <p className="text-xs text-muted-foreground">Neutral</p>
              </div>
              <div className="space-y-2">
                <div className="h-16 rounded-lg bg-muted"></div>
                <p className="text-sm font-medium">Muted</p>
                <p className="text-xs text-muted-foreground">Background</p>
              </div>
              <div className="space-y-2">
                <div className="h-16 rounded-lg bg-destructive"></div>
                <p className="text-sm font-medium">Destructive</p>
                <p className="text-xs text-muted-foreground">Error</p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-4">
              <div className="space-y-2">
                <div className="h-16 rounded-lg bg-background border"></div>
                <p className="text-sm font-medium">Background</p>
                <p className="text-xs text-muted-foreground">White</p>
              </div>
              <div className="space-y-2">
                <div className="h-16 rounded-lg bg-foreground"></div>
                <p className="text-sm font-medium">Foreground</p>
                <p className="text-xs text-muted-foreground">Near-black</p>
              </div>
              <div className="space-y-2">
                <div className="h-16 rounded-lg border-2 border-border"></div>
                <p className="text-sm font-medium">Border</p>
                <p className="text-xs text-muted-foreground">Subtle gray</p>
              </div>
              <div className="space-y-2">
                <div className="h-16 rounded-lg ring-2 ring-ring ring-offset-2"></div>
                <p className="text-sm font-medium">Ring (Focus)</p>
                <p className="text-xs text-muted-foreground">Primary red</p>
              </div>
            </div>
          </div>
        </Container>
      </Section>

      {/* Footer */}
      <footer className="border-t border-border py-8">
        <Container>
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-sm text-muted-foreground">
              DonorCRM Design System - SPO Style
            </p>
            <div className="flex gap-4">
              <Button variant="link" size="sm">
                Documentation
              </Button>
              <Button variant="link" size="sm">
                Components
              </Button>
              <Button variant="link" size="sm">
                GitHub
              </Button>
            </div>
          </div>
        </Container>
      </footer>
    </div>
  )
}
