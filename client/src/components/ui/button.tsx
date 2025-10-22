import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium ring-offset-background transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground shadow-lg shadow-primary/25 hover:bg-primary hover:shadow-primary/30",
        destructive: "bg-red-600 text-white shadow-lg shadow-red-600/25 hover:bg-red-700 hover:shadow-red-600/30",
        outline: "border border-border bg-transparent hover:bg-card text-foreground hover:text-card-foreground",
        secondary: "bg-secondary text-secondary-foreground shadow-md hover:bg-secondary/80",
        ghost: "text-foreground hover:bg-card/50 hover:text-card-foreground",
        link: "text-primary underline-offset-4 hover:underline",
        cta: "relative bg-primary text-primary-foreground shadow-lg shadow-primary/25 hover:shadow-primary/40",
        // Theme-aware brand variants
        "brand-primary": "theme-btn-primary",
        "brand-accent": "theme-btn-accent",
        "brand-success": "theme-btn-success",
        "brand-warning": "!bg-brand-amber text-white shadow-lg shadow-brand-amber/25 hover:!bg-orange-600 hover:shadow-orange-600/30 font-medium focus-visible:ring-brand-amber",
        "brand-outline": "theme-btn-outline",
        "brand-ghost": "theme-btn-ghost",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
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
        data-testid={(props as any)["data-testid"] || "button"}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
