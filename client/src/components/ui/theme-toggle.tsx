"use client"

import { Moon, Sun, Monitor } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useAppearance } from "@/contexts/AppearanceContext"
import { cn } from "@/lib/utils"

export function ThemeToggle() {
  const { theme, setTheme } = useAppearance()

  const options = [
    { value: "light", label: "Light", icon: Sun },
    { value: "dark", label: "Dark", icon: Moon },
    { value: "system", label: "System", icon: Monitor },
  ]

  return (
    <div className="flex flex-row gap-1 p-1 bg-card rounded-lg border border-border">
      {options.map(({ value, label, icon: Icon }) => (
        <Button
          key={value}
          variant="ghost"
          size="sm"
          onClick={() => setTheme(value as "light" | "dark" | "system")}
          className={cn(
            "flex items-center justify-center gap-2 h-8 px-3 transition-colors duration-150",
            "hover:bg-primary/10 hover:text-primary",
            "focus-visible:outline-none focus-visible:ring-0 focus-visible:ring-offset-0",
            theme === value
              ? "bg-primary/20 text-primary"
              : "text-muted-foreground"
          )}
        >
          <Icon className="h-4 w-4" />
          <span className="text-sm">{label}</span>
        </Button>
      ))}
    </div>
  )
}
