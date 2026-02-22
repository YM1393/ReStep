import { useState, useEffect, useRef, useCallback } from 'react';
import { walkingRouteApi } from '../services/api';
import type { WalkingRoute } from '../services/api';

declare global {
  interface Window {
    kakao: any;
  }
}

interface WalkingRouteCardProps {
  patientId: string;
  speedMps: number;
}

interface PlaceResult {
  place_name: string;
  address_name: string;
  road_address_name?: string;
  x: string; // lng
  y: string; // lat
}

// Haversine distance (meters)
function haversineDistance(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371000;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function formatTime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}초`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  if (mins >= 60) {
    const hrs = Math.floor(mins / 60);
    const remainMins = mins % 60;
    return remainMins > 0 ? `${hrs}시간 ${remainMins}분` : `${hrs}시간`;
  }
  if (secs === 0) return `${mins}분`;
  return `${mins}분 ${secs}초`;
}

export default function WalkingRouteCard({ patientId, speedMps }: WalkingRouteCardProps) {
  const [routes, setRoutes] = useState<WalkingRoute[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);

  // Search state
  const [originQuery, setOriginQuery] = useState('');
  const [destQuery, setDestQuery] = useState('');
  const [originResults, setOriginResults] = useState<PlaceResult[]>([]);
  const [destResults, setDestResults] = useState<PlaceResult[]>([]);
  const [selectedOrigin, setSelectedOrigin] = useState<PlaceResult | null>(null);
  const [selectedDest, setSelectedDest] = useState<PlaceResult | null>(null);

  // Map state
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const polylineRef = useRef<any>(null);
  const [sdkReady, setSdkReady] = useState(false);

  // Selected route for display
  const [selectedRoute, setSelectedRoute] = useState<WalkingRoute | null>(null);

  useEffect(() => {
    loadRoutes();
  }, [patientId]);

  // Initialize Kakao SDK (poll until script is loaded)
  useEffect(() => {
    let cancelled = false;
    const tryLoad = () => {
      if (cancelled) return;
      if (window.kakao?.maps) {
        window.kakao.maps.load(() => {
          if (!cancelled) setSdkReady(true);
        });
      } else {
        setTimeout(tryLoad, 200);
      }
    };
    tryLoad();
    return () => { cancelled = true; };
  }, []);

  const loadRoutes = async () => {
    try {
      const data = await walkingRouteApi.getAll(patientId);
      setRoutes(data);
      if (data.length > 0) setSelectedRoute(data[0]);
    } catch { /* ignore */ }
    setLoading(false);
  };

  // Destroy old map when view switches (form ↔ route list use different DOM elements)
  useEffect(() => {
    mapInstanceRef.current = null;
    markersRef.current = [];
    polylineRef.current = null;
  }, [showForm]);

  // Create map on a container element
  const createMap = useCallback((container: HTMLDivElement, lat = 37.5665, lng = 126.978) => {
    if (!sdkReady) return null;
    const kakao = window.kakao;
    const map = new kakao.maps.Map(container, {
      center: new kakao.maps.LatLng(lat, lng),
      level: 5,
    });
    mapInstanceRef.current = map;
    return map;
  }, [sdkReady]);

  // Show route on map (creates map if needed)
  const showRouteOnMap = useCallback((route: WalkingRoute, container?: HTMLDivElement | null) => {
    if (!sdkReady) return;
    const kakao = window.kakao;

    // Create map if not exists
    const target = container || mapContainerRef.current;
    if (!mapInstanceRef.current && target) {
      createMap(target, route.origin_lat, route.origin_lng);
    }
    const map = mapInstanceRef.current;
    if (!map) return;

    // Clear old markers and polyline
    markersRef.current.forEach(m => m.setMap(null));
    markersRef.current = [];
    if (polylineRef.current) polylineRef.current.setMap(null);

    const originPos = new kakao.maps.LatLng(route.origin_lat, route.origin_lng);
    const destPos = new kakao.maps.LatLng(route.dest_lat, route.dest_lng);

    // Origin marker (blue)
    const originMarker = new kakao.maps.Marker({ map, position: originPos });
    const originOverlay = new kakao.maps.CustomOverlay({
      map, position: originPos,
      content: '<div style="padding:3px 8px;background:#3B82F6;color:white;border-radius:12px;font-size:11px;font-weight:600;transform:translateY(-42px);">출발</div>',
      yAnchor: 0,
    });

    // Dest marker (red)
    const destMarker = new kakao.maps.Marker({ map, position: destPos });
    const destOverlay = new kakao.maps.CustomOverlay({
      map, position: destPos,
      content: '<div style="padding:3px 8px;background:#EF4444;color:white;border-radius:12px;font-size:11px;font-weight:600;transform:translateY(-42px);">도착</div>',
      yAnchor: 0,
    });

    markersRef.current = [originMarker, destMarker, originOverlay, destOverlay];

    // Polyline
    polylineRef.current = new kakao.maps.Polyline({
      map,
      path: [originPos, destPos],
      strokeWeight: 4,
      strokeColor: '#3B82F6',
      strokeOpacity: 0.8,
      strokeStyle: 'shortdash',
    });

    // Fit bounds
    const bounds = new kakao.maps.LatLngBounds();
    bounds.extend(originPos);
    bounds.extend(destPos);
    map.setBounds(bounds, 60, 60, 60, 60);
  }, [sdkReady, createMap]);

  // Callback ref for map container - initializes map when DOM element appears
  const mapRefCallback = useCallback((node: HTMLDivElement | null) => {
    mapContainerRef.current = node;
    if (!node || !sdkReady) return;

    // Small delay to ensure DOM is laid out
    setTimeout(() => {
      if (!mapContainerRef.current) return;
      if (selectedRoute) {
        showRouteOnMap(selectedRoute, node);
      } else if (showForm) {
        createMap(node);
      }
    }, 50);
  }, [sdkReady, selectedRoute, showForm, showRouteOnMap, createMap]);

  // Re-render map when sdkReady changes and container already exists
  useEffect(() => {
    if (!sdkReady || !mapContainerRef.current) return;
    if (selectedRoute) {
      showRouteOnMap(selectedRoute);
    } else if (showForm) {
      createMap(mapContainerRef.current);
    }
  }, [sdkReady]);

  // Preview on map when both origins selected
  useEffect(() => {
    if (!selectedOrigin || !selectedDest || !sdkReady) return;
    const previewRoute: WalkingRoute = {
      id: '', patient_id: '', created_at: '',
      origin_address: selectedOrigin.place_name,
      origin_lat: parseFloat(selectedOrigin.y),
      origin_lng: parseFloat(selectedOrigin.x),
      dest_address: selectedDest.place_name,
      dest_lat: parseFloat(selectedDest.y),
      dest_lng: parseFloat(selectedDest.x),
      distance_meters: null,
    };
    showRouteOnMap(previewRoute);
  }, [selectedOrigin, selectedDest, sdkReady, showRouteOnMap]);

  // Keyword search
  const searchPlaces = useCallback((query: string, callback: (results: PlaceResult[]) => void) => {
    if (!sdkReady || !query.trim()) { callback([]); return; }
    const kakao = window.kakao;
    const ps = new kakao.maps.services.Places();
    ps.keywordSearch(query, (data: any, status: any) => {
      if (status === kakao.maps.services.Status.OK) {
        callback(data.slice(0, 5));
      } else {
        callback([]);
      }
    });
  }, [sdkReady]);

  // Debounced search
  const originTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const destTimerRef = useRef<ReturnType<typeof setTimeout>>();

  const handleOriginSearch = (val: string) => {
    setOriginQuery(val);
    setSelectedOrigin(null);
    clearTimeout(originTimerRef.current);
    originTimerRef.current = setTimeout(() => searchPlaces(val, setOriginResults), 300);
  };

  const handleDestSearch = (val: string) => {
    setDestQuery(val);
    setSelectedDest(null);
    clearTimeout(destTimerRef.current);
    destTimerRef.current = setTimeout(() => searchPlaces(val, setDestResults), 300);
  };

  const handleSave = async () => {
    if (!selectedOrigin || !selectedDest) return;
    setSaving(true);
    const oLat = parseFloat(selectedOrigin.y);
    const oLng = parseFloat(selectedOrigin.x);
    const dLat = parseFloat(selectedDest.y);
    const dLng = parseFloat(selectedDest.x);
    const dist = haversineDistance(oLat, oLng, dLat, dLng) * 1.3;

    try {
      const created = await walkingRouteApi.create(patientId, {
        origin_address: selectedOrigin.place_name,
        origin_lat: oLat,
        origin_lng: oLng,
        dest_address: selectedDest.place_name,
        dest_lat: dLat,
        dest_lng: dLng,
        distance_meters: Math.round(dist),
      });
      setRoutes(prev => [created, ...prev]);
      setSelectedRoute(created);
      setShowForm(false);
      setOriginQuery('');
      setDestQuery('');
      setSelectedOrigin(null);
      setSelectedDest(null);
      setOriginResults([]);
      setDestResults([]);
    } catch { /* ignore */ }
    setSaving(false);
  };

  const handleDelete = async (routeId: string) => {
    try {
      await walkingRouteApi.delete(routeId);
      setRoutes(prev => prev.filter(r => r.id !== routeId));
      if (selectedRoute?.id === routeId) {
        const remaining = routes.filter(r => r.id !== routeId);
        setSelectedRoute(remaining[0] || null);
      }
    } catch { /* ignore */ }
  };

  if (loading) return null;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm overflow-hidden">
      {/* Route Section */}
      <div className="p-4">
        <div className="flex justify-between items-center mb-3">
          <h4 className="font-semibold text-gray-900 dark:text-gray-100 text-sm">경로 분석</h4>
          <button
            onClick={() => { setShowForm(!showForm); if (!showForm) setSelectedRoute(null); }}
            className="text-xs px-3 py-1.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            {showForm ? '취소' : '+ 경로'}
          </button>
        </div>

        {/* Add Form */}
        {showForm && (
          <div className="mb-3 space-y-2">
            {/* Origin Search */}
            <div className="relative">
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-blue-500 text-white text-[10px] flex items-center justify-center font-bold flex-shrink-0">출</span>
                <input
                  type="text"
                  placeholder="출발지 검색"
                  value={originQuery}
                  onChange={e => handleOriginSearch(e.target.value)}
                  className="flex-1 px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400"
                />
              </div>
              {originResults.length > 0 && !selectedOrigin && (
                <div className="absolute z-50 left-7 right-0 mt-1 bg-white dark:bg-gray-700 rounded-lg shadow-lg border border-gray-200 dark:border-gray-600 max-h-40 overflow-y-auto">
                  {originResults.map((r, i) => (
                    <button key={i} onClick={() => { setSelectedOrigin(r); setOriginQuery(r.place_name); setOriginResults([]); }}
                      className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-600 border-b border-gray-100 dark:border-gray-600 last:border-b-0">
                      <p className="font-medium text-gray-900 dark:text-gray-100">{r.place_name}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{r.road_address_name || r.address_name}</p>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Destination Search */}
            <div className="relative">
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-red-500 text-white text-[10px] flex items-center justify-center font-bold flex-shrink-0">도</span>
                <input
                  type="text"
                  placeholder="도착지 검색"
                  value={destQuery}
                  onChange={e => handleDestSearch(e.target.value)}
                  className="flex-1 px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400"
                />
              </div>
              {destResults.length > 0 && !selectedDest && (
                <div className="absolute z-50 left-7 right-0 mt-1 bg-white dark:bg-gray-700 rounded-lg shadow-lg border border-gray-200 dark:border-gray-600 max-h-40 overflow-y-auto">
                  {destResults.map((r, i) => (
                    <button key={i} onClick={() => { setSelectedDest(r); setDestQuery(r.place_name); setDestResults([]); }}
                      className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-600 border-b border-gray-100 dark:border-gray-600 last:border-b-0">
                      <p className="font-medium text-gray-900 dark:text-gray-100">{r.place_name}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{r.road_address_name || r.address_name}</p>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Map Preview */}
            <div ref={mapRefCallback} className="w-full h-48 rounded-lg bg-gray-100 dark:bg-gray-700" />

            {/* Distance & Time Preview */}
            {selectedOrigin && selectedDest && speedMps > 0 && (() => {
              const dist = haversineDistance(
                parseFloat(selectedOrigin.y), parseFloat(selectedOrigin.x),
                parseFloat(selectedDest.y), parseFloat(selectedDest.x)
              ) * 1.3;
              const time = dist / speedMps;
              const normalTime = dist / 1.0;
              return (
                <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg text-sm">
                  <div className="flex justify-between mb-1">
                    <span className="text-gray-600 dark:text-gray-400">예상 거리</span>
                    <span className="font-bold text-gray-900 dark:text-gray-100">{dist >= 1000 ? `${(dist / 1000).toFixed(1)}km` : `${Math.round(dist)}m`}</span>
                  </div>
                  <div className="flex justify-between mb-1">
                    <span className="text-gray-600 dark:text-gray-400">환자 예상 시간</span>
                    <span className="font-bold text-blue-600 dark:text-blue-400">{formatTime(time)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">일반인 기준 (1.0m/s)</span>
                    <span className="font-medium text-gray-500">{formatTime(normalTime)}</span>
                  </div>
                </div>
              );
            })()}

            <button
              onClick={handleSave}
              disabled={saving || !selectedOrigin || !selectedDest}
              className="w-full py-2 text-sm font-semibold text-white bg-blue-500 rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {saving ? '저장 중...' : '경로 저장'}
            </button>
          </div>
        )}

        {/* Saved Routes */}
        {!showForm && routes.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-4">저장된 경로가 없습니다</p>
        ) : !showForm && (
          <div className="space-y-2">
            {routes.map(route => {
              const dist = route.distance_meters || 0;
              const time = speedMps > 0 ? dist / speedMps : 0;
              const isSelected = selectedRoute?.id === route.id;
              return (
                <div key={route.id}
                  className={`group p-3 rounded-xl cursor-pointer transition-colors ${isSelected ? 'bg-blue-50 dark:bg-blue-900/20 ring-1 ring-blue-300 dark:ring-blue-700' : 'bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700'}`}
                  onClick={() => { setSelectedRoute(route); }}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 text-xs mb-1">
                        <span className="w-4 h-4 rounded-full bg-blue-500 text-white text-[8px] flex items-center justify-center font-bold">출</span>
                        <span className="text-gray-700 dark:text-gray-300 truncate">{route.origin_address}</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-xs">
                        <span className="w-4 h-4 rounded-full bg-red-500 text-white text-[8px] flex items-center justify-center font-bold">도</span>
                        <span className="text-gray-700 dark:text-gray-300 truncate">{route.dest_address}</span>
                      </div>
                    </div>
                    <div className="flex items-start gap-2 flex-shrink-0 ml-2">
                      <div className="text-right">
                        <p className="text-xs text-gray-400">{dist >= 1000 ? `${(dist / 1000).toFixed(1)}km` : `${Math.round(dist)}m`}</p>
                        {speedMps > 0 && (
                          <p className="text-sm font-bold text-blue-600 dark:text-blue-400">{formatTime(time)}</p>
                        )}
                      </div>
                      <button onClick={e => { e.stopPropagation(); handleDelete(route.id); }}
                        className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-opacity">&times;</button>
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Map for selected route */}
            {selectedRoute && (
              <div ref={mapRefCallback} className="w-full h-48 rounded-lg bg-gray-100 dark:bg-gray-700 mt-2" />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
