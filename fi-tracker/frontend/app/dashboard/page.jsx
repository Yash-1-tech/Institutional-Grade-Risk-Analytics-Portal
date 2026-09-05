"use client";

import { useState, useEffect } from "react";
import {
  LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid,
} from "recharts";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api";

export default function FixedIncomeDashboard({ portfolioId }) {
  const [curve, setCurve] = useState(null);
  const [shiftBps, setShiftBps] = useState(0);
  const [sensitivities, setSensitivities] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/v1/curve/latest/`)
      .then((r) => r.json())
      .then(setCurve);
  }, []);

  useEffect(() => {
    if (!portfolioId) return;
    setLoading(true);
    fetch(`${API_BASE}/v1/portfolio/${portfolioId}/sensitivities/?shift_bps=${shiftBps}`)
      .then((r) => r.json())
      .then((data) => {
        setSensitivities(data);
        setLoading(false);
      });
  }, [portfolioId, shiftBps]);

  const curveSeries = curve
    ? Object.entries(curve.rates).map(([tenor, rate]) => ({
        tenor,
        base: rate * 100,
        shifted: rate * 100 + shiftBps / 100,
      }))
    : [];

  return (
    <main className="min-h-screen bg-[#0B1210] text-[#E7EFEC] font-mono">
      <div className="max-w-5xl mx-auto px-6 py-12">
        <header className="mb-10 border-b border-[#1E2D28] pb-6">
          <h1 className="text-2xl tracking-tight text-[#E7EFEC]">
            Fixed Income Sensitivities Tracker
          </h1>
          <p className="text-sm text-[#7C9188] mt-1">
            Duration, convexity, and parallel-shift shock analysis for a bond
            portfolio.
          </p>
        </header>

        {/* Yield Curve Controller */}
        <section className="mb-10">
          <h2 className="text-sm text-[#7C9188] mb-3">
            Treasury yield curve {curve && `— ${curve.date}`}
          </h2>
          <div className="border border-[#1E2D28] rounded p-4">
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={curveSeries}>
                <CartesianGrid stroke="#1E2D28" strokeDasharray="3 3" />
                <XAxis dataKey="tenor" tick={{ fill: "#7C9188", fontSize: 11 }} />
                <YAxis
                  tick={{ fill: "#7C9188", fontSize: 11 }}
                  tickFormatter={(v) => `${v.toFixed(1)}%`}
                />
                <Tooltip
                  contentStyle={{ background: "#101A17", border: "1px solid #1E2D28" }}
                  formatter={(v) => `${v.toFixed(2)}%`}
                />
                <Line type="monotone" dataKey="base" stroke="#5FBF95"
                      strokeWidth={2} dot={{ r: 3 }} name="Current" />
                <Line type="monotone" dataKey="shifted" stroke="#D97757"
                      strokeWidth={2} strokeDasharray="5 3" dot={{ r: 3 }}
                      name="Shifted" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-4">
            <label className="text-xs text-[#7C9188]">
              Parallel shift: {shiftBps > 0 ? "+" : ""}{shiftBps} bps
            </label>
            <input
              type="range" min="-300" max="300" step="5"
              value={shiftBps}
              onChange={(e) => setShiftBps(parseInt(e.target.value))}
              className="w-full mt-2"
            />
          </div>
        </section>

        {/* Sensitivities Table */}
        {sensitivities && (
          <section className="mb-10">
            <h2 className="text-sm text-[#7C9188] mb-3">Bond-level sensitivities</h2>
            <div className="border border-[#1E2D28] rounded overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-[#7C9188] border-b border-[#1E2D28]">
                    <th className="p-3">ISIN</th>
                    <th className="p-3">PV</th>
                    <th className="p-3">YTM</th>
                    <th className="p-3">Mod. Duration</th>
                    <th className="p-3">Convexity</th>
                  </tr>
                </thead>
                <tbody>
                  {sensitivities.bonds?.map((b) => (
                    <tr key={b.isin} className="border-b border-[#1E2D28] last:border-0">
                      <td className="p-3">{b.isin}</td>
                      <td className="p-3">${b.pv.toLocaleString()}</td>
                      <td className="p-3">{(b.ytm * 100).toFixed(2)}%</td>
                      <td className="p-3">{b.modified_duration.toFixed(2)}</td>
                      <td className="p-3">{b.convexity.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* Shock Analysis Widget */}
        {sensitivities && (
          <section className="mb-10">
            <h2 className="text-sm text-[#7C9188] mb-3">Shock analysis</h2>
            <div className="grid grid-cols-3 gap-6">
              <div className="border border-[#1E2D28] rounded p-4">
                <div className="text-xs text-[#7C9188]">Base value</div>
                <div className="text-xl mt-1">
                  ${sensitivities.total_pv.toLocaleString()}
                </div>
              </div>
              <div className="border border-[#1E2D28] rounded p-4">
                <div className="text-xs text-[#7C9188]">
                  Shocked value ({shiftBps > 0 ? "+" : ""}{shiftBps}bps)
                </div>
                <div className="text-xl mt-1 text-[#D97757]">
                  ${sensitivities.shocked_value_exact?.toLocaleString()}
                </div>
                <div className="text-xs text-[#7C9188] mt-1">
                  {sensitivities.exact_value_change_pct}%
                </div>
              </div>
              <div className="border border-[#1E2D28] rounded p-4">
                <div className="text-xs text-[#7C9188]">Convexity benefit</div>
                <div className="text-xl mt-1 text-[#5FBF95]">
                  +${sensitivities.convexity_dollar_benefit?.toLocaleString()}
                </div>
                <div className="text-xs text-[#7C9188] mt-1">
                  vs. duration-only estimate
                </div>
              </div>
            </div>
          </section>
        )}

        {loading && <p className="text-sm text-[#7C9188]">recalculating…</p>}
      </div>
    </main>
  );
}
