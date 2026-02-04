import React from 'react';
import { useChat } from '../context/ChatContext';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Settings, Add } from '@mui/icons-material';
import { getConversationTags } from '../services/api';

interface ConversationSidebarProps {
  onConversationSelect?: () => void;
  onOpenFeedbackModal: () => void;
}

const ConversationSidebar: React.FC<ConversationSidebarProps> = ({ onConversationSelect, onOpenFeedbackModal }) => {
  const {
    conversations,
    currentConversationId,
    selectConversation,
    handleCreateConversation,
    isLoadingConversations,
    fetchConversations,
    setIsConfigViewActive,
    isConfigViewActive,
    handleUpdateConversationTitle,
    isUpdatingConversationTitle,
    handleUpdateConversationTags,
  } = useChat();

  const { user, logout } = useAuth();
  const location = useLocation();
  const isChatEndpoint = location.pathname === '/chat';

  const [editingConversationId, setEditingConversationId] = React.useState<number | null>(null);
  const [editingTitle, setEditingTitle] = React.useState<string>('');
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [tagSuggestions, setTagSuggestions] = React.useState<string[]>([]);
  const [tagFilters, setTagFilters] = React.useState<string[]>([]);
  const [tagMode, setTagMode] = React.useState<'any' | 'all'>('any');
  const [tagFilterInput, setTagFilterInput] = React.useState('');
  const [tagDrafts, setTagDrafts] = React.useState<Record<number, string>>({});
  const [tagSaving, setTagSaving] = React.useState<Record<number, boolean>>({});
  const [tagError, setTagError] = React.useState<string | null>(null);
  const hasAppliedFiltersRef = React.useRef(false);

  const handleLogout = () => {
    logout();
    selectConversation(null);
  };

  const handleDoubleClick = (conv: { id: number; title: string | null }) => {
    setEditingConversationId(conv.id);
    setEditingTitle(conv.title || 'Untitled Chat');
  };

  const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setEditingTitle(e.target.value);
  };

  const handleSaveEdit = async () => {
    if (editingConversationId === null || !editingTitle.trim()) {
      handleCancelEdit();
      return;
    }
    await handleUpdateConversationTitle(editingConversationId, editingTitle.trim());
    setEditingConversationId(null);
    setEditingTitle('');
  };

  const handleCancelEdit = () => {
    setEditingConversationId(null);
    setEditingTitle('');
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      handleSaveEdit();
    } else if (event.key === 'Escape') {
      handleCancelEdit();
    }
  };

  React.useEffect(() => {
    if (editingConversationId !== null && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingConversationId]);

  const normalizeTagInput = (value: string) => value.trim().replace(/\s+/g, ' ').toLowerCase();

  React.useEffect(() => {
    let isMounted = true;
    const fetchTags = async () => {
      try {
        const tags = await getConversationTags();
        if (isMounted) {
          setTagSuggestions(tags);
        }
      } catch (err) {
        console.error('Failed to fetch conversation tags:', err);
      }
    };
    fetchTags();
    return () => {
      isMounted = false;
    };
  }, []);

  React.useEffect(() => {
    if (!hasAppliedFiltersRef.current) {
      hasAppliedFiltersRef.current = true;
      return;
    }
    fetchConversations(tagFilters.length > 0 ? tagFilters : undefined, tagMode);
  }, [tagFilters, tagMode, fetchConversations]);

  const addTagFilter = (rawTag: string) => {
    const normalized = normalizeTagInput(rawTag);
    if (!normalized || tagFilters.includes(normalized)) {
      return;
    }
    setTagFilters((prev) => [...prev, normalized]);
    setTagFilterInput('');
  };

  const removeTagFilter = (tag: string) => {
    setTagFilters((prev) => prev.filter((item) => item !== tag));
  };

  const updateConversationTagList = async (conversationId: number, nextTags: string[]) => {
    setTagSaving((prev) => ({ ...prev, [conversationId]: true }));
    setTagError(null);
    try {
      await handleUpdateConversationTags(conversationId, nextTags);
      setTagDrafts((prev) => ({ ...prev, [conversationId]: '' }));
      setTagSuggestions((prev) => {
        const merged = new Set(prev);
        nextTags.forEach((tag) => merged.add(tag));
        return Array.from(merged).sort();
      });
    } catch (err) {
      console.error('Failed to update conversation tags:', err);
      setTagError('Failed to update tags. Please try again.');
    } finally {
      setTagSaving((prev) => ({ ...prev, [conversationId]: false }));
    }
  };

  const handleAddTag = (conversationId: number) => {
    const rawTag = tagDrafts[conversationId] ?? '';
    const normalized = normalizeTagInput(rawTag);
    if (!normalized) {
      return;
    }
    const conversation = conversations.find((item) => item.id === conversationId);
    const existing = conversation?.tags ?? [];
    if (existing.includes(normalized)) {
      setTagDrafts((prev) => ({ ...prev, [conversationId]: '' }));
      return;
    }
    updateConversationTagList(conversationId, [...existing, normalized]);
  };

  const handleRemoveTag = (conversationId: number, tag: string) => {
    const conversation = conversations.find((item) => item.id === conversationId);
    const existing = conversation?.tags ?? [];
    updateConversationTagList(
      conversationId,
      existing.filter((item) => item !== tag)
    );
  };

  const handleBrainConfigClick = () => {
    selectConversation(null);
    setIsConfigViewActive(true);
    onConversationSelect?.();
  };

  const handleConversationClick = (convId: number) => {
    selectConversation(convId);
    onConversationSelect?.();
  };

  const handleNewChatClick = () => {
    handleCreateConversation();
    onConversationSelect?.();
  };

  // Helper function to get a random emoji for each conversation based on its ID
  const getConversationEmoji = (id: number) => {
    const emojis = ['🚀', '🔍', '💡', '🌈', '🦄', '🌟', '🧠', '🔭', '📚', '🧩', '🔮', '🌍'];
    return emojis[id % emojis.length];
  };

  return (
    <div className="sidebar-main">
      {/* Header / New Chat Button */}
      <div className="sidebar-header">
        <button 
          onClick={handleNewChatClick} 
          className="new-chat-btn"
        >
          <Add className="mr-2" /> New Adventure
        </button>
      </div>

      {/* Conversation List */}
      <div className="conversation-list custom-scrollbar">
        <h2 className="conversation-list-header">Your Chats</h2>
        <div className="mb-3 rounded-xl bg-indigo-800/40 px-2 py-2">
          <div className="flex items-center justify-between px-1 text-[10px] font-semibold uppercase tracking-wider text-indigo-200">
            <span>Filter tags</span>
            <button
              type="button"
              className="text-[10px] font-semibold text-indigo-100 transition hover:text-white"
              onClick={() => setTagMode((prev) => (prev === 'any' ? 'all' : 'any'))}
            >
              Match: {tagMode === 'any' ? 'Any' : 'All'}
            </button>
          </div>
          <div className="mt-2 flex flex-wrap gap-1 px-1">
            {tagFilters.map((tag) => (
              <span
                key={`filter-${tag}`}
                className="inline-flex items-center gap-1 rounded-full bg-indigo-500/50 px-2 py-0.5 text-[10px] font-semibold text-white"
              >
                <span>{tag}</span>
                <button
                  type="button"
                  className="text-[11px] leading-none text-indigo-100 hover:text-white"
                  onClick={() => removeTagFilter(tag)}
                  aria-label={`Remove filter tag ${tag}`}
                >
                  ×
                </button>
              </span>
            ))}
            <input
              value={tagFilterInput}
              onChange={(event) => setTagFilterInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ',') {
                  event.preventDefault();
                  addTagFilter(tagFilterInput);
                }
              }}
              list="conversation-tag-suggestions"
              placeholder="Add filter"
              className="w-24 rounded-full border border-indigo-500/50 bg-indigo-900/40 px-2 py-0.5 text-[10px] text-indigo-100 placeholder:text-indigo-300 focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-400/40"
            />
          </div>
        </div>
        {tagError && (
          <div className="mb-2 rounded-lg bg-red-500/20 px-3 py-2 text-xs text-red-100">
            {tagError}
          </div>
        )}
        
        {isLoadingConversations ? (
          <div className="conversation-list-loading">Loading chats...</div>
        ) : conversations.length === 0 ? (
          <div className="conversation-list-empty">
            <div className="text-3xl mb-2">🔍</div>
            {tagFilters.length > 0
              ? 'No chats match these tags.'
              : (
                <>
                  No chats yet.<br />Start a new adventure!
                </>
              )}
          </div>
        ) : (
          <ul className="space-y-3">
            {conversations.map((conv) => {
              const conversationTags = conv.tags ?? [];
              return (
                <li key={conv.id} className="conversation-item">
                  {editingConversationId === conv.id ? (
                    <div className="conversation-edit-container">
                      <input
                        ref={inputRef}
                        type="text"
                        value={editingTitle}
                        onChange={handleTitleChange}
                        onKeyDown={handleKeyDown}
                        onBlur={() => setTimeout(() => {
                          if (!isUpdatingConversationTitle && editingConversationId !== null) {
                          }
                        }, 100)}
                        className="conversation-edit-input"
                        disabled={isUpdatingConversationTitle}
                      />
                      <div className="mt-2 flex justify-end space-x-2">
                        <button
                          onClick={handleSaveEdit}
                          className="conversation-edit-btn-save"
                          disabled={isUpdatingConversationTitle || !editingTitle.trim()}
                        >
                          {isUpdatingConversationTitle ? 'Saving...' : 'Save'}
                        </button>
                        <button
                          onClick={handleCancelEdit}
                          className="conversation-edit-btn-cancel"
                          disabled={isUpdatingConversationTitle}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <button
                        onClick={() => handleConversationClick(conv.id)}
                        onDoubleClick={() => handleDoubleClick(conv)}
                        className={conv.id === currentConversationId && !isConfigViewActive 
                            ? 'conversation-btn-active' 
                            : 'conversation-btn-inactive'}
                        title={conv.title || 'Untitled Chat'}
                      >
                        <div className="conversation-emoji">
                          <span>{getConversationEmoji(conv.id)}</span>
                        </div>
                        <div className="conversation-content">
                          <div className="conversation-title">
                            {conv.title || 'Untitled Chat'}
                          </div>
                          <span className="conversation-date">
                            {new Date(conv.updated_at).toLocaleDateString()}
                          </span>
                        </div>
                      </button>
                      <div className="mt-2 flex flex-wrap items-center gap-1 px-2">
                        {conversationTags.map((tag) => (
                          <span
                            key={`${conv.id}-${tag}`}
                            className="inline-flex items-center gap-1 rounded-full bg-white/20 px-2 py-0.5 text-[10px] font-semibold text-white"
                          >
                            <span>{tag}</span>
                            <button
                              type="button"
                              className="text-[11px] leading-none text-indigo-100 hover:text-white"
                              onClick={() => handleRemoveTag(conv.id, tag)}
                              aria-label={`Remove tag ${tag}`}
                              disabled={tagSaving[conv.id]}
                            >
                              ×
                            </button>
                          </span>
                        ))}
                        <div className="flex items-center gap-1">
                          <input
                            value={tagDrafts[conv.id] ?? ''}
                            onChange={(event) =>
                              setTagDrafts((prev) => ({ ...prev, [conv.id]: event.target.value }))
                            }
                            onKeyDown={(event) => {
                              if (event.key === 'Enter' || event.key === ',') {
                                event.preventDefault();
                                handleAddTag(conv.id);
                              }
                            }}
                            list="conversation-tag-suggestions"
                            placeholder="Add"
                            className="w-20 rounded-full border border-indigo-500/50 bg-indigo-900/40 px-2 py-0.5 text-[10px] text-indigo-100 placeholder:text-indigo-300 focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-400/40"
                            disabled={tagSaving[conv.id]}
                          />
                          <button
                            type="button"
                            className="rounded-full border border-indigo-500/60 px-2 py-0.5 text-[10px] font-semibold text-indigo-100 hover:border-indigo-300 hover:text-white disabled:opacity-60"
                            onClick={() => handleAddTag(conv.id)}
                            disabled={tagSaving[conv.id]}
                          >
                            Add
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                </li>
              );
            })}
          </ul>
        )}
        <datalist id="conversation-tag-suggestions">
          {tagSuggestions.map((tag) => (
            <option key={`conversation-tag-${tag}`} value={tag} />
          ))}
        </datalist>
      </div>

      {/* Brain Config Button - Hide for the /chat endpoint */}
      {!isChatEndpoint && (
        <div className="sidebar-section">
          <button 
            onClick={handleBrainConfigClick}
            className={isConfigViewActive ? 'brain-config-btn-active' : 'brain-config-btn'}
          >
            <Settings className="mr-2" /> Brain Config
          </button>
        </div>
      )}

      {/* User Info and Logout Button */}
      {user && (
        <div className="user-info-section">
          <div className="flex flex-col space-y-3">
            <button 
                onClick={onOpenFeedbackModal}
                className="new-chat-btn"
            >
                Give Feedback
            </button>
            <div className="text-center">
                <span className="user-info-text text-sm">
                Logged in as: <span className="font-medium text-white">{user.student?.first_name || user.name || user.phone_number}</span>
                </span>
                <span className="mx-2 text-gray-400">|</span>
                <button
                onClick={handleLogout}
                className="text-sm text-gray-300 hover:text-white hover:underline transition-colors duration-200"
                >
                Logout
                </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConversationSidebar; 
