import type { QuoteUpdate, OrderUpdateMessage, WebSocketMessage } from '@/types';

type MessageHandler = (data: unknown) => void;

interface WebSocketOptions {
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private options: Required<WebSocketOptions>;
  private reconnectAttempts = 0;
  private isConnecting = false;
  private shouldReconnect = true;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  
  private handlers: Map<string, Set<MessageHandler>> = new Map();
  private subscribedSymbols: Set<string> = new Set();

  constructor(url: string, options: WebSocketOptions = {}) {
    this.url = url;
    this.options = {
      reconnectInterval: options.reconnectInterval ?? 3000,
      maxReconnectAttempts: options.maxReconnectAttempts ?? 10,
      heartbeatInterval: options.heartbeatInterval ?? 30000,
    };
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }

      if (this.isConnecting) {
        resolve();
        return;
      }

      this.isConnecting = true;
      this.shouldReconnect = true;

      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.startHeartbeat();
          // Re-subscribe to previously subscribed symbols
          this.subscribedSymbols.forEach((symbol) => {
            this.send({ type: 'subscribe', symbol });
          });
          resolve();
        };

        this.ws.onclose = () => {
          this.isConnecting = false;
          this.stopHeartbeat();
          if (this.shouldReconnect) {
            this.attemptReconnect();
          }
        };

        this.ws.onerror = (error) => {
          this.isConnecting = false;
          console.error('WebSocket error:', error);
          reject(error);
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };
      } catch (error) {
        this.isConnecting = false;
        reject(error);
      }
    });
  }

  disconnect(): void {
    this.shouldReconnect = false;
    this.stopHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  subscribe(symbol: string): void {
    this.subscribedSymbols.add(symbol);
    if (this.isConnected()) {
      this.send({ type: 'subscribe', symbol });
    }
  }

  unsubscribe(symbol: string): void {
    this.subscribedSymbols.delete(symbol);
    if (this.isConnected()) {
      this.send({ type: 'unsubscribe', symbol });
    }
  }

  subscribeToQuotes(symbols: string[]): void {
    symbols.forEach((symbol) => this.subscribe(symbol));
  }

  unsubscribeFromQuotes(symbols: string[]): void {
    symbols.forEach((symbol) => this.unsubscribe(symbol));
  }

  on(event: 'quote', handler: (data: QuoteUpdate) => void): void;
  on(event: 'order_update', handler: (data: OrderUpdateMessage) => void): void;
  on(event: 'alert' | 'notification', handler: (data: unknown) => void): void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  on(event: string, handler: (data: any) => void): void {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event)!.add(handler);
  }

  off(event: string, handler: MessageHandler): void {
    this.handlers.get(event)?.delete(handler);
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private send(data: unknown): void {
    if (this.isConnected()) {
      this.ws!.send(JSON.stringify(data));
    }
  }

  private handleMessage(message: WebSocketMessage): void {
    const handlers = this.handlers.get(message.type);
    handlers?.forEach((handler) => handler(message.data));
  }

  private startHeartbeat(): void {
    this.heartbeatTimer = setInterval(() => {
      this.send({ type: 'ping' });
    }, this.options.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }
    this.reconnectAttempts++;
    this.reconnectTimer = setTimeout(() => {
      this.connect().catch(console.error);
    }, this.options.reconnectInterval);
  }
}

// Singleton instance
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';
export const wsClient = new WebSocketClient(WS_URL);

