"use client";

import React, { useState, useEffect } from "react";
import { offlineSyncService } from "../services/offlineSync";

export default function SyncStatusIndicator() {
    const [isOnline, setIsOnline] = useState<boolean>(true);
    const [isSyncing, setIsSyncing] = useState<boolean>(false);

    useEffect(() => {
        // Initial state
        if (typeof window !== "undefined") {
            setIsOnline(navigator.onLine);
        }

        const handleOnline = async () => {
            setIsOnline(true);
            setIsSyncing(true);
            try {
                await offlineSyncService.syncQueue();
            } catch (error) {
                console.error("Error during offline sync:", error);
            } finally {
                setIsSyncing(false);
            }
        };

        const handleOffline = () => {
            setIsOnline(false);
        };

        window.addEventListener("online", handleOnline);
        window.addEventListener("offline", handleOffline);

        // Attempt initial sync if online
        if (navigator.onLine) {
            handleOnline();
        }

        return () => {
            window.removeEventListener("online", handleOnline);
            window.removeEventListener("offline", handleOffline);
        };
    }, []);

    return (
        <div className="fixed bottom-4 right-4 p-3 rounded-lg shadow-lg flex items-center gap-2 bg-slate-800 text-white z-50 text-sm">
            {!isOnline && (
                <>
                    <span className="w-3 h-3 rounded-full bg-red-500 animate-pulse"></span>
                    <span>Offline Mode - Changes saved locally</span>
                </>
            )}
            
            {isOnline && isSyncing && (
                <>
                    <span className="w-3 h-3 rounded-full bg-yellow-500 animate-spin"></span>
                    <span>Syncing offline data...</span>
                </>
            )}
            
            {isOnline && !isSyncing && (
                <>
                    <span className="w-3 h-3 rounded-full bg-green-500"></span>
                    <span>Online - All changes synced</span>
                </>
            )}
        </div>
    );
}
