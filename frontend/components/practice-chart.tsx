"use client";

import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const activity = [
  { day: "Mon", solved: 2 }, { day: "Tue", solved: 4 }, { day: "Wed", solved: 3 },
  { day: "Thu", solved: 6 }, { day: "Fri", solved: 4 }, { day: "Sat", solved: 5 }, { day: "Sun", solved: 2 },
];

export function PracticeChart() {
  return (
    <section className="card chart-card">
      <div className="section-heading"><div><h2>Practice activity</h2><p>Problems solved this week</p></div><span className="pill">Demo data</span></div>
      <div className="chart" aria-label={activity.map(({ day, solved }) => `${day} ${solved}`).join(", ")} role="img">
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <BarChart data={activity} margin={{ top: 12, right: 8, left: -20, bottom: 0 }}>
            <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: "#a4adc6", fontSize: 12 }} dy={8} />
            <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: "#a4adc6", fontSize: 12 }} />
            <Tooltip cursor={{ fill: "#202941" }} contentStyle={{ background: "#151c2f", border: "1px solid #303952", borderRadius: 8 }} />
            <Bar name="Solved" dataKey="solved" fill="#F5A623" radius={[5, 5, 0, 0]} maxBarSize={34} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
