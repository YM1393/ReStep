import { useState, useCallback } from 'react';

export interface WidgetConfig {
  id: string;
  label: string;
  visible: boolean;
  order: number;
}

const DEFAULT_WIDGETS: WidgetConfig[] = [
  { id: 'stats', label: '통계 카드', visible: true, order: 0 },
  { id: 'recentTests', label: '최근 검사', visible: true, order: 1 },
  { id: 'riskPatients', label: '주의 필요 환자', visible: true, order: 2 },
  { id: 'speedDistribution', label: '속도 분포', visible: true, order: 3 },
  { id: 'weeklyActivity', label: '주간 활동', visible: true, order: 4 },
];

const STORAGE_KEY = 'dashboard_prefs';

function loadPrefs(): WidgetConfig[] {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed: WidgetConfig[] = JSON.parse(saved);
      // Merge with defaults (in case new widgets were added)
      const ids = new Set(parsed.map(w => w.id));
      const merged = [...parsed];
      for (const def of DEFAULT_WIDGETS) {
        if (!ids.has(def.id)) merged.push(def);
      }
      return merged.sort((a, b) => a.order - b.order);
    }
  } catch {
    // ignore
  }
  return DEFAULT_WIDGETS;
}

export function useDashboardPrefs() {
  const [widgets, setWidgets] = useState<WidgetConfig[]>(loadPrefs);

  const savePrefs = useCallback((updated: WidgetConfig[]) => {
    setWidgets(updated);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  }, []);

  const toggleWidget = useCallback((id: string) => {
    const updated = widgets.map(w =>
      w.id === id ? { ...w, visible: !w.visible } : w
    );
    savePrefs(updated);
  }, [widgets, savePrefs]);

  const moveWidget = useCallback((id: string, direction: 'up' | 'down') => {
    const idx = widgets.findIndex(w => w.id === id);
    if (idx < 0) return;
    const newIdx = direction === 'up' ? idx - 1 : idx + 1;
    if (newIdx < 0 || newIdx >= widgets.length) return;
    const updated = [...widgets];
    [updated[idx], updated[newIdx]] = [updated[newIdx], updated[idx]];
    const reordered = updated.map((w, i) => ({ ...w, order: i }));
    savePrefs(reordered);
  }, [widgets, savePrefs]);

  const resetPrefs = useCallback(() => {
    savePrefs(DEFAULT_WIDGETS);
  }, [savePrefs]);

  return { widgets, toggleWidget, moveWidget, resetPrefs };
}
