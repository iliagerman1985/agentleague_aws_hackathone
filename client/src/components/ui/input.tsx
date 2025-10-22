import * as React from "react"

import { cn } from "@/lib/utils"

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          // Unified padding & focus styling (app-wide) – supports icon adornments via data-* attributes
          // Accept both data-adornment-*=true and presence-only attributes for robustness
          // Add no-base to opt out of global input styling in index.css
          "no-base flex w-full rounded-lg border border-input bg-muted/80 px-3 py-2.5 text-base md:text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200 hover:bg-muted focus-visible:bg-muted data-[adornment-start=true]:pl-10 data-[adornment-end=true]:pr-10 [&[data-adornment-start]]:pl-10 [&[data-adornment-end]]:pr-10",
          className
        )}
        ref={ref}
        data-testid={(props as any)["data-testid"] || "input"}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }
