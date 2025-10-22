import { MessageCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Avatar } from "@/components/common/Avatar";

interface ChatMessage {
  playerId: string;
  message: string;
  timestamp: string;
}

interface ChatWindowProps {
  messages: ChatMessage[];
  playerNames?: Record<string, string>;
  playerAvatars?: Record<string, { avatarUrl?: string | null; avatarType?: string }>;
  onPlayerClick?: (playerId: string) => void;
}

export function ChatWindow({ messages, playerNames = {}, playerAvatars = {}, onPlayerClick }: ChatWindowProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isUserScrolledUp, setIsUserScrolledUp] = useState(false);
  const lastMessageCountRef = useRef(messages.length);

  // Detect when user scrolls up
  useEffect(() => {
    const element = scrollRef.current;
    if (!element) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = element;
      const isAtBottom = scrollHeight - scrollTop <= clientHeight + 50; // 50px tolerance
      setIsUserScrolledUp(!isAtBottom);
    };

    element.addEventListener('scroll', handleScroll);
    return () => element.removeEventListener('scroll', handleScroll);
  }, []);

  // On mount, ensure we start at the bottom so initial content mirrors playground behavior
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, []);

  // Smart auto-scroll: only scroll if new messages arrived AND user is at bottom
  useEffect(() => {
    if (!scrollRef.current) return;

    // Only auto-scroll if new messages arrived AND user is at bottom
    const hasNewMessages = messages.length > lastMessageCountRef.current;
    lastMessageCountRef.current = messages.length;

    if (hasNewMessages && !isUserScrolledUp) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isUserScrolledUp]);

  const getPlayerName = (playerId: string) => {
    return playerNames[playerId] || `Player ${playerId.slice(0, 8)}`;
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return "";
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="pb-3 flex-shrink-0 px-4 py-4 md:p-6">
        <h3 className="flex items-center gap-2 text-lg font-semibold">
          <MessageCircle className="h-5 w-5 text-brand-teal" />
          Agent Chat
        </h3>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden p-0">
        <div className="h-full px-3 md:px-4 pb-4 overflow-y-auto" ref={scrollRef}>
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
              No messages yet
            </div>
          ) : (
            <div className="space-y-3">
              {/* Natural order so newest is at the bottom */}
              {messages.map((msg, index) => (
                <div
                  key={index}
                  className="flex gap-3 p-3 rounded-lg bg-muted/50 hover:bg-muted/70 transition-colors"
                >
                  <div
                    className={onPlayerClick ? "cursor-pointer hover:opacity-80 transition-opacity" : ""}
                    onClick={() => onPlayerClick?.(msg.playerId)}
                    role={onPlayerClick ? "button" : undefined}
                    tabIndex={onPlayerClick ? 0 : undefined}
                    onKeyDown={(e) => {
                      if (onPlayerClick && (e.key === 'Enter' || e.key === ' ')) {
                        e.preventDefault();
                        onPlayerClick(msg.playerId);
                      }
                    }}
                  >
                    <Avatar
                      src={playerAvatars[msg.playerId]?.avatarUrl}
                      fallback={getPlayerName(msg.playerId)}
                      size="lg"
                      className="flex-shrink-0"
                      type={playerAvatars[msg.playerId]?.avatarType as any}
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span 
                        className={`font-semibold text-sm text-brand-teal ${onPlayerClick ? "cursor-pointer hover:opacity-80 transition-opacity" : ""}`}
                        onClick={() => onPlayerClick?.(msg.playerId)}
                        role={onPlayerClick ? "button" : undefined}
                        tabIndex={onPlayerClick ? 0 : undefined}
                        onKeyDown={(e) => {
                          if (onPlayerClick && (e.key === 'Enter' || e.key === ' ')) {
                            e.preventDefault();
                            onPlayerClick(msg.playerId);
                          }
                        }}
                      >
                        {getPlayerName(msg.playerId)}
                      </span>
                      {msg.timestamp && (
                        <span className="text-xs text-muted-foreground flex-shrink-0">
                          {formatTimestamp(msg.timestamp)}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-foreground whitespace-pre-wrap break-words">
                      {msg.message}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

