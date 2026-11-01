import { useState, useRef, useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { FaPaperPlane, FaRobot, FaUser, FaBalanceScale, FaFileContract, FaGavel, FaPlus, FaComments, FaTrash, FaEllipsisV, FaHistory, FaTimes } from 'react-icons/fa';
import { useLanguage } from '../../context/useLanguage';
import { formatRelative, formatTime as fmtTime, formatDate } from '../../utils/formatDate';
import { useUser } from '../../context/useUser';
import { useAuthFetch } from '../../hooks/useAuthFetch';
import UpgradePlanScreen from '../UpgradePlanScreen';
import ConfirmDeleteModal from '../ConfirmDeleteModal';
import { API_ORIGIN } from '../../config/api';

const API_BASE = API_ORIGIN;

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  contract_name?: string | null;
  created_at: string;
  status?: 'completed' | 'error';
  error_code?: string;
  retry_text?: string;
  failed_temp_id?: string;
  citations?: Array<{ identifier?: string; citation?: string; law_name?: string }>;
  limitations?: string[];
  abstained?: boolean;
}

interface Conversation {
  id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
  contract_id?: string | null;
  generated_contract_id?: string | null;
  contract_name?: string | null;
}

interface ContractListItem {
  id: string;
  filename: string;
  uploadDate: string;
  source: 'analyzed' | 'generated';
  status: string;
}

interface ChatRequestBody {
  message: string;
  contract_id?: string;
  generated_contract_id?: string;
  request_id: string;
}




