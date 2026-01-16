import * as React from "react"
import { cn } from "@/lib/utils"

interface SectionProps extends React.HTMLAttributes<HTMLElement> {
  children: React.ReactNode
  /**
   * Size variant for section padding
   * - default: py-12 md:py-16
   * - large: py-16 md:py-20 (for hero sections)
   */
  size?: "default" | "large"
  /**
   * Use muted background
   */
  muted?: boolean
}

/**
 * Section Component
 * SPO Style: Generous padding, sections should "breathe"
 */
export function Section({
  className,
  children,
  size = "default",
  muted = false,
  ...props
}: SectionProps) {
  return (
    <section
      className={cn(
        size === "large" ? "py-16 md:py-20" : "py-12 md:py-16",
        muted && "bg-muted",
        className
      )}
      {...props}
    >
      {children}
    </section>
  )
}
