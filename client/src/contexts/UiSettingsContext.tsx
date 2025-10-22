import React, { createContext, useContext, ReactNode } from "react";

interface UiSettingsContextType {
  // Placeholder for future UI settings
}

const UiSettingsContext = createContext<UiSettingsContextType | undefined>(undefined);

export const UiSettingsProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const value: UiSettingsContextType = {
    // Placeholder for future UI settings
  };

  return (
    <UiSettingsContext.Provider value={value}>
      {children}
    </UiSettingsContext.Provider>
  );
};

export const useUiSettings = () => {
  const context = useContext(UiSettingsContext);
  if (context === undefined) {
    throw new Error("useUiSettings must be used within a UiSettingsProvider");
  }
  return context;
};