export default function Agent() {
  const location = useLocation();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
  const [loadingConvs, setLoadingConvs] = useState(true);
  const [showContracts, setShowContracts] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [contracts, setContracts] = useState<ContractListItem[]>([]);
  const [loadingContracts, setLoadingContracts] = useState(false);
  const [selectedContractId, setSelectedContractId] = useState<string | null>(null);
  const [selectedGeneratedContractId, setSelectedGeneratedContractId] = useState<string | null>(null);
  const [selectedContractName, setSelectedContractName] = useState<string | null>(null);
  const [conversationToDelete, setConversationToDelete] = useState<Conversation | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesRequestVersionRef = useRef(0);
  const skipNextMessagesFetchRef = useRef(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { t, language } = useLanguage();
  const { user } = useUser();
  const authFetch = useAuthFetch();

  const scrollToBottom = () => {
    if (typeof messagesEndRef.current?.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);


  useEffect(() => {
    const handleClick = () => {
      setMenuOpenId(null);
    };
    if (menuOpenId) document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, [menuOpenId]);





  const fetchConversations = useCallback(async () => {
    try {
      const res = await authFetch(`${API_BASE}/api/agent/conversations`);
      if (res.ok) {
        const data: Conversation[] = await res.json();
        setConversations(data);
      }
    } catch (err) {
      console.error('Error fetching conversations:', err);
    } finally {
      setLoadingConvs(false);
    }
  }, [authFetch]);

  const fetchMessages = useCallback(async (convId: string) => {
    const requestVersion = messagesRequestVersionRef.current;
    try {
      const res = await authFetch(`${API_BASE}/api/agent/conversations/${convId}/messages`);
      if (res.ok) {
        const data: Message[] = await res.json();
        if (requestVersion === messagesRequestVersionRef.current) {
          setMessages(data);
        }
      }
    } catch (err) {
      console.error('Error fetching messages:', err);
    }
  }, [authFetch]);

  const fetchContracts = useCallback(async () => {
    setLoadingContracts(true);
    try {
      const [analyzedRes, generatedRes] = await Promise.all([
        authFetch(`${API_BASE}/api/contracts`),
        authFetch(`${API_BASE}/api/generated-contracts`),
      ]);

      const allContracts: ContractListItem[] = [];

      if (analyzedRes.ok) {
        const analyzed = await analyzedRes.json();
          for (const c of analyzed.filter((item: { status?: string }) => item.status === 'completed')) {
          allContracts.push({
            id: c.id,
            filename: c.filename,
            uploadDate: c.uploadDate,
            source: 'analyzed',
            status: c.status,
          });
        }
      }

      if (generatedRes.ok) {
        const generated = await generatedRes.json();
          for (const c of generated.filter((item: { status?: string }) => item.status === 'completed')) {
          allContracts.push({
            id: c.id,
            filename: c.title,
            uploadDate: formatDate(c.created_at, language),
            source: 'generated',
            status: c.status,
          });
        }
      }

      setContracts(allContracts);
    } catch (err) {
      console.error('Error fetching contracts:', err);
    } finally {
      setLoadingContracts(false);
    }
  }, [authFetch]);

  const sendChatMessage = useCallback(async (convId: string, text: string, contractId?: string | null, generatedContractId?: string | null): Promise<{ user_message: Message | null; assistant_message: Message } | null> => {
    try {
      const body: ChatRequestBody = { message: text, request_id: crypto.randomUUID() };
      if (contractId) {
        body.contract_id = contractId;
      }
      if (generatedContractId) {
        body.generated_contract_id = generatedContractId;
      }
      const res = await authFetch(`${API_BASE}/api/agent/conversations/${convId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        return await res.json();
      }
      const errorBody = await res.json().catch(() => null);
      const code = errorBody?.detail?.code || 'unexpected_error';
      const messageByCode: Record<string, string> = {
        guardrail_rejected: t('agent.errorGuardrail'),
        unsupported_contract: t('agent.errorUnsupported'),
        contract_not_found: t('agent.errorContract'),
        agent_access_denied: t('agent.errorAccess'),
        chat_temporarily_unavailable: t('agent.errorUnavailable'),
        chat_request_in_progress: t('agent.errorInProgress'),
      };
      return {
        user_message: null,
        assistant_message: {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: messageByCode[code] || t('agent.errorUnexpected'),
          contract_name: null,
          created_at: new Date().toISOString(),
          status: 'error',
          error_code: code,
        },
      };
    } catch (err) {
      console.error('Error sending chat message:', err);
    }
    return null;
  }, [authFetch, t]);

  const createConversationAPI = useCallback(async (): Promise<Conversation | null> => {
    try {
      const res = await authFetch(`${API_BASE}/api/agent/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (err) {
      console.error('Error creating conversation:', err);
    }
    return null;
  }, [authFetch]);

  const deleteConversationAPI = useCallback(async (convId: string) => {
    try {
      await authFetch(`${API_BASE}/api/agent/conversations/${convId}`, { method: 'DELETE' });
    } catch (err) {
      console.error('Error deleting conversation:', err);
    }
  }, [authFetch]);


  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);


  useEffect(() => {
    const state = location.state as {
      generatedContract?: { id: string; title: string };
      analyzedContract?: { id: string; filename: string };
    } | null;

    if (state?.generatedContract) {
      const { id, title } = state.generatedContract;
      window.history.replaceState({}, '');
      setSelectedGeneratedContractId(id);
      setSelectedContractName(title);
      setInputText('');
      inputRef.current?.focus();
    } else if (state?.analyzedContract) {
      const { id, filename } = state.analyzedContract;
      window.history.replaceState({}, '');
      setSelectedContractId(id);
      setSelectedContractName(filename);
      setInputText('');
      inputRef.current?.focus();
    }
  }, [location.state]);


  useEffect(() => {
    if (activeConvId) {
      if (skipNextMessagesFetchRef.current) {
        skipNextMessagesFetchRef.current = false;
        return;
      }
      fetchMessages(activeConvId);
    } else {
      setMessages([]);
    }
  }, [activeConvId, fetchMessages]);

  useEffect(() => {
    if (!activeConvId) return;
    const conversation = conversations.find((item) => item.id === activeConvId);
    if (!conversation) return;
    setSelectedContractId(conversation.contract_id || null);
    setSelectedGeneratedContractId(conversation.generated_contract_id || null);
    setSelectedContractName(conversation.contract_name || null);
  }, [activeConvId, conversations]);



  const handleNewChat = () => {
    setActiveConvId(null);
    setMessages([]);
    setInputText('');
    setSelectedContractId(null);
    setSelectedGeneratedContractId(null);
    setSelectedContractName(null);
  };

  const deleteConversation = async (convId: string) => {
    await deleteConversationAPI(convId);
    setConversations((prev) => prev.filter((c) => c.id !== convId));
    if (activeConvId === convId) {
      setActiveConvId(null);
      setMessages([]);
    }
    setMenuOpenId(null);
    setConversationToDelete(null);
  };

  const sendAndReceive = async (convId: string, text: string) => {
    messagesRequestVersionRef.current += 1;
    const tempId = `temp-${Date.now()}`;
    const contractNameToSend = selectedContractName;
    const optimisticMessage: Message = {
      id: tempId,
      role: 'user',
      content: text,
      contract_name: contractNameToSend || null,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, optimisticMessage]);
    setIsTyping(true);

    const contractIdToSend = selectedContractId;
    const generatedContractIdToSend = selectedGeneratedContractId;
    try {
      const result = await sendChatMessage(convId, text, contractIdToSend, generatedContractIdToSend);

      if (result) {
        setMessages((prev) => {
          const filtered = prev.filter((msg) => msg.id !== tempId);
          if (result.user_message) {
            return [...filtered, result.user_message, result.assistant_message];
          }
          return [...filtered, optimisticMessage, {
            ...result.assistant_message,
            retry_text: text,
            failed_temp_id: tempId,
          }];
        });
      } else {
        setMessages((prev) => prev.filter((msg) => msg.id !== tempId));
      }
    } catch (error) {
      console.error('Error in sendAndReceive:', error);
      setMessages((prev) => prev.filter((msg) => msg.id !== tempId));
    } finally {
      setIsTyping(false);
      fetchConversations();
    }
  };

  const clearContractContext = async () => {
    if (activeConvId) {
      const response = await authFetch(`${API_BASE}/api/agent/conversations/${activeConvId}/context`, { method: 'DELETE' });
      if (!response.ok) return;
      setConversations((previous) => previous.map((conversation) => conversation.id === activeConvId
        ? { ...conversation, contract_id: null, generated_contract_id: null, contract_name: null }
        : conversation));
    }
    setSelectedContractId(null);
    setSelectedGeneratedContractId(null);
    setSelectedContractName(null);
  };

  const retryFailedMessage = (message: Message) => {
    if (!activeConvId || !message.retry_text) return;
    setMessages((previous) => previous.filter((item) => item.id !== message.id && item.id !== message.failed_temp_id));
    sendAndReceive(activeConvId, message.retry_text);
  };

  const handleSend = async () => {
    const text = inputText.trim();
    if (!text || isTyping) return;
    setInputText('');

    let convId = activeConvId;

    if (!convId) {
      const newConv = await createConversationAPI();
      if (!newConv) return;
      convId = newConv.id;
      skipNextMessagesFetchRef.current = true;
      setActiveConvId(convId);
      setConversations((prev) => [newConv, ...prev]);
    }

    inputRef.current?.focus();
    sendAndReceive(convId, text);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSuggestion = async (text: string) => {
    let convId = activeConvId;

    if (!convId) {
      const newConv = await createConversationAPI();
      if (!newConv) return;
      convId = newConv.id;
      skipNextMessagesFetchRef.current = true;
      setActiveConvId(convId);
      setConversations((prev) => [newConv, ...prev]);
    }

    sendAndReceive(convId, text);
  };

  const suggestions = [
    { icon: FaBalanceScale, text: t('agent.suggestion1') },
    { icon: FaFileContract, text: t('agent.suggestion2') },
    { icon: FaGavel, text: t('agent.suggestion3') },
  ];

  const formatTime = (isoString: string) => fmtTime(isoString, language);


  const renderSidebar = () => (
    <div className={`fixed inset-y-0 left-0 z-40 w-72 bg-white dark:bg-dark-800 border-r border-dark-200 dark:border-dark-700 flex flex-col h-full transform transition-transform duration-300 ease-in-out md:relative md:translate-x-0 ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>

      <div className="px-4 py-4 border-b border-dark-200 dark:border-dark-700">
        <button
          onClick={handleNewChat}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
            bg-primary-600 hover:bg-primary-500 text-white font-medium
            transition-all duration-200 shadow-md shadow-primary-600/20"
        >
          <FaPlus className="w-3.5 h-3.5" />
          {t('agent.newChat')}
        </button>
      </div>


      <div className="flex-1 overflow-y-auto">
        {loadingConvs ? (
          <div className="flex items-center justify-center h-32">
            <div className="w-6 h-6 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : conversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full px-4 text-center">
            <FaComments className="w-8 h-8 text-dark-300 dark:text-dark-600 mb-3" />
            <p className="text-sm text-dark-400 dark:text-dark-500">
              {t('agent.noConversations')}
            </p>
          </div>
        ) : (
          <div className="py-2">
            {conversations.map((conv) => (
              <div key={conv.id} className="relative group px-2">
                <button
                  onClick={() => { setActiveConvId(conv.id); setMenuOpenId(null); }}
                  className={`w-full flex items-start gap-3 px-3 py-3 rounded-lg text-left
                    transition-all duration-150
                    ${activeConvId === conv.id
                      ? 'bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800'
                      : 'hover:bg-dark-50 dark:hover:bg-dark-700/50 border border-transparent'
                    }`}
                >
                  <div className={`w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center mt-0.5
                    ${activeConvId === conv.id
                      ? 'bg-primary-100 dark:bg-primary-900/40'
                      : 'bg-dark-100 dark:bg-dark-700'
                    }`}>
                    <FaComments className={`w-3.5 h-3.5
                      ${activeConvId === conv.id
                        ? 'text-primary-600 dark:text-primary-400'
                        : 'text-dark-400 dark:text-dark-500'
                      }`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-medium truncate
                      ${activeConvId === conv.id
                        ? 'text-primary-700 dark:text-primary-300'
                        : 'text-dark-800 dark:text-dark-200'
                      }`}>
                      {conv.title}
                    </p>
                    <p className="text-xs text-dark-400 dark:text-dark-500 mt-0.5">
                      {conv.message_count} {conv.message_count !== 1 ? t('agent.messagesCountPlural') : t('agent.messagesCount')} · {formatRelative(conv.updated_at, language, t)}
                    </p>
                  </div>
                </button>


                <button
                  onClick={(e) => { e.stopPropagation(); setMenuOpenId(menuOpenId === conv.id ? null : conv.id); }}
                  className="absolute top-3 right-3 p-1.5 rounded-md opacity-0 group-hover:opacity-100
                    hover:bg-dark-200 dark:hover:bg-dark-600 transition-all duration-150"
                >
                  <FaEllipsisV className="w-3 h-3 text-dark-400" />
                </button>


                {menuOpenId === conv.id && (
                  <div className="absolute right-3 top-10 z-10 bg-white dark:bg-dark-700 border border-dark-200 dark:border-dark-600 rounded-lg shadow-lg py-1 min-w-[140px]">
                    <button
                      onClick={() => setConversationToDelete(conv)}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                    >
                      <FaTrash className="w-3 h-3" />
                      {t('agent.delete')}
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );


  const renderChatContent = () => {
    if (messages.length === 0 && !activeConvId) {
      return (
        <>

          <div className="flex-1 flex flex-col items-center justify-center px-4">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-400 to-primary-700 flex items-center justify-center mb-6 shadow-lg shadow-primary-500/25">
              <FaRobot className="w-10 h-10 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-dark-900 dark:text-white mb-2">
              {t('agent.title')}
            </h2>
            <p className="text-dark-500 dark:text-dark-400 text-center max-w-md mb-10">
              {t('agent.subtitle')}
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-3xl">
              {suggestions.map((s, i) => {
                const Icon = s.icon;
                return (
                  <button
                    key={i}
                    onClick={() => handleSuggestion(s.text)}
                    className="group flex flex-col items-start gap-3 p-5 rounded-xl
                      bg-white dark:bg-dark-800 border border-dark-200 dark:border-dark-700
                      hover:border-primary-400 dark:hover:border-primary-500
                      hover:shadow-lg hover:shadow-primary-500/10
                      transition-all duration-200 text-left"
                  >
                    <Icon className="w-5 h-5 text-primary-500 group-hover:text-primary-400 transition-colors" />
                    <span className="text-sm text-dark-700 dark:text-dark-300 leading-relaxed">
                      {s.text}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </>
      );
    }

    return (
      <>

        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
              >
                {msg.role === 'user' && msg.contract_name && (
                  <div className="flex items-center gap-1.5 mb-1.5 mr-12 px-2.5 py-1 bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-lg">
                    <FaFileContract className="w-3 h-3 text-primary-500 flex-shrink-0" />
                    <span className="text-xs font-medium text-primary-700 dark:text-primary-300 truncate max-w-[250px]">
                      {msg.contract_name}
                    </span>
                  </div>
                )}
                <div className={`flex gap-3 w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.role === 'assistant' && (
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-400 to-primary-700 flex-shrink-0 flex items-center justify-center shadow-md shadow-primary-500/20">
                      <FaRobot className="w-4 h-4 text-white" />
                    </div>
                  )}

                  <div
                    className={`max-w-[75%] px-4 py-3 rounded-2xl ${msg.role === 'user'
                      ? 'bg-primary-600 text-white rounded-br-md'
                      : 'bg-white dark:bg-dark-800 text-dark-800 dark:text-dark-200 border border-dark-200 dark:border-dark-700 rounded-bl-md'
                      }`}
                  >
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                    {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-dark-200 dark:border-dark-700">
                        <p className="text-xs font-semibold mb-1">{t('agent.sources')}</p>
                        <ul className="text-xs space-y-1 text-dark-500 dark:text-dark-400">
                          {msg.citations.map((citation, index) => (
                            <li key={citation.identifier || index}>{citation.citation || citation.identifier}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {msg.status === 'error' && msg.retry_text && (
                      <button
                        type="button"
                        onClick={() => retryFailedMessage(msg)}
                        className="mt-3 text-xs font-semibold text-primary-600 dark:text-primary-400 hover:underline"
                      >
                        {t('agent.retry')}
                      </button>
                    )}
                    <p
                      className={`text-[10px] mt-1.5 ${msg.role === 'user' ? 'text-primary-200' : 'text-dark-400 dark:text-dark-500'
                        }`}
                    >
                      {formatTime(msg.created_at)}
                    </p>
                  </div>

                  {msg.role === 'user' && (
                    <div className="w-9 h-9 rounded-xl bg-dark-200 dark:bg-dark-600 flex-shrink-0 flex items-center justify-center overflow-hidden">
                      {user?.profile_image_url ? (
                        <img src={user.profile_image_url} alt="" referrerPolicy="no-referrer" className="w-full h-full object-cover" />
                      ) : (
                        <FaUser className="w-4 h-4 text-dark-600 dark:text-dark-300" />
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}


            {isTyping && (
              <div className="flex gap-3 justify-start">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-400 to-primary-700 flex-shrink-0 flex items-center justify-center shadow-md shadow-primary-500/20">
                  <FaRobot className="w-4 h-4 text-white" />
                </div>
                <div className="bg-white dark:bg-dark-800 border border-dark-200 dark:border-dark-700 px-5 py-4 rounded-2xl rounded-bl-md">
                  <div className="flex gap-1.5">
                    <span className="w-2 h-2 bg-dark-400 dark:bg-dark-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-dark-400 dark:bg-dark-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-dark-400 dark:bg-dark-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>
      </>
    );
  };

  if (user?.role === '1') {
    return <UpgradePlanScreen feature={t('agent.featureLabel')} />;
  }

  return (
    <div className="flex h-full bg-dark-50 dark:bg-dark-900">

      {renderSidebar()}

      {isSidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      <div className="flex-1 flex flex-col min-w-0 relative">
        <button
          onClick={() => setIsSidebarOpen(true)}
          className="md:hidden absolute top-4 left-4 z-10 p-3 bg-white dark:bg-dark-800 text-dark-600 dark:text-dark-300 rounded-full shadow-lg border border-dark-200 dark:border-dark-700 hover:bg-dark-50 dark:hover:bg-dark-700 transition-all"
        >
          <FaHistory className="w-5 h-5" />
        </button>
        {renderChatContent()}


        <div className="border-t border-dark-200 dark:border-dark-700 bg-white dark:bg-dark-800 px-4 py-4">
          <div className="max-w-3xl mx-auto flex gap-3 items-end">
            <div className="relative flex-shrink-0">
              <button
                onClick={() => {
                  setShowContracts(!showContracts);
                  if (!contracts.length) fetchContracts();
                }}
                className={`p-3 rounded-full transition-all duration-200 flex items-center justify-center
                  ${showContracts
                    ? 'bg-primary-600 text-white rotate-45'
                    : 'bg-dark-200 dark:bg-dark-700 text-dark-600 dark:text-dark-300 hover:bg-dark-300 dark:hover:bg-dark-600'
                  }`}
                title={t('agent.addReference')}
              >
                <FaPlus className="w-4 h-4" />
              </button>

              {showContracts && (
                <div className="absolute bottom-full left-0 mb-2 w-72 max-h-96 overflow-y-auto
                  bg-white dark:bg-dark-800 border border-dark-200 dark:border-dark-700
                  rounded-xl shadow-xl z-20 flex flex-col">
                  <div className="p-3 border-b border-dark-200 dark:border-dark-700 bg-dark-50 dark:bg-dark-700/50">
                    <h3 className="text-xs font-bold text-dark-500 dark:text-dark-400 uppercase tracking-wider">
                      {t('agent.selectContract')}
                    </h3>
                  </div>

                  {loadingContracts ? (
                    <div className="p-4 flex justify-center">
                      <div className="w-5 h-5 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
                    </div>
                  ) : contracts.length === 0 ? (
                    <div className="p-4 text-center text-sm text-dark-500 dark:text-dark-400">
                      {t('agent.noContracts')}
                    </div>
                  ) : (
                    <div className="py-1">
                      {contracts.map(contract => {
                        const isSelected = contract.source === 'generated'
                          ? selectedGeneratedContractId === contract.id
                          : selectedContractId === contract.id;
                        return (
                          <button
                            key={`${contract.source}-${contract.id}`}
                            onClick={() => {
                              if (contract.source === 'generated') {
                                setSelectedGeneratedContractId(contract.id);
                                setSelectedContractId(null);
                              } else {
                                setSelectedContractId(contract.id);
                                setSelectedGeneratedContractId(null);
                              }
                              setSelectedContractName(contract.filename);
                              setShowContracts(false);
                              inputRef.current?.focus();
                            }}
                            className={`w-full text-left px-4 py-3 hover:bg-dark-50 dark:hover:bg-dark-700
                              transition-colors border-b border-dark-100 dark:border-dark-700/50 last:border-0
                              ${isSelected ? 'bg-primary-50 dark:bg-primary-900/10' : ''}`}
                          >
                            <div className="flex items-center gap-3">
                              <FaFileContract className={`w-4 h-4 flex-shrink-0 ${contract.source === 'generated' ? 'text-amber-500' : 'text-primary-500'}`} />
                              <div className="min-w-0">
                                <p className="text-sm font-medium text-dark-900 dark:text-white truncate">
                                  {contract.filename}
                                </p>
                                <p className="text-xs text-dark-500 dark:text-dark-400 mt-0.5">
                                  {contract.uploadDate} · {contract.source === 'generated' ? t('agent.generated') : t('agent.analyzed')}
                                </p>
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="flex-1 flex flex-col gap-2">
              {selectedContractName && (
                <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-lg max-w-full overflow-hidden self-start">
                  <FaFileContract className="w-3.5 h-3.5 text-primary-500 flex-shrink-0" />
                  <span className="text-xs font-medium text-primary-700 dark:text-primary-300 truncate min-w-0">
                    {selectedContractName}
                  </span>
                  <button
                    onClick={() => {
                      clearContractContext();
                    }}
                    className="p-0.5 rounded-full hover:bg-primary-200 dark:hover:bg-primary-800 text-primary-400 hover:text-primary-600 dark:hover:text-primary-300 transition-colors flex-shrink-0"
                    title={t('agent.removeReference')}
                  >
                    <FaTimes className="w-3 h-3" />
                  </button>
                </div>
              )}
              <input
                ref={inputRef}
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={t('agent.placeholder')}
                maxLength={4000}
                className="w-full px-4 py-3 rounded-xl border border-dark-300 dark:border-dark-600
                  bg-dark-50 dark:bg-dark-700 text-dark-900 dark:text-white
                  placeholder-dark-400 dark:placeholder-dark-500
                  focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
                  transition-all duration-200"
              />
            </div>
            <button
              onClick={handleSend}
              disabled={!inputText.trim() || isTyping}
              className="flex-shrink-0 px-5 py-3 rounded-xl bg-primary-600 hover:bg-primary-500
                disabled:opacity-40 disabled:cursor-not-allowed
                text-white font-medium transition-all duration-200
                flex items-center gap-2 shadow-md shadow-primary-600/20"
            >
              <FaPaperPlane className="w-4 h-4" />
              <span className="hidden sm:inline">{t('agent.send')}</span>
            </button>
          </div>
          <p className="max-w-3xl mx-auto mt-2 text-center text-[11px] text-dark-400 dark:text-dark-500">
            {t('agent.disclaimer')}
          </p>
        </div>
      </div>
      <ConfirmDeleteModal
        isOpen={Boolean(conversationToDelete)}
        contractName={conversationToDelete?.title || ''}
        title={t('agent.deleteConversationTitle')}
        description={t('agent.deleteConversationDescription')}
        warningItems={[t('agent.deleteConversationWarning')]}
        onConfirm={() => conversationToDelete && deleteConversation(conversationToDelete.id)}
        onCancel={() => setConversationToDelete(null)}
      />
    </div>
  );
}
