import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

interface AngleDataPoint {
  time: number;
  shoulder_tilt: number;
  hip_tilt: number;
}

interface AngleChartProps {
  data: AngleDataPoint[];
}

export default function AngleChart({ data }: AngleChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="space-y-4">
        <div className="card">
          <h4 className="font-semibold text-gray-800 mb-4">어깨 기울기</h4>
          <div className="text-center py-8 text-gray-500">
            각도 데이터가 없습니다
          </div>
        </div>
        <div className="card">
          <h4 className="font-semibold text-gray-800 mb-4">골반 기울기</h4>
          <div className="text-center py-8 text-gray-500">
            각도 데이터가 없습니다
          </div>
        </div>
      </div>
    );
  }

  // 데이터 샘플링 (너무 많으면 성능 저하)
  const sampledData = data.length > 100
    ? data.filter((_, i) => i % Math.ceil(data.length / 100) === 0)
    : data;

  // 평균값 계산
  const shoulderAvg = sampledData.reduce((sum, d) => sum + d.shoulder_tilt, 0) / sampledData.length;
  const hipAvg = sampledData.reduce((sum, d) => sum + d.hip_tilt, 0) / sampledData.length;
  const avgMap: Record<string, number> = {
    shoulder_tilt: shoulderAvg,
    hip_tilt: hipAvg,
  };

  const ChartComponent = ({
    dataKey,
    title,
    color
  }: {
    dataKey: 'shoulder_tilt' | 'hip_tilt';
    title: string;
    color: string;
  }) => {
    const avg = avgMap[dataKey];
    return (
      <div className="card">
        <h4 className="font-semibold text-gray-800 dark:text-gray-100 mb-4 flex items-center justify-between">
          <span className="flex items-center">
            <div className={`w-3 h-3 rounded-full mr-2`} style={{ backgroundColor: color }}></div>
            {title}
          </span>
          <span className={`text-sm font-bold ${Math.abs(avg) <= 5 ? 'text-green-600' : 'text-orange-600'}`}>
            평균 {avg >= 0 ? '+' : ''}{avg.toFixed(1)}°
          </span>
        </h4>

        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sampledData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="time"
                tick={{ fontSize: 11 }}
                tickFormatter={(value) => `${value.toFixed(1)}s`}
                label={{ value: '시간 (초)', position: 'insideBottom', offset: -5, fontSize: 10 }}
              />
              <YAxis
                tick={{ fontSize: 11 }}
                domain={[-15, 15]}
                tickFormatter={(value) => `${value}°`}
                label={{ value: '기울기 (도)', angle: -90, position: 'insideLeft', fontSize: 10 }}
              />
              <Tooltip
                formatter={(value: number) => [`${value.toFixed(1)}°`, title]}
                labelFormatter={(label) => `${Number(label).toFixed(2)}초`}
                contentStyle={{ fontSize: 12 }}
              />
              <ReferenceLine y={0} stroke="#666" strokeDasharray="5 5" />
              <ReferenceLine y={5} stroke="#f59e0b" strokeDasharray="3 3" strokeOpacity={0.5} />
              <ReferenceLine y={-5} stroke="#f59e0b" strokeDasharray="3 3" strokeOpacity={0.5} />
              <ReferenceLine
                y={avg}
                stroke="#ef4444"
                strokeDasharray="6 3"
                strokeWidth={1.5}
                label={{ value: `평균 ${avg >= 0 ? '+' : ''}${avg.toFixed(1)}°`, position: 'right', fontSize: 10, fill: '#ef4444' }}
              />
              <Line
                type="monotone"
                dataKey={dataKey}
                stroke={color}
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="mt-3 p-2 bg-gray-50 rounded-lg text-xs text-gray-500">
          <p>• 양수(+): 오른쪽이 높음 | 음수(-): 왼쪽이 높음</p>
          <p>• 노란선(±5°): 기준선 | <span className="text-red-500">빨간선: 평균값</span></p>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      <ChartComponent
        dataKey="shoulder_tilt"
        title="어깨 기울기"
        color="#3b82f6"
      />
      <ChartComponent
        dataKey="hip_tilt"
        title="골반 기울기"
        color="#10b981"
      />
    </div>
  );
}
