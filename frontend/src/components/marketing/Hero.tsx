import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"

interface HeroProps {
  /**
   * Main headline text
   */
  headline: string
  /**
   * Supporting description text
   */
  description: string
  /**
   * Primary CTA button text
   */
  primaryCTA?: {
    text: string
    href?: string
    onClick?: () => void
  }
  /**
   * Secondary CTA button text
   */
  secondaryCTA?: {
    text: string
    href?: string
    onClick?: () => void
  }
  /**
   * Image URL for the right side
   */
  imageUrl?: string
  /**
   * Image alt text
   */
  imageAlt?: string
  /**
   * Optional overlay text on image
   */
  imageOverlayText?: string
  className?: string
}

/**
 * Hero Component (DonateHero style)
 *
 * SPO Style:
 * - Two-column layout (desktop)
 * - Left: text + stacked outline CTAs
 * - Right: large image with optional overlay text
 * - Mobile: stack vertically (content first)
 */
export function Hero({
  headline,
  description,
  primaryCTA,
  secondaryCTA,
  imageUrl,
  imageAlt = "Hero image",
  imageOverlayText,
  className,
}: HeroProps) {
  return (
    <Section size="large" className={cn(className)}>
      <Container>
        <div className="grid gap-12 lg:grid-cols-2 lg:gap-16 items-center">
          {/* Content Column */}
          <div className="space-y-8">
            <div className="space-y-4">
              <h1 className="text-4xl md:text-5xl font-semibold tracking-tight text-foreground">
                {headline}
              </h1>
              <p className="text-lg leading-8 text-muted-foreground max-w-prose">
                {description}
              </p>
            </div>

            {/* CTA Buttons - Stacked with generous spacing */}
            {(primaryCTA || secondaryCTA) && (
              <div className="flex flex-col sm:flex-row gap-4">
                {primaryCTA && (
                  <Button
                    size="lg"
                    onClick={primaryCTA.onClick}
                    asChild={!!primaryCTA.href}
                  >
                    {primaryCTA.href ? (
                      <a href={primaryCTA.href}>{primaryCTA.text}</a>
                    ) : (
                      primaryCTA.text
                    )}
                  </Button>
                )}
                {secondaryCTA && (
                  <Button
                    variant="secondary"
                    size="lg"
                    onClick={secondaryCTA.onClick}
                    asChild={!!secondaryCTA.href}
                  >
                    {secondaryCTA.href ? (
                      <a href={secondaryCTA.href}>{secondaryCTA.text}</a>
                    ) : (
                      secondaryCTA.text
                    )}
                  </Button>
                )}
              </div>
            )}
          </div>

          {/* Image Column */}
          {imageUrl && (
            <div className="relative overflow-hidden rounded-lg">
              <img
                src={imageUrl}
                alt={imageAlt}
                className="w-full h-auto object-cover aspect-[4/3]"
              />
              {/* Image Overlay */}
              {imageOverlayText && (
                <div className="absolute inset-0 bg-black/60 flex items-center justify-center p-8">
                  <p className="text-white text-center text-2xl md:text-3xl font-semibold uppercase tracking-wide">
                    {imageOverlayText}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </Container>
    </Section>
  )
}
