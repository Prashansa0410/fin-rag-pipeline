"use client";
import React, { useEffect, useState } from 'react';
import Link from 'next/link';

export default function AnalyticsDashboard() {
  const [summary, setSummary] = useState<any>(null);
  const [routing, setRouting] = useState<any>(null);
  const [latency, setLatency] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch('/api/analytics/summary').then(res => res.json()),
      fetch('/api/analytics/routing').then(res => res.json()),
      fetch('/api/analytics/latency').then(res => res.json())
    ]).then(([sumData, routeData, latData]) => {
      setSummary(sumData);
      setRouting(routeData);
      setLatency(latData);
      setLoading(false);
    }).catch(err => {
      console.error(err);
      setLoading(false);
    });
  }, []);

  if (loading) return <div className="p-8">Loading analytics...</div>;
  if (!summary) return <div className="p-8 text-red-500">Failed to load analytics</div>;

  const totalQueries = summary.total_queries || 1; // Prevent div by 0 for percentages
  const ecoPct = Math.round((routing.economical || 0) / totalQueries * 100);
  const stdPct = Math.round((routing.standard || 0) / totalQueries * 100);
  const advPct = Math.round((routing.advanced || 0) / totalQueries * 100);

  return (
    <div className="p-8 max-w-6xl mx-auto bg-gray-50 min-h-screen">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Cost & Performance Analytics</h1>
        <Link href="/" className="text-blue-600 hover:underline">
          &larr; Back to Home
        </Link>
      </div>
      
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <p className="text-sm font-medium text-gray-500 uppercase">Total Queries</p>
          <p className="text-3xl font-bold mt-2 text-gray-900">{summary.total_queries}</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-green-200">
          <p className="text-sm font-medium text-green-700 uppercase">Tokens Saved (Context Budget)</p>
          <p className="text-3xl font-bold mt-2 text-green-800">
            {summary.total_tokens_saved.toLocaleString()}
          </p>
          <p className="text-xs mt-1 text-green-600">Pruned before generation</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <p className="text-sm font-medium text-gray-500 uppercase">Avg Total Latency</p>
          <p className="text-3xl font-bold mt-2 text-gray-900">{summary.avg_latency_ms} ms</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-red-200">
          <p className="text-sm font-medium text-red-700 uppercase">Review Escalation Rate</p>
          <p className="text-3xl font-bold mt-2 text-red-800">{summary.review_escalation_rate}%</p>
          <p className="text-xs mt-1 text-red-600">Flagged for HITL</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Routing Distribution */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h2 className="text-xl font-bold text-gray-800 mb-4">Intelligent Routing Savings</h2>
          <p className="text-sm text-gray-600 mb-6">Percentage of queries dynamically routed to cheaper model tiers based on high retrieval confidence.</p>
          
          <div className="space-y-4">
            <div>
              <div className="flex justify-between mb-1">
                <span className="font-semibold text-green-700">Economical Tier</span>
                <span>{ecoPct}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-green-500 h-2 rounded-full" style={{ width: `${ecoPct}%` }}></div>
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <span className="font-semibold text-blue-700">Standard Tier</span>
                <span>{stdPct}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${stdPct}%` }}></div>
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <span className="font-semibold text-purple-700">Advanced Tier (High Cost)</span>
                <span>{advPct}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-purple-500 h-2 rounded-full" style={{ width: `${advPct}%` }}></div>
              </div>
            </div>
          </div>
        </div>

        {/* Latency Breakdown */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h2 className="text-xl font-bold text-gray-800 mb-4">Average Latency Breakdown</h2>
          <div className="flex flex-col justify-center h-full pb-8">
            <div className="flex items-center justify-between p-3 border-b border-gray-100">
              <span className="text-gray-600">Query Analysis (Deterministic)</span>
              <span className="font-semibold">{latency.query_analysis_ms} ms</span>
            </div>
            <div className="flex items-center justify-between p-3 border-b border-gray-100">
              <span className="text-gray-600">Hybrid Search (Vector + Keyword)</span>
              <span className="font-semibold">{latency.retrieval_ms} ms</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded mt-2 border border-blue-100">
              <span className="text-blue-800 font-semibold">LLM Generation</span>
              <span className="font-bold text-blue-900">{latency.llm_generation_ms} ms</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
