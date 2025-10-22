/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./*.html", "./src/**/*.{html,js}"],
  theme: {
    extend: {
      colors: {
        'primary': '#0cf2cc',
        'background-color': '#121212',
        'text-primary': '#E0E0E0',
        'text-secondary': '#A0A0A0',
        'accent-color': '#0cf2cc',
        'card-background': '#1E1E1E',
        'button-primary-hover': '#09c2a3',
      },
      fontFamily: {
        'space-grotesk': ['Space Grotesk', 'sans-serif'],
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite',
        'slide-up': 'slideInUp 0.8s ease-out forwards',
        'slide-left': 'slideInLeft 0.8s ease-out forwards',
        'slide-right': 'slideInRight 0.8s ease-out forwards',
        'pulse-custom': 'pulse 2s ease-in-out infinite',
        'rotate-slow': 'rotate 20s linear infinite',
        'fade-scale': 'fadeInScale 0.6s ease-out forwards',
        'gradient-shift': 'gradientShift 3s ease infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        glow: {
          '0%, 100%': { boxShadow: '0 0 20px rgba(12, 242, 204, 0.3)' },
          '50%': { boxShadow: '0 0 40px rgba(12, 242, 204, 0.6)' },
        },
        slideInUp: {
          from: {
            opacity: '0',
            transform: 'translateY(50px)',
          },
          to: {
            opacity: '1',
            transform: 'translateY(0)',
          },
        },
        slideInLeft: {
          from: {
            opacity: '0',
            transform: 'translateX(-50px)',
          },
          to: {
            opacity: '1',
            transform: 'translateX(0)',
          },
        },
        slideInRight: {
          from: {
            opacity: '0',
            transform: 'translateX(50px)',
          },
          to: {
            opacity: '1',
            transform: 'translateX(0)',
          },
        },
        fadeInScale: {
          from: {
            opacity: '0',
            transform: 'scale(0.8)',
          },
          to: {
            opacity: '1',
            transform: 'scale(1)',
          },
        },
        gradientShift: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
      },
    },
  },
  plugins: [],
}
