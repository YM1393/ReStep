import { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { notificationApi } from '../services/api';
import type { Notification } from '../services/api';

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return '방금 전';
  if (mins < 60) return `${mins}분 전`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}시간 전`;
  const days = Math.floor(hours / 24);
  return `${days}일 전`;
}

const TYPE_ICONS: Record<string, string> = {
  analysis_complete: '📊',
  goal_achieved: '🎯',
  therapist_approved: '✅',
};

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const portalPanelRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const fetchUnreadCount = useCallback(async () => {
    try {
      const count = await notificationApi.getUnreadCount();
      setUnreadCount(count);
    } catch {
      // ignore
    }
  }, []);

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const data = await notificationApi.getAll(20);
      setNotifications(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll unread count every 30s
  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

  // Load notifications when panel opens
  useEffect(() => {
    if (open) {
      fetchNotifications();
    }
  }, [open, fetchNotifications]);

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      const target = e.target as Node;
      if (
        panelRef.current && !panelRef.current.contains(target) &&
        portalPanelRef.current && !portalPanelRef.current.contains(target)
      ) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  const handleClick = async (noti: Notification) => {
    // Mark read
    if (!noti.is_read) {
      await notificationApi.markRead(noti.id);
      setNotifications(prev => prev.map(n => n.id === noti.id ? { ...n, is_read: 1 } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    }

    // Navigate
    if (noti.data?.patient_id) {
      navigate(`/patients/${noti.data.patient_id}`);
      setOpen(false);
    }
  };

  const handleMarkAllRead = async () => {
    await notificationApi.markAllRead();
    setNotifications(prev => prev.map(n => ({ ...n, is_read: 1 })));
    setUnreadCount(0);
  };

  const buttonRef = useRef<HTMLButtonElement>(null);

  // Compute panel position for desktop (below bell button)
  const [btnRect, setBtnRect] = useState<DOMRect | null>(null);
  useEffect(() => {
    if (open && buttonRef.current) {
      setBtnRect(buttonRef.current.getBoundingClientRect());
    }
  }, [open]);

  const panel = open ? createPortal(
    <>
      {/* 백드롭 */}
      <div className="fixed inset-0 bg-black/30 sm:bg-transparent z-[9998]" onClick={() => setOpen(false)} />

      {/* 알림 패널 */}
      <div
        ref={portalPanelRef}
        className="fixed z-[9999] bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden inset-x-3 top-16 max-h-[70vh] sm:inset-auto sm:max-h-[500px] sm:w-96"
        style={btnRect && window.innerWidth >= 640 ? {
          top: btnRect.bottom + 8,
          right: window.innerWidth - btnRect.right,
        } : undefined}
      >
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center flex-shrink-0">
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">알림</h3>
          <div className="flex items-center gap-3">
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
              >
                모두 읽음
              </button>
            )}
            <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {loading && notifications.length === 0 ? (
            <div className="py-8 text-center text-gray-500 dark:text-gray-400 text-sm">
              로딩 중...
            </div>
          ) : notifications.length === 0 ? (
            <div className="py-8 text-center text-gray-500 dark:text-gray-400 text-sm">
              알림이 없습니다
            </div>
          ) : (
            notifications.map(noti => (
              <button
                key={noti.id}
                onClick={() => handleClick(noti)}
                className={`w-full px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors border-b border-gray-100 dark:border-gray-700/50 last:border-b-0 ${
                  !noti.is_read ? 'bg-blue-50/50 dark:bg-blue-900/10' : ''
                }`}
              >
                <div className="flex gap-3">
                  <span className="text-xl flex-shrink-0 mt-0.5">
                    {TYPE_ICONS[noti.type] || '🔔'}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100 break-words">
                        {noti.title}
                      </span>
                      {!noti.is_read && (
                        <span className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" />
                      )}
                    </div>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 break-words">
                      {noti.message}
                    </p>
                    <span className="text-xs text-gray-400 dark:text-gray-500 mt-1 block">
                      {timeAgo(noti.created_at)}
                    </span>
                  </div>
                </div>
              </button>
            ))
          )}
        </div>
      </div>
    </>,
    document.body
  ) : null;

  return (
    <div className="relative" ref={panelRef}>
      <button
        ref={buttonRef}
        onClick={() => setOpen(!open)}
        className="relative p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
        aria-label={`알림 ${unreadCount > 0 ? `(${unreadCount}개 읽지 않음)` : ''}`}
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center font-medium">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>
      {panel}
    </div>
  );
}
