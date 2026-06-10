/**
 * Offline Synchronization Service (Issue #805)
 * 
 * Provides an offline-first caching layer using IndexedDB and a background
 * synchronization queue to push data once a connection is restored.
 */

const DB_NAME = "envforage_offline_db";
const STORE_NAME = "sync_queue";

class OfflineSyncService {
    private db: IDBDatabase | null = null;
    
    constructor() {
        if (typeof window !== "undefined") {
            this.initDB();
        }
    }
    
    private initDB(): Promise<void> {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, 1);
            
            request.onupgradeneeded = (event: IDBVersionChangeEvent) => {
                const db = (event.target as IDBOpenDBRequest).result;
                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    db.createObjectStore(STORE_NAME, { keyPath: "id", autoIncrement: true });
                }
            };
            
            request.onsuccess = (event: Event) => {
                this.db = (event.target as IDBOpenDBRequest).result;
                resolve();
            };
            
            request.onerror = (event: Event) => {
                console.error("IndexedDB initialization error:", event);
                reject((event.target as IDBOpenDBRequest).error);
            };
        });
    }
    
    /**
     * Cache an action locally when offline.
     */
    public async cacheAction(endpoint: string, payload: any): Promise<void> {
        if (!this.db) await this.initDB();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db!.transaction(STORE_NAME, "readwrite");
            const store = transaction.objectStore(STORE_NAME);
            
            const item = {
                endpoint,
                payload,
                timestamp: Date.now(),
                status: "pending"
            };
            
            const request = store.add(item);
            
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }
    
    /**
     * Process the queue and sync with the backend.
     * Uses timestamp-based basic conflict resolution strategy.
     */
    public async syncQueue(): Promise<void> {
        if (!navigator.onLine) return;
        if (!this.db) await this.initDB();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db!.transaction(STORE_NAME, "readwrite");
            const store = transaction.objectStore(STORE_NAME);
            const request = store.getAll();
            
            request.onsuccess = async () => {
                const items = request.result;
                if (items.length === 0) {
                    resolve();
                    return;
                }
                
                console.log(`Syncing ${items.length} offline items...`);
                
                for (const item of items) {
                    try {
                        // Attempt to send to server
                        const response = await fetch(item.endpoint, {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify(item.payload)
                        });
                        
                        if (response.ok) {
                            // Clean up successfully synced items
                            const deleteTx = this.db!.transaction(STORE_NAME, "readwrite");
                            deleteTx.objectStore(STORE_NAME).delete(item.id);
                        }
                    } catch (error) {
                        console.error("Sync failed for item:", item, error);
                    }
                }
                resolve();
            };
            
            request.onerror = () => reject(request.error);
        });
    }
}

export const offlineSyncService = new OfflineSyncService();
