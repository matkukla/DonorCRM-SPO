import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"

interface CTASectionProps {
  /**
   * Headline text
   */
  headline: string
  /**
   * Optional description
   */
  description?: string
  /**
   * CTA button text
   */
  ctaText: string
  /**
   * CTA click handler
   */
  onCTAClick?: () => void
  /**
   * CTA href (if link)
   */
  ctaHref?: string
  className?: string
}

/**
 * CTASection Component
 *
 * SPO Style:
 * - Muted background band
 * - Headline + primary outline button
 * - Centered, clean layout
 */
export function CTASection({
  headline,
  description,
  ctaText,
  onCTAClick,
  ctaHref,
  className,
}: CTASectionProps) {
  return (
    <Section muted className={cn(className)}>
      <Container>
        <div className="text-center space-y-6">
          <div className="space-y-4">
            <h2 className="text-3xl md:text-4xl font-semibold tracking-tight">
              {headline}
            </h2>
            {description && (
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                {description}
              </p>
            )}
          </div>
          <Button size="lg" onClick={onCTAClick} asChild={!!ctaHref}>
            {ctaHref ? <a href={ctaHref}>{ctaText}</a> : ctaText}
          </Button>
        </div>
      </Container>
    </Section>
  )
}
