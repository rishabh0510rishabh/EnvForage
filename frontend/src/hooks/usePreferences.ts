
// --- User Preferences Context & Hook ---
import { useState, useEffect, createContext, useContext } from 'react';

interface UserPreferences {
    theme: 'light' | 'dark' | 'system';
    locale: string;
    animationsEnabled: boolean;
}

interface PreferencesContextType {
    preferences: UserPreferences;
    updatePreferences: (newPrefs: Partial<UserPreferences>) => void;
}

const defaultPreferences: UserPreferences = {
    theme: 'system',
    locale: 'en-US',
    animationsEnabled: true,
};

const PreferencesContext = createContext<PreferencesContextType | undefined>(undefined);

export function usePreferencesStore() {
    const [preferences, setPreferences] = useState<UserPreferences>(defaultPreferences);
    const [isLoaded, setIsLoaded] = useState(false);

    useEffect(() => {
        try {
            const stored = localStorage.getItem('user-preferences');
            if (stored) {
                // eslint-disable-next-line react-hooks/set-state-in-effect
                setPreferences({ ...defaultPreferences, ...JSON.parse(stored) });
            }
        } catch (e) {
            console.error('Failed to load preferences from local storage', e);
        }
        setIsLoaded(true);
    }, []);

    const updatePreferences = (newPrefs: Partial<UserPreferences>) => {
        setPreferences((prev) => {
            const updated = { ...prev, ...newPrefs };
            try {
                localStorage.setItem('user-preferences', JSON.stringify(updated));
            } catch (e) {
                console.error('Failed to save preferences to local storage', e);
            }
            return updated;
        });
    };

    return { preferences, updatePreferences, isLoaded };
}

export const usePreferences = () => {
    const context = useContext(PreferencesContext);
    if (!context) {
        throw new Error('usePreferences must be used within a PreferencesProvider');
    }
    return context;
};
