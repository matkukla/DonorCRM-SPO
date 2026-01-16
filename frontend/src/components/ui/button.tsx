import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/**
 * SPO Button System
 *
 * CRITICAL: Default CTA style is OUTLINE-FIRST (not solid)
 * - White background, red border, red text
 * - On hover: solid red background with white text
 * - No pill buttons (rounded-lg = 12px, not rounded-full)
 * - No heavy shadows
 */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        // Default: Outlined red CTA (SPO style)
        default:
          "border-2 border-primary bg-white text-primary hover:bg-primary hover:text-white tracking-wide",
        // Destructive: Solid red (use sparingly)
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        // Outline: Same as default (for compatibility)
        outline:
          "border-2 border-primary bg-white text-primary hover:bg-primary hover:text-white tracking-wide",
        // Secondary: Subtle neutral background
        secondary:
          "bg-secondary text-secondary-foreground border border-border hover:bg-secondary/80",
        // Ghost: No border, subtle hover
        ghost:
          "hover:bg-accent hover:text-accent-foreground",
        // Link: Red text, underline on hover
        link:
          "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2 rounded-lg text-sm",
        sm: "h-9 px-3 rounded-lg text-sm",
        lg: "h-12 px-6 rounded-lg text-base",
        icon: "h-10 w-10 rounded-lg",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
