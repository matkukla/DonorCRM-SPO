import * as React from "react"
import { cn } from "@/lib/utils"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"

interface Feature {
  /**
   * Feature title
   */
  title: string
  /**
   * Feature description
   */
  description: string
  /**
   * Optional icon component
   */
  icon?: React.ReactNode
}

interface FeatureGridProps {
  /**
   * Section headline
   */
  headline?: string
  /**
   * Section description
   */
  description?: string
  /**
   * Features to display (3-6 recommended)
   */
  features: Feature[]
  /**
   * Number of columns (2, 3, or 4)
   */
  columns?: 2 | 3 | 4
  className?: string
}

/**
 * FeatureGrid Component
 *
 * SPO Style:
 * - Subtle borders, minimal shadow
 * - 3-6 feature cards
 * - Clean, calm aesthetic
 */
export function FeatureGrid({
  headline,
  description,
  features,
  columns = 3,
  className,
}: FeatureGridProps) {
  const gridCols = {
    2: "md:grid-cols-2",
    3: "md:grid-cols-2 lg:grid-cols-3",
    4: "md:grid-cols-2 lg:grid-cols-4",
  }

  return (
    <Section className={cn(className)}>
      <Container>
        {/* Section Header */}
        {(headline || description) && (
          <div className="text-center mb-12 space-y-4">
            {headline && (
              <h2 className="text-3xl md:text-4xl font-semibold tracking-tight">
                {headline}
              </h2>
            )}
            {description && (
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                {description}
              </p>
            )}
          </div>
        )}

        {/* Feature Cards */}
        <div className={cn("grid gap-6", gridCols[columns])}>
          {features.map((feature, index) => (
            <div
              key={index}
              className="p-6 rounded-lg border border-border bg-card"
            >
              {feature.icon && (
                <div className="mb-4 text-primary">{feature.icon}</div>
              )}
              <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
              <p className="text-muted-foreground leading-7">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </Container>
    </Section>
  )
}
