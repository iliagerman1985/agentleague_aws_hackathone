/** @type {import('tailwindcss').Config} */
export default {
  // Enable class-based dark mode
  darkMode: "class",
  content: [
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  prefix: "",
  theme: {
    // System-wide responsive breakpoints
    // Change md to 1200px so that widths below 1200px use the mobile layout
    screens: {
      sm: "640px",
      md: "1200px",
      lg: "1220px",
      xl: "1280px",
      "2xl": "1536px",
    },
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      fontFamily: {
        sans: ["Lexend", "system-ui", "sans-serif"],
      },
      colors: {
        brand: {
          // Dark Gaming Theme Colors - Based on screenshots
          primaryRed: "#E53E3E",     // Primary red/orange for buttons
          cardBlue: "#2D3748",       // Medium blue for cards
          darkBlue: "#1A202C",       // Dark blue for sidebar/secondary
          navy: "#171923",           // Very dark navy for main background
          teal: "#38B2AC",           // Teal accent color
          success: "#48BB78",        // Green for success states
          warning: "#ED8936",        // Orange for warnings
          textLight: "#F7FAFC",      // Light text
          textMuted: "#A0AEC0",      // Muted text

          // Legacy compatibility mappings
          orange: "#E53E3E",         // Map to primary red
          mint: "#48BB78",           // Map to success green
          cyan: "#38B2AC",           // Map to teal
          purple: "#805AD5",         // Purple accent
          amber: "#ED8936",          // Amber/warning
          slate: "#4A5568",          // Slate gray
          lightBlue: "#2D3748",      // Map to card blue
          warmGray: "#2D3748",       // Map to card blue
          primaryTeal: "#0891B2",           // Teal primary
          accentOrange: "#EA580C",          // Orange accent

        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        "button-primary": "hsl(var(--button-primary))",
        "button-primary-foreground": "hsl(var(--button-primary-foreground))",
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        // Standardized app-wide border radius
        'app-sm': '0.5rem',    // 8px - small elements like badges, pills
        'app-md': '0.75rem',   // 12px - buttons, inputs, small cards
        'app-lg': '1rem',      // 16px - cards, panels, dialogs
        'app-xl': '1.25rem',   // 20px - large containers, main panels
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "gradient-x": {
          "0%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
          "100%": { backgroundPosition: "0% 50%" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-700px 0" },
          "100%": { backgroundPosition: "700px 0" },
        },
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(14,165,233,0.4)" },
          "50%": { boxShadow: "0 0 0 8px rgba(14,165,233,0.1)" },
        },
        starTravel: {
          "0%": {
            transform: "translate(0px, 0px) scale(0.5)",
            opacity: "0.3"
          },
          "10%": {
            transform: "translate(200px, -150px) scale(0.8)",
            opacity: "0.6"
          },
          "25%": {
            transform: "translate(-300px, 200px) scale(1.2)",
            opacity: "0.8"
          },
          "40%": {
            transform: "translate(400px, 300px) scale(0.7)",
            opacity: "0.5"
          },
          "55%": {
            transform: "translate(-250px, -200px) scale(1.1)",
            opacity: "0.7"
          },
          "70%": {
            transform: "translate(350px, -250px) scale(0.9)",
            opacity: "0.4"
          },
          "85%": {
            transform: "translate(-400px, 100px) scale(1.3)",
            opacity: "0.6"
          },
          "100%": {
            transform: "translate(0px, 0px) scale(0.5)",
            opacity: "0.3"
          },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-20px)" },
        },
        colorShift: {
          "0%, 100%": { filter: "hue-rotate(0deg) saturate(1)" },
          "25%": { filter: "hue-rotate(90deg) saturate(1.2)" },
          "50%": { filter: "hue-rotate(180deg) saturate(0.8)" },
          "75%": { filter: "hue-rotate(270deg) saturate(1.1)" },
        },
        gentleGlow: {
          "0%, 80%, 100%": {
            transform: "scale(1)",
            opacity: "1"
          },
          "90%": {
            transform: "scale(1.02)",
            opacity: "0.9"
          },
        },
        slideOut: {
          "0%, 70%": { transform: "translateX(0) scale(1)", opacity: "1" },
          "85%": { transform: "translateX(60px) scale(0.95)", opacity: "0.7" },
          "95%": { transform: "translateX(100px) scale(0.9)", opacity: "0.3" },
          "100%": { transform: "translateX(0) scale(1)", opacity: "1" },
        },
        slideDown: {
          "0%, 70%": { transform: "translateY(0) scale(1)", opacity: "1" },
          "85%": { transform: "translateY(40px) scale(0.95)", opacity: "0.7" },
          "95%": { transform: "translateY(80px) scale(0.9)", opacity: "0.3" },
          "100%": { transform: "translateY(0) scale(1)", opacity: "1" },
        },
        slowSpin: {
          "0%, 70%": { transform: "rotate(0deg) scale(1)" },
          "85%": { transform: "rotate(180deg) scale(1.05)" },
          "95%": { transform: "rotate(360deg) scale(0.95)" },
          "100%": { transform: "rotate(0deg) scale(1)" },
        },
        shrinkRestore: {
          "0%, 70%": { transform: "scale(1)", opacity: "1" },
          "85%": { transform: "scale(0.7)", opacity: "0.8" },
          "95%": { transform: "scale(0.5)", opacity: "0.6" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
        wobble: {
          "0%, 100%": { transform: "rotate(0deg) scale(1)" },
          "15%": { transform: "rotate(-5deg) scale(1.05)" },
          "30%": { transform: "rotate(3deg) scale(0.95)" },
          "45%": { transform: "rotate(-3deg) scale(1.02)" },
          "60%": { transform: "rotate(2deg) scale(0.98)" },
          "75%": { transform: "rotate(-1deg) scale(1.01)" },
        },
        flash: {
          "0%, 50%, 100%": { opacity: "1" },
          "25%, 75%": { opacity: "0.3" },
        },
        zoomPulse: {
          "0%, 100%": { transform: "scale(1)" },
          "50%": { transform: "scale(1.15)" },
        },
        shake: {
          "0%, 100%": { transform: "translateX(0)" },
          "10%, 30%, 50%, 70%, 90%": { transform: "translateX(-2px)" },
          "20%, 40%, 60%, 80%": { transform: "translateX(2px)" },
        },
        dramaticIn: {
          "0%": { opacity: "0", transform: "perspective(1000px) translateY(20px) rotateX(8deg) scale(0.96)", filter: "blur(4px)" },
          "100%": { opacity: "1", transform: "perspective(1000px) translateY(0) rotateX(0) scale(1)", filter: "blur(0)" }
        },
        dramaticOut: {
          "0%": { opacity: "1", transform: "perspective(1000px) translateY(0) rotateX(0) scale(1)", filter: "blur(0)" },
          "100%": { opacity: "0", transform: "perspective(1000px) translateY(-16px) rotateX(-6deg) scale(0.98)", filter: "blur(3px)" }
        },
        loginPop: {
          "0%": { opacity: "0", transform: "scale(0.6)", filter: "blur(6px)" },
          "60%": { opacity: "1", transform: "scale(1.08)", filter: "blur(0)" },
          "100%": { opacity: "1", transform: "scale(1)", filter: "blur(0)" }
        },
        modalFlipIn: {
          "0%": { opacity: "0", transform: "perspective(1200px) rotateX(-10deg) translateX(-50%) translateY(calc(-50% - 8px)) scale(0.96)" },
          "100%": { opacity: "1", transform: "perspective(1200px) rotateX(0) translateX(-50%) translateY(-50%) scale(1)" }
        },
        modalFlipOut: {
          "0%": { opacity: "1", transform: "perspective(1200px) rotateX(0) translateX(-50%) translateY(-50%) scale(1)" },
          "100%": { opacity: "0", transform: "perspective(1200px) rotateX(6deg) translateX(-50%) translateY(calc(-50% + 8px)) scale(0.98)" }
        }
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "gradient-x": "gradient-x 3s ease-in-out infinite",
        shimmer: "shimmer 2s linear infinite",
        pulseGlow: "pulseGlow 2.5s ease-in-out infinite",
        starTravel: "starTravel 30s ease-in-out infinite",
        float: "float 6s ease-in-out infinite",
        colorShift: "colorShift 8s ease-in-out infinite",
        gentleGlow: "gentleGlow 8s ease-in-out infinite",
        slideOut: "slideOut 5s ease-in-out",
        slideDown: "slideDown 5s ease-in-out",
        slowSpin: "slowSpin 6s ease-in-out",
        shrinkRestore: "shrinkRestore 4s ease-in-out",
        wobble: "wobble 3s ease-in-out",
        flash: "flash 2s ease-in-out",
        zoomPulse: "zoomPulse 3s ease-in-out",
        shake: "shake 2s ease-in-out",
        dramaticIn: "dramaticIn 700ms cubic-bezier(.2,.9,.2,1) both",
        dramaticOut: "dramaticOut 620ms cubic-bezier(.2,.9,.2,1) both",
        modalFlipIn: "modalFlipIn 780ms cubic-bezier(.2,.9,.2,1) both",
        modalFlipOut: "modalFlipOut 640ms cubic-bezier(.2,.9,.2,1) both",
        loginPop: "loginPop 320ms cubic-bezier(.2,.9,.2,1) both",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}