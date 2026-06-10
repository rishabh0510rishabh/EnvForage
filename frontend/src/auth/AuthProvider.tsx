
// --- Comprehensive JWT Authentication Provider ---
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

interface User {
    id: string;
    email: string;
    role: string;
}

interface AuthContextType {
    user: User | null;
    accessToken: string | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (token: string, user: User) => void;
    logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const authApiClient = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL,
    withCredentials: true, // Crucial for refresh token HttpOnly cookies
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [accessToken, setAccessToken] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    const refreshTokens = useCallback(async () => {
        try {
            // The refresh token should be in an HttpOnly cookie
            const response = await authApiClient.post('/auth/refresh');
            const { access_token, user_data } = response.data;
            setAccessToken(access_token);
            setUser(user_data);
            return access_token;
        } catch (error) {
            console.error("Token refresh failed", error);
            setAccessToken(null);
            setUser(null);
            return null;
        }
    }, []);

    useEffect(() => {
        // Initial load validation
        refreshTokens().finally(() => setIsLoading(false));
        
        // Background refresh loop (e.g. 14 minutes for a 15 min token)
        const interval = setInterval(() => {
            if (accessToken) refreshTokens();
        }, 14 * 60 * 1000);
        
        return () => clearInterval(interval);
    }, [refreshTokens, accessToken]);

    // Axios interceptor to attach access token and handle 401s globally
    useEffect(() => {
        const reqInterceptor = authApiClient.interceptors.request.use(config => {
            if (accessToken && config.headers) {
                config.headers.Authorization = `Bearer ${accessToken}`;
            }
            return config;
        });

        const resInterceptor = authApiClient.interceptors.response.use(
            response => response,
            async error => {
                const prevRequest = error?.config;
                if (error?.response?.status === 401 && !prevRequest?.sent) {
                    prevRequest.sent = true;
                    const newAccessToken = await refreshTokens();
                    if (newAccessToken) {
                        prevRequest.headers.Authorization = `Bearer ${newAccessToken}`;
                        return authApiClient(prevRequest);
                    }
                }
                return Promise.reject(error);
            }
        );

        return () => {
            authApiClient.interceptors.request.eject(reqInterceptor);
            authApiClient.interceptors.response.eject(resInterceptor);
        };
    }, [accessToken, refreshTokens]);

    const login = (token: string, userData: User) => {
        setAccessToken(token);
        setUser(userData);
    };

    const logout = async () => {
        try {
            await authApiClient.post('/auth/logout');
        } finally {
            setAccessToken(null);
            setUser(null);
        }
    };

    return (
        <AuthContext.Provider value={{ user, accessToken, isAuthenticated: !!user, isLoading, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) throw new Error("useAuth must be used within an AuthProvider");
    return context;
};
